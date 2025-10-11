import React, { useEffect, useState } from 'react';
import {
  SafeAreaView,
  ScrollView,
  StyleSheet,
  Text,
  TouchableOpacity,
  View,
} from 'react-native';
import * as Clipboard from 'expo-clipboard';

import { useTranscription } from '../TranscriptionContext';

const ENTRIES = [
  { key: 'originalStrict', label: 'Original (Strict)' },
  { key: 'originalLight', label: 'Original (Light)' },
  { key: 'englishStrict', label: 'English (Strict)' },
  { key: 'englishLight', label: 'English (Light)' },
];

export default function ResultsScreen({ navigation }) {
  const { transcriptions } = useTranscription();
  const [feedback, setFeedback] = useState('');

  useEffect(() => {
    if (!transcriptions) {
      navigation.replace('Recording');
    }
  }, [transcriptions, navigation]);

  const copyToClipboard = async (text) => {
    try {
      await Clipboard.setStringAsync(text);
      setFeedback('Copied to clipboard!');
      setTimeout(() => setFeedback(''), 2000);
    } catch (err) {
      console.error('copyToClipboard error', err);
      setFeedback('Unable to copy text.');
      setTimeout(() => setFeedback(''), 2000);
    }
  };

  return (
    <SafeAreaView style={styles.container}>
      <ScrollView contentContainerStyle={styles.inner}>
        <Text style={styles.title}>Transcription Results</Text>
        {feedback ? <Text style={styles.feedback}>{feedback}</Text> : null}

        {ENTRIES.map(({ key, label }) => {
          const transcriptValue = transcriptions?.[key] ?? '';
          return (
            <View key={key} style={styles.card}>
              <View style={styles.cardHeader}>
                <Text style={styles.cardTitle}>{label}</Text>
                <TouchableOpacity
                  style={styles.copyButton}
                  onPress={() => copyToClipboard(transcriptValue)}
                  disabled={!transcriptValue}
                >
                  <Text style={styles.copyButtonText}>Copy</Text>
                </TouchableOpacity>
              </View>
              <Text style={styles.cardBody}>{transcriptValue || '-'}</Text>
              <TouchableOpacity
                style={[
                  styles.button,
                  styles.primaryButton,
                  !transcriptValue ? styles.disabledButton : null,
                ]}
                onPress={() => navigation.navigate('Transform', { text: transcriptValue })}
                disabled={!transcriptValue}
              >
                <Text style={styles.buttonText}>Transform</Text>
              </TouchableOpacity>
            </View>
          );
        })}

        <TouchableOpacity
          style={[styles.button, styles.primaryButton]}
          onPress={() => navigation.replace('Recording')}
        >
          <Text style={styles.buttonText}>Record Again</Text>
        </TouchableOpacity>
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#0f172a',
  },
  inner: {
    padding: 24,
  },
  title: {
    fontSize: 24,
    fontWeight: '600',
    color: '#f8fafc',
    textAlign: 'center',
    marginBottom: 16,
  },
  feedback: {
    color: '#34d399',
    textAlign: 'center',
    marginBottom: 12,
  },
  card: {
    backgroundColor: '#1e293b',
    borderRadius: 12,
    padding: 16,
    marginBottom: 16,
  },
  cardHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 8,
  },
  cardTitle: {
    color: '#f8fafc',
    fontWeight: '600',
    fontSize: 16,
  },
  cardBody: {
    color: '#cbd5f5',
    lineHeight: 20,
  },
  copyButton: {
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 8,
    backgroundColor: '#2563eb',
  },
  copyButtonText: {
    color: '#f8fafc',
    fontWeight: '600',
  },
  button: {
    minWidth: 220,
    paddingVertical: 16,
    borderRadius: 12,
    alignItems: 'center',
    justifyContent: 'center',
    marginTop: 8,
  },
  primaryButton: {
    backgroundColor: '#2563eb',
  },
  disabledButton: {
    opacity: 0.6,
  },
  buttonText: {
    color: '#f8fafc',
    fontSize: 16,
    fontWeight: '600',
  },
});
