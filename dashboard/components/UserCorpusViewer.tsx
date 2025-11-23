'use client';

import { useState } from 'react';
import { getUserCorpus, getUserMessages, updateUserCorpus } from '@/lib/api';
import ReactMarkdown from 'react-markdown';

export default function UserCorpusViewer() {
  const [phoneNumber, setPhoneNumber] = useState('');
  const [corpus, setCorpus] = useState('');
  const [editedCorpus, setEditedCorpus] = useState('');
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [editing, setEditing] = useState(false);
  const [messageCount, setMessageCount] = useState(0);

  const handleLoad = async () => {
    if (!phoneNumber.trim()) return;

    setLoading(true);
    try {
      // Add whatsapp: prefix if not present
      const formattedNumber = phoneNumber.startsWith('whatsapp:')
        ? phoneNumber
        : `whatsapp:${phoneNumber}`;

      const [corpusData, messages] = await Promise.all([
        getUserCorpus(formattedNumber),
        getUserMessages(formattedNumber, 100),
      ]);

      setCorpus(corpusData);
      setEditedCorpus(corpusData);
      setMessageCount(messages.length);
    } catch (error) {
      console.error('Failed to load user data:', error);
      alert('Failed to load user data. Please check the phone number.');
    } finally {
      setLoading(false);
    }
  };

  const handleSave = async () => {
    setSaving(true);
    try {
      const formattedNumber = phoneNumber.startsWith('whatsapp:')
        ? phoneNumber
        : `whatsapp:${phoneNumber}`;

      await updateUserCorpus(formattedNumber, editedCorpus);
      setCorpus(editedCorpus);
      setEditing(false);
      alert('Corpus updated successfully!');
    } catch (error) {
      console.error('Failed to update corpus:', error);
      alert('Failed to update corpus. Please try again.');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="max-w-4xl">
      {/* Search */}
      <div className="bg-white rounded-lg shadow p-6 mb-6">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">View User Corpus</h2>
        <div className="flex gap-3">
          <input
            type="text"
            value={phoneNumber}
            onChange={(e) => setPhoneNumber(e.target.value)}
            placeholder="Enter phone number (e.g., +31634829116 or whatsapp:+31...)"
            className="flex-1 px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none"
            onKeyDown={(e) => e.key === 'Enter' && handleLoad()}
          />
          <button
            onClick={handleLoad}
            disabled={loading || !phoneNumber.trim()}
            className="px-6 py-2 bg-blue-600 hover:bg-blue-700 text-white font-semibold rounded-lg transition disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {loading ? 'Loading...' : 'Load'}
          </button>
        </div>
      </div>

      {/* Corpus Display */}
      {corpus && (
        <div className="bg-white rounded-lg shadow">
          <div className="px-6 py-4 border-b border-gray-200">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="text-lg font-semibold text-gray-900">Knowledge Graph</h3>
                <p className="text-sm text-gray-500">
                  {phoneNumber} • {messageCount} messages
                </p>
              </div>
              <button
                onClick={() => setEditing(!editing)}
                className="px-4 py-2 text-sm font-medium text-blue-600 bg-blue-50 rounded-lg hover:bg-blue-100"
              >
                {editing ? 'Cancel Edit' : 'Edit Corpus'}
              </button>
            </div>
          </div>

          <div className="p-6">
            {editing ? (
              <div>
                <textarea
                  value={editedCorpus}
                  onChange={(e) => setEditedCorpus(e.target.value)}
                  rows={20}
                  className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none font-mono text-sm resize-y"
                  placeholder="Edit the markdown corpus..."
                />
                <div className="mt-4 flex gap-3">
                  <button
                    onClick={handleSave}
                    disabled={saving}
                    className="px-6 py-2 bg-green-600 hover:bg-green-700 text-white font-semibold rounded-lg transition disabled:opacity-50"
                  >
                    {saving ? 'Saving...' : 'Save Changes'}
                  </button>
                  <button
                    onClick={() => {
                      setEditedCorpus(corpus);
                      setEditing(false);
                    }}
                    className="px-6 py-2 bg-gray-200 hover:bg-gray-300 text-gray-700 font-semibold rounded-lg transition"
                  >
                    Discard
                  </button>
                </div>
              </div>
            ) : (
              <div className="prose prose-sm max-w-none">
                <ReactMarkdown>{corpus}</ReactMarkdown>
              </div>
            )}
          </div>
        </div>
      )}

      {!corpus && !loading && (
        <div className="bg-white rounded-lg shadow p-12 text-center text-gray-500">
          <svg
            className="mx-auto h-12 w-12 text-gray-400 mb-4"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253"
            />
          </svg>
          <p className="text-lg font-medium text-gray-900 mb-1">No corpus loaded</p>
          <p className="text-sm">Enter a phone number above to view their knowledge graph</p>
        </div>
      )}
    </div>
  );
}
