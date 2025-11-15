git # Custom Prompt Flows

This document visualizes the current custom prompt pipeline and two candidate constraint strategies. Each diagram is written in Mermaid so we can tweak or extend it easily.

---

## 1. Current Flow (Unconstrained)

```mermaid
flowchart LR
    A[User enters custom prompt + transcript] --> B[Expo TransformScreen sends request]
    B --> C[FastAPI /api/transform]
    C --> D[Backend injects raw user instruction + transcript]
    D --> E[Gemini generates free-form response]
    E --> F[Response returned to app & cached]
    F --> G[User reviews result in Transform screen]
```

**Characteristics**
- Gemini sees the raw user instruction with no extra guardrails.
- Output may include commentary, lists, or long text.
- No validation beyond “request succeeded.”

---

## 2. Soft Constraint Template

```mermaid
flowchart LR
    A[User enters custom prompt] --> B[App sends request with prompt + transcript]
    B --> C[Backend wraps prompt in template with style hints]
    C --> D[Gemini told to reply ≤120 words, single paragraph, no lists]
    D --> E[Gemini output]
    E --> F[Backend trims whitespace, returns text]
    F --> G[App displays result & warns if hints ignored]
```

**What changes**
- Backend injects strong guidance (length, no lists, paragraph focus) before the user instruction.
- We do not reject responses; the app only surfaces warnings if the hints are ignored.

---

## 3. Hard Constraint Template + Validation

```mermaid
flowchart LR
    A(User enters custom prompt) --> B(App sends request)
    B --> C(Backend wraps instruction in strict scaffold specifying exact format + max length)
    C --> D(Gemini response)
    D --> E(Backend validator checks: word count, no bullets, correct paragraph count)
    E -->|Pass| F(Return result to app)
    E -->|Fail| G(Backend retries with reinforced instructions or returns error message)
    F --> H(App shows constrained output)
    G --> H
```

**What changes**
- Backend enforces a fixed structure (e.g., ≤120 words, single paragraph).  
- If the model’s answer violates rules, we either retry with extra instructions or respond with an error telling the user to adjust the prompt.
- Guarantees predictable formatting but adds latency and possible failures.

---

Use these diagrams to pick the enforcement level you want before we modify the `/api/transform` logic.

