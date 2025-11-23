'use client';

import { useState, useEffect } from 'react';
import { getAllUsers, getUserCorpus, getUserMessages, updateUserCorpus, User } from '@/lib/api';
import { formatDistanceToNow } from 'date-fns';
import ReactMarkdown from 'react-markdown';

export default function UserCorpusViewer() {
  const [users, setUsers] = useState<User[]>([]);
  const [selectedUser, setSelectedUser] = useState<User | null>(null);
  const [corpus, setCorpus] = useState('');
  const [editedCorpus, setEditedCorpus] = useState('');
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [editing, setEditing] = useState(false);
  const [messageCount, setMessageCount] = useState(0);

  useEffect(() => {
    loadUsers();
  }, []);

  const loadUsers = async () => {
    setLoading(true);
    try {
      const data = await getAllUsers();
      setUsers(data);
    } catch (error) {
      console.error('Failed to load users:', error);
    } finally {
      setLoading(false);
    }
  };

  const loadUserData = async (user: User) => {
    setSelectedUser(user);
    setLoading(true);
    try {
      const [corpusData, messages] = await Promise.all([
        getUserCorpus(user.phone_number),
        getUserMessages(user.phone_number, 100),
      ]);

      setCorpus(corpusData);
      setEditedCorpus(corpusData);
      setMessageCount(messages.length);
      setEditing(false);
    } catch (error) {
      console.error('Failed to load user data:', error);
      alert('Failed to load user data.');
    } finally {
      setLoading(false);
    }
  };

  const handleSave = async () => {
    if (!selectedUser) return;

    setSaving(true);
    try {
      await updateUserCorpus(selectedUser.phone_number, editedCorpus);
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

  if (loading && users.length === 0) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="text-center">
          <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mb-4"></div>
          <p className="text-gray-500">Loading users...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
      {/* User List */}
      <div className="lg:col-span-1">
        <div className="bg-white rounded-lg shadow">
          <div className="px-6 py-4 border-b border-gray-200">
            <h2 className="text-lg font-semibold text-gray-900">All Users ({users.length})</h2>
            <p className="text-sm text-gray-500">Click to view corpus</p>
          </div>

          {users.length === 0 ? (
            <div className="p-8 text-center text-gray-500">
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
                  d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z"
                />
              </svg>
              <p className="text-sm">No users yet</p>
            </div>
          ) : (
            <div className="divide-y divide-gray-200 max-h-[600px] overflow-y-auto">
              {users.map((user) => (
                <button
                  key={user.phone_number}
                  onClick={() => loadUserData(user)}
                  className={`w-full text-left px-6 py-4 hover:bg-gray-50 transition ${
                    selectedUser?.phone_number === user.phone_number
                      ? 'bg-blue-50 border-l-4 border-blue-500'
                      : ''
                  }`}
                >
                  <p className="text-sm font-medium text-gray-900 mb-1">
                    {user.display_name || user.phone_number}
                  </p>
                  {user.display_name && (
                    <p className="text-xs text-gray-500 mb-1">{user.phone_number}</p>
                  )}
                  <p className="text-xs text-gray-400">
                    Last message: {formatDistanceToNow(new Date(user.last_message_at), { addSuffix: true })}
                  </p>
                </button>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Corpus Display */}
      <div className="lg:col-span-2">
        {selectedUser ? (
          <div className="bg-white rounded-lg shadow">
            <div className="px-6 py-4 border-b border-gray-200">
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="text-lg font-semibold text-gray-900">
                    {selectedUser.display_name || selectedUser.phone_number}
                  </h3>
                  <p className="text-sm text-gray-500">
                    {messageCount} messages • Created {formatDistanceToNow(new Date(selectedUser.created_at), { addSuffix: true })}
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
              {loading ? (
                <div className="flex items-center justify-center py-12">
                  <div className="text-center">
                    <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mb-4"></div>
                    <p className="text-gray-500">Loading corpus...</p>
                  </div>
                </div>
              ) : editing ? (
                <div>
                  <textarea
                    value={editedCorpus}
                    onChange={(e) => setEditedCorpus(e.target.value)}
                    rows={20}
                    className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none font-mono text-sm resize-y text-gray-900 placeholder:text-gray-400"
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
        ) : (
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
            <p className="text-lg font-medium text-gray-900 mb-1">No user selected</p>
            <p className="text-sm">Select a user from the list to view their knowledge graph</p>
          </div>
        )}
      </div>
    </div>
  );
}
