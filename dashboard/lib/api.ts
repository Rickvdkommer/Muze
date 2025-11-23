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

export interface UserDetails extends User {
  last_interaction_at?: string;
  timezone: string;
  quiet_hours_start: number;
  quiet_hours_end: number;
  onboarding_step: number;
  open_loops: Record<string, any>;
  pending_questions: any[];
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

// Get complete user details (including settings and open loops)
export async function getUserDetails(phoneNumber: string): Promise<UserDetails> {
  const response = await api.get(`/api/users/${encodeURIComponent(phoneNumber)}/details`);
  return response.data;
}

// Update user settings
export async function updateUserSettings(
  phoneNumber: string,
  settings: Partial<Pick<UserDetails, 'timezone' | 'quiet_hours_start' | 'quiet_hours_end' | 'onboarding_step' | 'open_loops' | 'pending_questions' | 'display_name'>>
): Promise<void> {
  await api.put(`/api/users/${encodeURIComponent(phoneNumber)}/settings`, settings);
}

// Reset user corpus to default template
export async function resetUserCorpus(phoneNumber: string): Promise<void> {
  await api.post(`/api/users/${encodeURIComponent(phoneNumber)}/reset-corpus`);
}

// Delete all messages for a user
export async function deleteUserMessages(phoneNumber: string): Promise<number> {
  const response = await api.delete(`/api/users/${encodeURIComponent(phoneNumber)}/messages`);
  return response.data.count;
}

export default api;
