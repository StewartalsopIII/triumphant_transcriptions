import asyncio
import json
import logging
import os
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

try:
    import httpx
except ImportError:  # pragma: no cover - httpx is optional depending on backend
    httpx = None  # type: ignore

logger = logging.getLogger(__name__)


@dataclass
class AudioPayload:
    """Metadata describing the uploaded audio clip."""

    filename: str
    content_type: str
    size_bytes: int
    data: bytes


class ArchiveBackend:
    """Common interface for storage backends."""

    backend_name = "none"

    async def store(
        self,
        session_id: str,
        prompt: str,
        raw_response_text: str,
        strict_variants: Dict[str, Any],
        light_variants: Dict[str, Any],
        audio: Optional[AudioPayload],
        metadata: Dict[str, Any],
    ) -> Dict[str, Any]:
        raise NotImplementedError


class NullBackend(ArchiveBackend):
    """No-op backend when archiving is disabled."""

    async def store(
        self,
        session_id: str,
        prompt: str,
        raw_response_text: str,
        strict_variants: Dict[str, Any],
        light_variants: Dict[str, Any],
        audio: Optional[AudioPayload],
        metadata: Dict[str, Any],
    ) -> Dict[str, Any]:
        return {"enabled": False, "backend": self.backend_name}


class LocalFilesystemBackend(ArchiveBackend):
    backend_name = "local"

    def __init__(self, base_directory: str) -> None:
        self.base_path = Path(base_directory)
        self.base_path.mkdir(parents=True, exist_ok=True)

    async def store(
        self,
        session_id: str,
        prompt: str,
        raw_response_text: str,
        strict_variants: Dict[str, Any],
        light_variants: Dict[str, Any],
        audio: Optional[AudioPayload],
        metadata: Dict[str, Any],
    ) -> Dict[str, Any]:
        def _write_to_disk() -> Dict[str, Any]:
            session_path = self.base_path / session_id
            session_path.mkdir(parents=True, exist_ok=True)

            artifacts: Dict[str, Any] = {}

            if audio and audio.data:
                audio_path = session_path / audio.filename
                audio_path.write_bytes(audio.data)
                artifacts["audioPath"] = str(audio_path)

            strict_path = session_path / "strict.json"
            strict_path.write_text(json.dumps(strict_variants, ensure_ascii=True, indent=2))
            artifacts["strictPath"] = str(strict_path)

            light_path = session_path / "light.json"
            light_path.write_text(json.dumps(light_variants, ensure_ascii=True, indent=2))
            artifacts["lightPath"] = str(light_path)

            raw_path = session_path / "raw_response.txt"
            raw_path.write_text(raw_response_text)
            artifacts["rawResponsePath"] = str(raw_path)

            prompt_path = session_path / "prompt.txt"
            prompt_path.write_text(prompt)
            artifacts["promptPath"] = str(prompt_path)

            metadata_path = session_path / "metadata.json"
            metadata_payload = {
                **metadata,
                "archivedAt": datetime.utcnow().isoformat() + "Z",
            }
            metadata_path.write_text(json.dumps(metadata_payload, ensure_ascii=True, indent=2))
            artifacts["metadataPath"] = str(metadata_path)

            return {
                "enabled": True,
                "backend": self.backend_name,
                "artifacts": artifacts,
            }

        return await asyncio.to_thread(_write_to_disk)


