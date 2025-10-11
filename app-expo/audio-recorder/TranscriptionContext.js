import React, { createContext, useCallback, useContext, useMemo, useState } from 'react';

const TranscriptionContext = createContext();

export function TranscriptionProvider({ children }) {
  const [transcriptions, setTranscriptions] = useState(null);
  const [transformCache, setTransformCache] = useState({});

  const resetTransforms = useCallback(() => setTransformCache({}), []);

  const value = useMemo(
    () => ({
      transcriptions,
      setTranscriptions,
      transformCache,
      setTransformCache,
      resetTransforms,
    }),
    [transcriptions, transformCache, resetTransforms]
  );

  return (
    <TranscriptionContext.Provider value={value}>
      {children}
    </TranscriptionContext.Provider>
  );
}

export function useTranscription() {
  return useContext(TranscriptionContext);
}
