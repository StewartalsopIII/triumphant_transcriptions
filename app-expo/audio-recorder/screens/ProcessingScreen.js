import React, { useCallback, useEffect, useState } from 'react';
import {
  ActivityIndicator,
  SafeAreaView,
  StyleSheet,
  Text,
  TouchableOpacity,
  View,
} from 'react-native';

import { api } from '../services/api';
import { useTranscription } from '../TranscriptionContext';

export default function ProcessingScreen({ route, navigation }) {
  const { uri } = route.params || {};
  const { setTranscriptions } = useTranscription();
  const [error, setError] = useState('');
  const [isProcessing, setIsProcessing] = useState(true);

  const processRecording = useCallback(async () => {
    if (!uri) {
      setError('Missing audio recording. Please record again.');
      setIsProcessing(false);
      return;
    }

    setIsProcessing(true);
    setError('');

    try {
      const result = await api.transcribe(uri);
      setTranscriptions(result);
      navigation.replace('Results');
    } catch (err) {
      console.error('processRecording error', err);
      setError(err?.message || 'Processing failed. Check your connection.');
    } finally {
      setIsProcessing(false);
    }
  }, [uri, setTranscriptions, navigation]);

  useEffect(() => {
    processRecording();
  }, [processRecording]);

  return (
    <SafeAreaView style={styles.container}>
      <View style={styles.inner}>
        <Text style={styles.title}>Processing Recording</Text>
        {isProcessing ? (
          <View style={styles.loadingContainer}>
            <ActivityIndicator size="large" color="#60a5fa" />
            <Text style={[styles.message, styles.spacing]}>Processing…</Text>
            <Text style={[styles.helperText, styles.spacingSmall]}>Hang tight while we transcribe your audio.</Text>
          </View>
        ) : null}

        {error ? <Text style={styles.errorText}>{error}</Text> : null}

        {!isProcessing ? (
          <View style={styles.actions}>
            <TouchableOpacity style={[styles.button, styles.primaryButton]} onPress={processRecording}>
              <Text style={styles.buttonText}>Retry</Text>
            </TouchableOpacity>
            <TouchableOpacity
              style={[styles.button, styles.secondaryButton]}
              onPress={() => navigation.replace('Recording')}
            >
              <Text style={[styles.buttonText, styles.secondaryButtonText]}>Record Again</Text>
            </TouchableOpacity>
          </View>
        ) : null}
      </View>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#0f172a',
  },
  inner: {
    flex: 1,
    paddingHorizontal: 24,
    paddingTop: 48,
  },
  title: {
    fontSize: 24,
    fontWeight: '600',
    color: '#f8fafc',
    textAlign: 'center',
    marginBottom: 48,
  },
  loadingContainer: {
    alignItems: 'center',
  },
  message: {
    color: '#f8fafc',
    fontSize: 18,
  },
  helperText: {
    color: '#cbd5f5',
    textAlign: 'center',
    paddingHorizontal: 16,
    lineHeight: 20,
  },
  spacing: {
    marginTop: 16,
  },
  spacingSmall: {
    marginTop: 8,
  },
  errorText: {
    color: '#f87171',
    textAlign: 'center',
    marginTop: 24,
  },
  actions: {
    marginTop: 32,
    alignItems: 'center',
  },
  button: {
    minWidth: 200,
    paddingVertical: 16,
    borderRadius: 12,
    alignItems: 'center',
    justifyContent: 'center',
    marginVertical: 8,
  },
  primaryButton: {
    backgroundColor: '#2563eb',
  },
  secondaryButton: {
    backgroundColor: 'transparent',
    borderWidth: 1,
    borderColor: '#93c5fd',
  },
  buttonText: {
    color: '#f8fafc',
    fontSize: 16,
    fontWeight: '600',
  },
  secondaryButtonText: {
    color: '#bfdbfe',
  },
});