class VercelBlobBackend(ArchiveBackend):
    backend_name = "vercel_blob"

    def __init__(self, token: str, prefix: str = "sessions") -> None:
        if httpx is None:  # pragma: no cover - httpx missing
            raise RuntimeError("httpx is required for Vercel Blob archiving")

        self.token = token
        self.prefix = prefix.strip("/") or "sessions"
        self.timeout = httpx.Timeout(30.0)

    async def store(
        self,
        session_id: str,
        prompt: str,
        raw_response_text: str,
        strict_variants: Dict[str, Any],
        light_variants: Dict[str, Any],
        audio: Optional[AudioPayload],
        metadata: Dict[str, Any],
    ) -> Dict[str, Any]:
        if httpx is None:  # pragma: no cover - defensive
            raise RuntimeError("httpx is required for Vercel Blob archiving")

        artifacts: Dict[str, Any] = {}
        base_key = f"{self.prefix}/{session_id}"

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            if audio and audio.data:
                key = f"{base_key}/{audio.filename}"
                artifacts["audioUrl"] = await self._upload(
                    client, key, audio.data, audio.content_type or "application/octet-stream"
                )

            strict_bytes = json.dumps(strict_variants, ensure_ascii=True, indent=2).encode("utf-8")
            artifacts["strictUrl"] = await self._upload(
                client, f"{base_key}/strict.json", strict_bytes, "application/json"
            )

            light_bytes = json.dumps(light_variants, ensure_ascii=True, indent=2).encode("utf-8")
            artifacts["lightUrl"] = await self._upload(
                client, f"{base_key}/light.json", light_bytes, "application/json"
            )

            raw_bytes = raw_response_text.encode("utf-8")
            artifacts["rawResponseUrl"] = await self._upload(
                client, f"{base_key}/raw_response.txt", raw_bytes, "text/plain"
            )

            prompt_bytes = prompt.encode("utf-8")
            artifacts["promptUrl"] = await self._upload(
                client, f"{base_key}/prompt.txt", prompt_bytes, "text/plain"
            )

            metadata_payload = {
                **metadata,
                "archivedAt": datetime.utcnow().isoformat() + "Z",
            }
            metadata_bytes = json.dumps(metadata_payload, ensure_ascii=True, indent=2).encode("utf-8")
            artifacts["metadataUrl"] = await self._upload(
                client, f"{base_key}/metadata.json", metadata_bytes, "application/json"
            )

        return {
            "enabled": True,
            "backend": self.backend_name,
            "artifacts": artifacts,
        }

    async def _upload(self, client: "httpx.AsyncClient", key: str, data: bytes, content_type: str) -> str:
        url = f"https://blob.vercel-storage.com/{key}"
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": content_type,
        }
        response = await client.put(url, headers=headers, content=data)
        response.raise_for_status()

        try:
            payload = response.json()
        except ValueError:  # pragma: no cover - non-JSON response
            payload = {}

        return (
            payload.get("downloadUrl")
            or payload.get("url")
            or payload.get("pathname")
            or url
        )


class ArchiveManager:
    """Factory/manager that delegates persistence to a concrete backend."""

    def __init__(self, backend: ArchiveBackend) -> None:
        self._backend = backend

    @classmethod
    def from_env(cls) -> "ArchiveManager":
        storage_mode = os.getenv("ARCHIVE_STORAGE", "none").strip().lower()

        if storage_mode == "local":
            base_dir = os.getenv("ARCHIVE_LOCAL_DIR", "./archive")
            backend: ArchiveBackend = LocalFilesystemBackend(base_dir)
            logger.info("archive_backend_initialized: mode=local directory=%s", base_dir)
        elif storage_mode == "vercel_blob":
            token = os.getenv("VERCEL_BLOB_READ_WRITE_TOKEN")
            prefix = os.getenv("ARCHIVE_BLOB_PREFIX", "sessions")
            if not token:
                logger.warning(
                    "archive_backend_disabled: mode=vercel_blob reason=missing_token"
                )
                backend = NullBackend()
            else:
                try:
                    backend = VercelBlobBackend(token=token, prefix=prefix)
                    logger.info(
                        "archive_backend_initialized: mode=vercel_blob prefix=%s", prefix
                    )
                except Exception as exc:  # pragma: no cover - defensive
                    logger.error("archive_backend_init_failed: %s", exc)
                    backend = NullBackend()
        else:
            backend = NullBackend()
            if storage_mode not in {"", "none"}:
                logger.warning(
                    "archive_backend_disabled: mode=%s reason=unrecognized", storage_mode
                )

        return cls(backend)

    async def persist_session(
        self,
        session_id: str,
        prompt: str,
        raw_response_text: str,
        strict_variants: Dict[str, Any],
        light_variants: Dict[str, Any],
        audio: Optional[AudioPayload],
        metadata: Dict[str, Any],
    ) -> Dict[str, Any]:
        try:
            result = await self._backend.store(
                session_id=session_id,
                prompt=prompt,
                raw_response_text=raw_response_text,
                strict_variants=strict_variants,
                light_variants=light_variants,
                audio=audio,
                metadata=metadata,
            )
        except Exception as exc:  # pragma: no cover - defensive logging
            logger.error(
                "archive_persist_failed: session_id=%s error=%s", session_id, exc, exc_info=True
            )
            return {
                "enabled": False,
                "backend": getattr(self._backend, "backend_name", "unknown"),
                "error": str(exc),
            }

        # Ensure stable shape for consumers
        result.setdefault("backend", getattr(self._backend, "backend_name", "unknown"))
        result.setdefault("enabled", result.get("backend") != "none")
        return result


_default_manager: Optional[ArchiveManager] = None


def get_archive_manager() -> ArchiveManager:
    global _default_manager
    if _default_manager is None:
        _default_manager = ArchiveManager.from_env()
    return _default_manager


__all__ = [
    "ArchiveManager",
    "AudioPayload",
    "get_archive_manager",
]
