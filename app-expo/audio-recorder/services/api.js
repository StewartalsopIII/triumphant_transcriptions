import { Platform } from 'react-native';
import Constants from 'expo-constants';

const API_URL = Constants.expoConfig?.extra?.apiUrl || process.env.EXPO_PUBLIC_API_URL;

if (!API_URL) {
  console.warn('API URL is not configured. Please set EXPO_PUBLIC_API_URL in your .env file.');
}

export const api = {
  async transcribe(uri) {
    if (!API_URL) {
      throw new Error('API URL is not configured.');
    }

    const formData = new FormData();
    formData.append('audio', {
      uri,
      type: 'audio/m4a',
      name: 'recording.m4a',
    });

    const endpoint = `${API_URL}/api/transcribe`;
    console.log('Transcribing via:', endpoint);

    const headers =
      Platform.OS === 'web' ? { 'Content-Type': 'multipart/form-data' } : undefined;

    const response = await fetch(endpoint, {
      method: 'POST',
      body: formData,
      ...(headers ? { headers } : {}),
    });

    if (!response.ok) {
      const error = await response.text();
      throw new Error(`Transcription failed: ${error}`);
    }

    return await response.json();
  },
};
