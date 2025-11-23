'use client';

import { useState, useEffect } from 'react';
import { Message, generateAIResponse, sendWhatsAppMessage, markMessageProcessed, getUserCorpus } from '@/lib/api';
import { formatDistanceToNow } from 'date-fns';
import ReactMarkdown from 'react-markdown';

interface MessageDetailProps {
  message: Message;
  onProcessed: () => void;
}

export default function MessageDetail({ message, onProcessed }: MessageDetailProps) {
  const [aiResponse, setAiResponse] = useState('');
  const [editedResponse, setEditedResponse] = useState('');
  const [corpus, setCorpus] = useState('');
  const [loading, setLoading] = useState(false);
  const [sending, setSending] = useState(false);
  const [showCorpus, setShowCorpus] = useState(false);

  useEffect(() => {
    loadAIResponse();
    loadCorpus();
  }, [message.id]);

  const loadAIResponse = async () => {
    setLoading(true);
    try {
      const response = await generateAIResponse(message.phone_number, message.text);
      setAiResponse(response);
      setEditedResponse(response);
    } catch (error) {
      console.error('Failed to generate AI response:', error);
      setAiResponse('Failed to generate response. Please try again.');
      setEditedResponse('');
    } finally {
      setLoading(false);
    }
  };

  const loadCorpus = async () => {
    try {
      const data = await getUserCorpus(message.phone_number);
      setCorpus(data);
    } catch (error) {
      console.error('Failed to load corpus:', error);
    }
  };

  const handleSendResponse = async () => {
    if (!editedResponse.trim()) return;

    setSending(true);
    try {
      // Send via Twilio
      await sendWhatsAppMessage(message.phone_number, editedResponse);

      // Mark as processed
      await markMessageProcessed(message.id);

      // Note: Corpus update happens automatically when message is received,
      // no need to trigger it here

      // Notify parent
      onProcessed();
    } catch (error) {
      console.error('Failed to send message:', error);
      alert('Failed to send message. Please try again.');
    } finally {
      setSending(false);
    }
  };

  const handleSkip = async () => {
    try {
      await markMessageProcessed(message.id);
      onProcessed();
    } catch (error) {
      console.error('Failed to skip message:', error);
    }
  };

  return (
    <div className="bg-white rounded-lg shadow">
      {/* Message Header */}
      <div className="px-6 py-4 border-b border-gray-200">
        <div className="flex items-center justify-between mb-2">
          <h2 className="text-lg font-semibold text-gray-900">Message Details</h2>
          <button
            onClick={() => setShowCorpus(!showCorpus)}
            className="text-sm text-blue-600 hover:text-blue-700"
          >
            {showCorpus ? 'Hide' : 'View'} User Corpus
          </button>
        </div>
        <p className="text-sm text-gray-500">
          From {message.phone_number} • {formatDistanceToNow(new Date(message.timestamp), { addSuffix: true })}
        </p>
      </div>

      {/* User Corpus (Collapsible) */}
      {showCorpus && (
        <div className="px-6 py-4 bg-gray-50 border-b border-gray-200">
          <h3 className="text-sm font-semibold text-gray-700 mb-2">User Knowledge Graph</h3>
          <div className="prose prose-sm max-w-none bg-white rounded p-4 max-h-60 overflow-y-auto text-gray-900">
            <ReactMarkdown>{corpus}</ReactMarkdown>
          </div>
        </div>
      )}

      {/* Incoming Message */}
      <div className="px-6 py-4 border-b border-gray-200">
        <h3 className="text-sm font-semibold text-gray-700 mb-2">Incoming Message</h3>
        <div className="bg-blue-50 rounded-lg p-4">
          <p className="text-gray-800">{message.text}</p>
        </div>
      </div>

      {/* AI Suggested Response */}
      <div className="px-6 py-4 border-b border-gray-200">
        <div className="flex items-center justify-between mb-2">
          <h3 className="text-sm font-semibold text-gray-700">AI Suggested Response</h3>
          <button
            onClick={loadAIResponse}
            disabled={loading}
            className="text-sm text-blue-600 hover:text-blue-700 disabled:opacity-50"
          >
            {loading ? 'Generating...' : 'Regenerate'}
          </button>
        </div>
        {loading ? (
          <div className="bg-gray-50 rounded-lg p-4 text-center">
            <div className="inline-block animate-spin rounded-full h-6 w-6 border-b-2 border-blue-600"></div>
            <p className="text-sm text-gray-500 mt-2">Generating response...</p>
          </div>
        ) : (
          <div className="bg-green-50 rounded-lg p-4">
            <p className="text-gray-800 whitespace-pre-wrap">{aiResponse}</p>
          </div>
        )}
      </div>

      {/* Response Editor */}
      <div className="px-6 py-4 border-b border-gray-200">
        <h3 className="text-sm font-semibold text-gray-700 mb-2">Edit & Send Response</h3>
        <textarea
          value={editedResponse}
          onChange={(e) => setEditedResponse(e.target.value)}
          rows={6}
          className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none resize-none text-gray-900 placeholder:text-gray-400"
          placeholder="Edit the AI response before sending..."
        />
        <div className="mt-2 flex items-center justify-between text-sm">
          <span className={editedResponse.length > 1600 ? 'text-red-600 font-semibold' : 'text-gray-500'}>
            {editedResponse.length} / 1600 characters
          </span>
          {editedResponse.length > 1600 && (
            <span className="text-red-600 font-semibold">⚠ Too long! Trim message</span>
          )}
        </div>
      </div>

      {/* Actions */}
      <div className="px-6 py-4 bg-gray-50">
        <div className="flex gap-3">
          <button
            onClick={handleSendResponse}
            disabled={sending || !editedResponse.trim() || editedResponse.length > 1600}
            className="flex-1 bg-blue-600 hover:bg-blue-700 text-white font-semibold py-3 px-4 rounded-lg transition disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {sending ? 'Sending...' : 'Send Response'}
          </button>
          <button
            onClick={handleSkip}
            className="px-6 py-3 bg-white border border-gray-300 text-gray-700 font-semibold rounded-lg hover:bg-gray-50 transition"
          >
            Skip
          </button>
        </div>
        <p className="text-xs text-gray-500 mt-3 text-center">
          Sending will mark this message as processed and send via WhatsApp
        </p>
      </div>
    </div>
  );
}
