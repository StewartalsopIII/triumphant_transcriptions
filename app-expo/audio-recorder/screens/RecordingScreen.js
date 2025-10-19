import React, { useCallback, useRef, useState } from 'react';
import {
  SafeAreaView,
  StyleSheet,
  Text,
  TouchableOpacity,
  View,
} from 'react-native';
import { Audio } from 'expo-av';
import { useFocusEffect } from '@react-navigation/native';
import { activateKeepAwakeAsync, deactivateKeepAwake } from 'expo-keep-awake';

import { useTranscription } from '../TranscriptionContext';

const formatTime = (seconds) => {
  const mins = Math.floor(seconds / 60)
    .toString()
    .padStart(2, '0');
  const secs = Math.floor(seconds % 60)
    .toString()
    .padStart(2, '0');
  return `${mins}:${secs}`;
};

export default function RecordingScreen({ navigation }) {
  const KEEP_AWAKE_TAG = 'recording-session';
  const [isRecording, setIsRecording] = useState(false);
  const [elapsedTime, setElapsedTime] = useState(0);
  const [error, setError] = useState('');
  const timerRef = useRef(null);
  const recordingRef = useRef(null);
  const { setTranscriptions, resetTransforms } = useTranscription();

  useFocusEffect(
    useCallback(() => {
      setTranscriptions(null);
      resetTransforms();
      setError('');
      setElapsedTime(0);

      return () => {
        if (timerRef.current) {
          clearInterval(timerRef.current);
          timerRef.current = null;
        }

        deactivateKeepAwake(KEEP_AWAKE_TAG).catch(() => {});
      };
    }, [setTranscriptions, resetTransforms])
  );

  const startRecording = async () => {
    setError('');

    try {
      const permission = await Audio.requestPermissionsAsync();
      if (!permission.granted) {
        setError('Microphone permission denied. Enable it in Settings.');
        return;
      }

      await Audio.setAudioModeAsync({
        allowsRecordingIOS: true,
        playsInSilentModeIOS: true,
      });

      const { recording } = await Audio.Recording.createAsync(
        Audio.RecordingOptionsPresets.HIGH_QUALITY
      );

      recordingRef.current = recording;

      await activateKeepAwakeAsync(KEEP_AWAKE_TAG);

      setIsRecording(true);
      setElapsedTime(0);

      timerRef.current = setInterval(() => {
        setElapsedTime((prev) => prev + 1);
      }, 1000);
    } catch (err) {
      console.error('startRecording error', err);
      setError(err?.message || 'Failed to start recording.');

      if (recordingRef.current) {
        try {
          await recordingRef.current.stopAndUnloadAsync();
        } catch (stopErr) {
          console.error('cleanupRecording error', stopErr);
        }
        recordingRef.current = null;
      }

      deactivateKeepAwake(KEEP_AWAKE_TAG).catch(() => {});
    }
  };

  const stopRecording = async () => {
    const recording = recordingRef.current;
    if (!recording) {
      return;
    }

    try {
      if (timerRef.current) {
        clearInterval(timerRef.current);
        timerRef.current = null;
      }

      await recording.stopAndUnloadAsync();
      await Audio.setAudioModeAsync({ allowsRecordingIOS: false });

      const uri = recording.getURI();
      if (!uri) {
        setError('Unable to access recording file.');
        return;
      }

      navigation.navigate('Processing', { uri });
    } catch (err) {
      console.error('stopRecording error', err);
      setError(err?.message || 'Failed to stop recording.');
    } finally {
      setIsRecording(false);
      recordingRef.current = null;
      deactivateKeepAwake(KEEP_AWAKE_TAG).catch(() => {});
    }
  };

  return (
    <SafeAreaView style={styles.container}>
      <View style={styles.inner}>
        <Text style={styles.title}>Triumphant Transcripts Recorder</Text>
        <View style={styles.timerContainer}>
          <Text style={styles.timerText}>{formatTime(elapsedTime)}</Text>
          {isRecording && <Text style={styles.recordingBadge}>Recording…</Text>}
        </View>

        {error ? <Text style={styles.errorText}>{error}</Text> : null}

        <TouchableOpacity
          style={[styles.button, isRecording ? styles.stopButton : styles.primaryButton]}
          onPress={isRecording ? stopRecording : startRecording}
        >
          <Text style={styles.buttonText}>
            {isRecording ? 'Stop Recording' : 'Start Recording'}
          </Text>
        </TouchableOpacity>

        <Text style={styles.helperText}>
          {isRecording
            ? 'Tap stop when you are done speaking.'
            : 'Tap start to begin a new recording. It will upload automatically when you stop.'}
        </Text>
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
    marginBottom: 32,
  },
  timerContainer: {
    alignItems: 'center',
    marginBottom: 24,
  },
  timerText: {
    fontSize: 48,
    fontVariant: ['tabular-nums'],
    color: '#f1f5f9',
  },
  recordingBadge: {
    marginTop: 8,
    color: '#f87171',
    fontWeight: '500',
  },
  errorText: {
    textAlign: 'center',
    color: '#f87171',
    marginBottom: 12,
  },
  button: {
    minWidth: 220,
    paddingVertical: 16,
    borderRadius: 12,
    alignItems: 'center',
    justifyContent: 'center',
    marginVertical: 8,
  },
  primaryButton: {
    backgroundColor: '#2563eb',
  },
  stopButton: {
    backgroundColor: '#ef4444',
  },
  buttonText: {
    color: '#f8fafc',
    fontSize: 16,
    fontWeight: '600',
  },
  helperText: {
    marginTop: 24,
    textAlign: 'center',
    color: '#cbd5f5',
    lineHeight: 20,
  },
});
