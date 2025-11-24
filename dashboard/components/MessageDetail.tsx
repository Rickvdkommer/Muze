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
    setSending(true);
    try {
      await markMessageProcessed(message.id);
      onProcessed();
    } catch (error) {
      console.error('Failed to skip message:', error);
      alert('Failed to mark as processed. Please try again.');
    } finally {
      setSending(false);
    }
  };

  return (
    <div className="bg-gradient-to-br from-blue-50 to-indigo-50 rounded-xl shadow-sm border border-blue-100">
      {/* Message Header */}
      <div className="px-6 py-4 border-b-2 border-blue-200">
        <div className="flex items-center gap-3 mb-2">
          <div className="w-10 h-10 bg-blue-500 rounded-lg flex items-center justify-center shadow-sm">
            <span className="text-2xl">📨</span>
          </div>
          <div className="flex-1">
            <h2 className="text-xl font-bold text-gray-900">Message Details</h2>
            <p className="text-xs text-blue-600">
              From {message.phone_number} • {formatDistanceToNow(new Date(message.timestamp), { addSuffix: true })}
            </p>
          </div>
          <button
            onClick={() => setShowCorpus(!showCorpus)}
            className="px-4 py-2 bg-white border-2 border-blue-300 text-blue-700 text-sm font-semibold rounded-lg hover:bg-blue-50 hover:border-blue-400 shadow-sm transition"
          >
            {showCorpus ? '👁️ Hide' : '📚 View'} Corpus
          </button>
        </div>
      </div>

      {/* User Corpus (Collapsible) */}
      {showCorpus && (
        <div className="px-6 py-4 bg-gradient-to-br from-indigo-50 to-purple-50 border-b-2 border-indigo-200">
          <div className="flex items-center gap-2 mb-2">
            <span className="text-lg">📚</span>
            <h3 className="text-sm font-bold text-gray-900">User Knowledge Graph</h3>
          </div>
          <div className="prose prose-sm max-w-none bg-white rounded-lg p-4 max-h-60 overflow-y-auto text-gray-900 border-2 border-indigo-200 shadow-sm">
            <ReactMarkdown>{corpus}</ReactMarkdown>
          </div>
        </div>
      )}

      {/* Incoming Message */}
      <div className="px-6 py-4 border-b-2 border-blue-200">
        <div className="flex items-center gap-2 mb-2">
          <span className="text-lg">💬</span>
          <h3 className="text-sm font-bold text-gray-900">Incoming Message</h3>
        </div>
        <div className="bg-gradient-to-br from-blue-100 to-cyan-100 rounded-lg p-4 border-2 border-blue-300 shadow-sm">
          <p className="text-gray-900 font-medium">{message.text}</p>
        </div>
      </div>

      {/* AI Suggested Response */}
      <div className="px-6 py-4 border-b-2 border-blue-200">
        <div className="flex items-center justify-between mb-2">
          <div className="flex items-center gap-2">
            <span className="text-lg">🤖</span>
            <h3 className="text-sm font-bold text-gray-900">AI Suggested Response</h3>
          </div>
          <button
            onClick={loadAIResponse}
            disabled={loading}
            className="px-4 py-2 bg-white border-2 border-blue-300 text-blue-700 text-sm font-semibold rounded-lg hover:bg-blue-50 hover:border-blue-400 disabled:opacity-50 shadow-sm transition"
          >
            {loading ? '⏳ Generating...' : '🔄 Regenerate'}
          </button>
        </div>
        {loading ? (
          <div className="bg-white rounded-lg p-6 text-center border-2 border-blue-200 shadow-sm">
            <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
            <p className="text-sm text-blue-600 font-semibold mt-3">Generating response...</p>
          </div>
        ) : (
          <div className="bg-gradient-to-br from-green-100 to-emerald-100 rounded-lg p-4 border-2 border-green-300 shadow-sm">
            <p className="text-gray-900 font-medium whitespace-pre-wrap">{aiResponse}</p>
          </div>
        )}
      </div>

      {/* Response Editor */}
      <div className="px-6 py-4 border-b-2 border-blue-200">
        <div className="flex items-center gap-2 mb-2">
          <span className="text-lg">✏️</span>
          <h3 className="text-sm font-bold text-gray-900">Edit & Send Response</h3>
        </div>
        <textarea
          value={editedResponse}
          onChange={(e) => setEditedResponse(e.target.value)}
          rows={6}
          className="w-full px-4 py-3 border-2 border-blue-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none resize-none text-gray-900 placeholder:text-gray-400 shadow-sm"
          placeholder="Edit the AI response before sending..."
        />
        <div className="mt-2 flex items-center justify-between text-sm">
          <span className={editedResponse.length > 1600 ? 'text-red-600 font-bold' : 'text-blue-600 font-semibold'}>
            {editedResponse.length} / 1600 characters
          </span>
          {editedResponse.length > 1600 && (
            <span className="text-red-600 font-bold">⚠ Too long! Trim message</span>
          )}
        </div>
      </div>

      {/* Actions */}
      <div className="px-6 py-4 bg-white rounded-b-xl">
        <div className="flex gap-3">
          <button
            onClick={handleSendResponse}
            disabled={sending || !editedResponse.trim() || editedResponse.length > 1600}
            className="flex-1 bg-gradient-to-r from-blue-500 to-indigo-600 hover:from-blue-600 hover:to-indigo-700 text-white font-bold py-3 px-4 rounded-lg transition disabled:opacity-50 disabled:cursor-not-allowed shadow-md"
          >
            {sending ? '⏳ Sending...' : '📤 Send Response'}
          </button>
          <button
            onClick={handleSkip}
            disabled={sending}
            className="px-6 py-3 bg-white border-2 border-gray-300 text-gray-700 font-bold rounded-lg hover:bg-gray-50 transition disabled:opacity-50 shadow-sm"
          >
            {sending ? '⏳ Processing...' : '✓ Mark as Processed'}
          </button>
        </div>
        <p className="text-xs text-blue-600 font-medium mt-3 text-center">
          💡 Corpus is automatically updated when messages arrive. Send a response or mark as processed without replying.
        </p>
      </div>
    </div>
  );
}
