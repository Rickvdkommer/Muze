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

// Send WhatsApp message via Twilio
export async function sendWhatsAppMessage(to: string, message: string): Promise<void> {
  const accountSid = process.env.NEXT_PUBLIC_TWILIO_ACCOUNT_SID;
  const authToken = process.env.NEXT_PUBLIC_TWILIO_AUTH_TOKEN;
  const from = process.env.NEXT_PUBLIC_TWILIO_PHONE_NUMBER;

  const response = await fetch(
    `https://api.twilio.com/2010-04-01/Accounts/${accountSid}/Messages.json`,
    {
      method: 'POST',
      headers: {
        'Authorization': 'Basic ' + btoa(`${accountSid}:${authToken}`),
        'Content-Type': 'application/x-www-form-urlencoded',
      },
      body: new URLSearchParams({
        To: to,
        From: from || '',
        Body: message,
      }),
    }
  );

  if (!response.ok) {
    throw new Error('Failed to send message via Twilio');
  }
}

export default api;
