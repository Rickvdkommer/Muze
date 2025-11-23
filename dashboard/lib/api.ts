import axios from 'axios';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:5000';

const api = axios.create({
  baseURL: API_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

export interface Message {
  id: number;
  phone_number: string;
  direction: 'incoming' | 'outgoing';
  text: string;
  timestamp: string;
  processed: boolean;
}

export interface User {
  phone_number: string;
  display_name?: string;
  created_at: string;
  last_message_at: string;
}

// Get unprocessed messages
export async function getUnprocessedMessages(limit = 50): Promise<Message[]> {
  const response = await api.get(`/api/messages/unprocessed?limit=${limit}`);
  return response.data.messages;
}

// Get all users
export async function getAllUsers(): Promise<User[]> {
  const response = await api.get('/api/users');
  return response.data.users;
}

// Get user messages
export async function getUserMessages(phoneNumber: string, limit = 50): Promise<Message[]> {
  const response = await api.get(`/api/users/${encodeURIComponent(phoneNumber)}/messages?limit=${limit}`);
  return response.data.messages;
}

// Get user corpus
export async function getUserCorpus(phoneNumber: string): Promise<string> {
  const response = await api.get(`/api/users/${encodeURIComponent(phoneNumber)}/corpus`);
  return response.data.corpus;
}

// Update user corpus
export async function updateUserCorpus(phoneNumber: string, corpus: string): Promise<void> {
  await api.put(`/api/users/${encodeURIComponent(phoneNumber)}/corpus`, { corpus });
}

// Generate AI response
export async function generateAIResponse(phoneNumber: string, message: string): Promise<string> {
  const response = await api.post('/api/generate-response', {
    phone_number: phoneNumber,
    message: message,
  });
  return response.data.response;
}

// Mark message as processed
export async function markMessageProcessed(messageId: number): Promise<void> {
  await api.post(`/api/messages/${messageId}/process`);
}

// Send WhatsApp message via Twilio (secure server-side API route)
export async function sendWhatsAppMessage(to: string, message: string): Promise<void> {
  const response = await fetch('/api/send-message', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      to: to,
      message: message,
    }),
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.error || 'Failed to send message via Twilio');
  }
}

export default api;
