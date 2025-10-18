import React, { useMemo, useState, useEffect } from 'react';
import {
  ActivityIndicator,
  SafeAreaView,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  TouchableOpacity,
  View,
} from 'react-native';
import * as Clipboard from 'expo-clipboard';

import { api } from '../services/api';
import { useTranscription } from '../TranscriptionContext';

const PREVIEW_LIMIT = 220;

const SECTION_META = {
  tweet: {
    title: 'Tweet-Ready',
    actionLabel: 'Generate Tweet',
    description: 'Craft a concise, shareable version ideal for Twitter/X.',
  },
  professional: {
    title: 'Professional Tone',
    actionLabel: 'Generate Professional',
    description: 'Rewrite with polished business language and structure.',
  },
  custom: {
    title: 'Custom Prompt',
    actionLabel: 'Transform',
    description: 'Use your own instruction to reshape the text.',
  },
};

export default function TransformScreen({ route, navigation }) {
  const sourceText = route.params?.text ?? '';
  const { transformCache, setTransformCache } = useTranscription();

  const cached = useMemo(() => transformCache[sourceText] || {}, [transformCache, sourceText]);

  const [showFull, setShowFull] = useState(false);
  const [results, setResults] = useState({
    tweet: cached.tweet ?? null,
    professional: cached.professional ?? null,
    custom: cached.custom?.text ?? null,
  });
  const [errors, setErrors] = useState({ tweet: '', professional: '', custom: '' });
  const [loading, setLoading] = useState({ tweet: false, professional: false, custom: false });
  const [customPrompt, setCustomPrompt] = useState(cached.custom?.prompt ?? '');
  const [feedback, setFeedback] = useState('');

  useEffect(() => {
    setResults({
      tweet: cached.tweet ?? null,
      professional: cached.professional ?? null,
      custom: cached.custom?.text ?? null,
    });
    setCustomPrompt(cached.custom?.prompt ?? '');
    setErrors({ tweet: '', professional: '', custom: '' });
  }, [cached]);

  const updateCache = (type, payload) => {
    setTransformCache((prev) => {
      const existing = prev[sourceText] || {};
      const nextValue =
        type === 'custom'
          ? { ...existing, custom: { prompt: customPrompt.trim(), text: payload } }
          : { ...existing, [type]: payload };
      return { ...prev, [sourceText]: nextValue };
    });
  };

  const handleTransform = async (type) => {
    if (!sourceText) {
      setErrors((prev) => ({ ...prev, [type]: 'No source text available.' }));
      return;
    }

    if (type === 'custom' && !customPrompt.trim()) {
      setErrors((prev) => ({ ...prev, custom: 'Enter a custom prompt first.' }));
      return;
    }

    setLoading((prev) => ({ ...prev, [type]: true }));
    setErrors((prev) => ({ ...prev, [type]: '' }));

    try {
      const response = await api.transform(
        sourceText,
        type,
        type === 'custom' ? customPrompt.trim() : null
      );
      const text = response?.text ?? '';
      setResults((prev) => ({ ...prev, [type]: text }));
      updateCache(type, text);
    } catch (err) {
      console.error('transform error', err);
      setErrors((prev) => ({ ...prev, [type]: err?.message || 'Transform failed.' }));
    } finally {
      setLoading((prev) => ({ ...prev, [type]: false }));
    }
  };

  const copyToClipboard = async (value) => {
    if (!value) return;
    try {
      await Clipboard.setStringAsync(value);
      setFeedback('Copied to clipboard!');
      setTimeout(() => setFeedback(''), 2000);
    } catch (err) {
      console.error('clipboard error', err);
      setFeedback('Unable to copy text.');
      setTimeout(() => setFeedback(''), 2000);
    }
  };

  const renderPreview = () => {
    if (!sourceText) {
      return <Text style={styles.previewPlaceholder}>No transcript text provided.</Text>;
    }

    const truncated = sourceText.length > PREVIEW_LIMIT && !showFull;
    const displayText = truncated ? `${sourceText.slice(0, PREVIEW_LIMIT)}…` : sourceText;

    return (
      <View style={styles.previewBox}>
        <Text style={styles.previewLabel}>Original Transcript</Text>
        <Text style={styles.previewText}>{displayText}</Text>
        {sourceText.length > PREVIEW_LIMIT ? (
          <TouchableOpacity onPress={() => setShowFull((prev) => !prev)}>
            <Text style={styles.previewToggle}>{showFull ? 'Show less' : 'Show full'}</Text>
          </TouchableOpacity>
        ) : null}
      </View>
    );
  };

  const renderSection = (type) => {
    const meta = SECTION_META[type];
    const resultValue = type === 'custom' ? results.custom : results[type];
    const errorMessage = errors[type];
    const isLoading = loading[type];

    return (
      <View key={type} style={styles.section}>
        <View style={styles.sectionHeader}>
          <Text style={styles.sectionTitle}>{meta.title}</Text>
          <Text style={styles.sectionDescription}>{meta.description}</Text>
        </View>

        {type === 'custom' ? (
          <TextInput
            style={styles.input}
            placeholder="Enter your custom instruction"
            placeholderTextColor="#94a3b8"
            value={customPrompt}
            onChangeText={setCustomPrompt}
            multiline
          />
        ) : null}

        {errorMessage ? <Text style={styles.errorText}>{errorMessage}</Text> : null}

        <TouchableOpacity
          style={[styles.button, isLoading ? styles.disabledButton : styles.primaryButton, type === 'custom' && !customPrompt.trim() ? styles.disabledButton : null]}
          onPress={() => handleTransform(type)}
          disabled={isLoading || (type === 'custom' && !customPrompt.trim())}
        >
          {isLoading ? (
            <ActivityIndicator color="#f8fafc" />
          ) : (
            <Text style={styles.buttonText}>{meta.actionLabel}</Text>
          )}
        </TouchableOpacity>

        {resultValue ? (
          <View style={styles.resultBox}>
            <Text style={styles.resultText}>{resultValue}</Text>
            <TouchableOpacity
              style={[styles.button, styles.secondaryButton]}
              onPress={() => copyToClipboard(resultValue)}
            >
              <Text style={[styles.buttonText, styles.secondaryButtonText]}>Copy</Text>
            </TouchableOpacity>
          </View>
        ) : null}
      </View>
    );
  };

  return (
    <SafeAreaView style={styles.container}>
      <ScrollView contentContainerStyle={styles.inner}>
        <Text style={styles.title}>Transform Your Transcript</Text>
        {feedback ? <Text style={styles.feedback}>{feedback}</Text> : null}
        {renderPreview()}
        {['tweet', 'professional', 'custom'].map(renderSection)}
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
    paddingBottom: 48,
  },
  title: {
    fontSize: 24,
    fontWeight: '600',
    color: '#f8fafc',
    textAlign: 'center',
  },
  feedback: {
    color: '#34d399',
    textAlign: 'center',
    marginTop: 8,
  },
  previewBox: {
    backgroundColor: '#1e293b',
    borderRadius: 12,
    padding: 16,
    marginTop: 16,
  },
  previewLabel: {
    color: '#93c5fd',
    fontWeight: '600',
    marginBottom: 8,
  },
  previewText: {
    color: '#e2e8f0',
    lineHeight: 20,
  },
  previewToggle: {
    marginTop: 12,
    color: '#60a5fa',
    fontWeight: '500',
  },
  previewPlaceholder: {
    color: '#f87171',
  },
  section: {
    backgroundColor: '#1e293b',
    borderRadius: 12,
    padding: 16,
    marginTop: 20,
  },
  sectionHeader: {
    marginBottom: 8,
  },
  sectionTitle: {
    color: '#f8fafc',
    fontSize: 18,
    fontWeight: '600',
  },
  sectionDescription: {
    color: '#cbd5f5',
    fontSize: 14,
  },
  input: {
    minHeight: 70,
    borderRadius: 10,
    borderColor: '#3b82f6',
    borderWidth: 1,
    padding: 12,
    color: '#f8fafc',
    textAlignVertical: 'top',
  },
  button: {
    minWidth: 200,
    paddingVertical: 14,
    borderRadius: 12,
    alignItems: 'center',
    justifyContent: 'center',
    marginTop: 8,
  },
  primaryButton: {
    backgroundColor: '#2563eb',
  },
  secondaryButton: {
    marginTop: 12,
    backgroundColor: 'transparent',
    borderWidth: 1,
    borderColor: '#93c5fd',
  },
  secondaryButtonText: {
    color: '#bfdbfe',
  },
  buttonText: {
    color: '#f8fafc',
    fontSize: 16,
    fontWeight: '600',
  },
  disabledButton: {
    opacity: 0.6,
  },
  resultBox: {
    backgroundColor: '#0f172a',
    borderRadius: 10,
    padding: 16,
    marginTop: 12,
  },
  resultText: {
    color: '#e2e8f0',
    lineHeight: 20,
  },
  errorText: {
    color: '#f87171',
  },
});
