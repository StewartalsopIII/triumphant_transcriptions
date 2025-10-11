import React, { createContext, useContext, useState } from 'react';

const TranscriptionContext = createContext();

export function TranscriptionProvider({ children }) {
  const [transcriptions, setTranscriptions] = useState(null);

  return (
    <TranscriptionContext.Provider value={{ transcriptions, setTranscriptions }}>
      {children}
    </TranscriptionContext.Provider>
  );
}

export function useTranscription() {
  return useContext(TranscriptionContext);
}

