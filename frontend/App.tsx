import React, { useEffect, useState } from 'react';
import { StyleSheet, Text, View, ActivityIndicator, TouchableOpacity, ScrollView } from 'react-native';
import { StatusBar } from 'expo-status-bar';

const API_BASE_URL = process.env.EXPO_PUBLIC_API_URL || 'http://localhost:8000';

export default function App() {
  const [health, setHealth] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const checkBackendHealth = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await fetch(`${API_BASE_URL}/health`);
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }
      const data = await response.json();
      setHealth(data);
    } catch (err: any) {
      setError(err.message || 'Failed to reach backend');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    checkBackendHealth();
  }, []);

  return (
    <ScrollView contentContainerStyle={styles.container}>
      <StatusBar style="auto" />
      <View style={styles.card}>
        <Text style={styles.badge}>PHASE 0 READY</Text>
        <Text style={styles.title}>ReMind MVP</Text>
        <Text style={styles.subtitle}>
          Google Photos Memory Reconstruction Platform
        </Text>

        <View style={styles.section}>
          <Text style={styles.sectionHeader}>Backend Service Status</Text>
          {loading ? (
            <ActivityIndicator size="small" color="#1a73e8" />
          ) : error ? (
            <View style={styles.errorBox}>
              <Text style={styles.errorText}>Status: Offline ({error})</Text>
              <Text style={styles.helperText}>
                Ensure FastAPI server is running at {API_BASE_URL}
              </Text>
            </View>
          ) : health ? (
            <View style={styles.successBox}>
              <Text style={styles.successText}>Status: Connected (OK)</Text>
              <Text style={styles.detailText}>Service: {health.service}</Text>
              <Text style={styles.detailText}>Model: {health.gemini_model}</Text>
              <Text style={styles.detailText}>Embeddings: {health.embedding_model}</Text>
            </View>
          ) : null}

          <TouchableOpacity style={styles.button} onPress={checkBackendHealth}>
            <Text style={styles.buttonText}>Test Backend Connection</Text>
          </TouchableOpacity>
        </View>

        <View style={styles.phaseGuide}>
          <Text style={styles.phaseHeader}>Upcoming 5-Screen Flow:</Text>
          <Text style={styles.phaseItem}>1. Memory Search ("What do you remember?")</Text>
          <Text style={styles.phaseItem}>2. Understanding (Gemini Clue Extraction)</Text>
          <Text style={styles.phaseItem}>3. Candidate Grid (Top 20 Possibilities)</Text>
          <Text style={styles.phaseItem}>4. Memory Refinement (Uncertainty-Driven Loop)</Text>
          <Text style={styles.phaseItem}>5. Success & Recognition ("We found it!")</Text>
        </View>
      </View>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: {
    flexGrow: 1,
    backgroundColor: '#f8f9fa',
    alignItems: 'center',
    justifyContent: 'center',
    padding: 20,
  },
  card: {
    backgroundColor: '#ffffff',
    borderRadius: 16,
    padding: 24,
    width: '100%',
    maxWidth: 480,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.08,
    shadowRadius: 12,
    elevation: 3,
  },
  badge: {
    alignSelf: 'flex-start',
    backgroundColor: '#e8f0fe',
    color: '#1a73e8',
    fontWeight: '700',
    fontSize: 12,
    paddingHorizontal: 10,
    paddingVertical: 4,
    borderRadius: 12,
    marginBottom: 12,
  },
  title: {
    fontSize: 28,
    fontWeight: '800',
    color: '#202124',
    marginBottom: 4,
  },
  subtitle: {
    fontSize: 14,
    color: '#5f6368',
    marginBottom: 20,
    lineHeight: 20,
  },
  section: {
    marginVertical: 12,
    padding: 16,
    backgroundColor: '#f1f3f4',
    borderRadius: 12,
  },
  sectionHeader: {
    fontSize: 14,
    fontWeight: '700',
    color: '#3c4043',
    marginBottom: 8,
  },
  successBox: {
    backgroundColor: '#e6f4ea',
    borderRadius: 8,
    padding: 12,
    marginBottom: 10,
  },
  successText: {
    color: '#137333',
    fontWeight: '700',
    marginBottom: 4,
  },
  detailText: {
    fontSize: 12,
    color: '#3c4043',
    marginTop: 2,
  },
  errorBox: {
    backgroundColor: '#fce8e6',
    borderRadius: 8,
    padding: 12,
    marginBottom: 10,
  },
  errorText: {
    color: '#c5221f',
    fontWeight: '700',
  },
  helperText: {
    fontSize: 12,
    color: '#5f6368',
    marginTop: 4,
  },
  button: {
    backgroundColor: '#1a73e8',
    paddingVertical: 10,
    paddingHorizontal: 16,
    borderRadius: 8,
    alignItems: 'center',
    marginTop: 6,
  },
  buttonText: {
    color: '#ffffff',
    fontWeight: '600',
    fontSize: 14,
  },
  phaseGuide: {
    marginTop: 16,
    borderTopWidth: 1,
    borderTopColor: '#e0e0e0',
    paddingTop: 16,
  },
  phaseHeader: {
    fontSize: 13,
    fontWeight: '700',
    color: '#3c4043',
    marginBottom: 8,
  },
  phaseItem: {
    fontSize: 12,
    color: '#5f6368',
    marginBottom: 4,
  },
});
