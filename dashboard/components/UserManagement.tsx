'use client';

import { useState, useEffect } from 'react';
import {
  getAllUsers,
  getUserCorpus,
  getUserMessages,
  getUserDetails,
  updateUserCorpus,
  updateUserSettings,
  resetUserCorpus,
  deleteUserMessages,
  User,
  UserDetails
} from '@/lib/api';
import { formatDistanceToNow } from 'date-fns';
import ReactMarkdown from 'react-markdown';

type Tab = 'corpus' | 'settings' | 'loops' | 'messages';

export default function UserManagement() {
  const [users, setUsers] = useState<User[]>([]);
  const [selectedUser, setSelectedUser] = useState<User | null>(null);
  const [userDetails, setUserDetails] = useState<UserDetails | null>(null);
  const [activeTab, setActiveTab] = useState<Tab>('corpus');

  // Corpus state
  const [corpus, setCorpus] = useState('');
  const [editedCorpus, setEditedCorpus] = useState('');
  const [editingCorpus, setEditingCorpus] = useState(false);

  // Settings state
  const [editedSettings, setEditedSettings] = useState<Partial<UserDetails>>({});
  const [editingSettings, setEditingSettings] = useState(false);

  // Loops state
  const [editedLoops, setEditedLoops] = useState<Record<string, any>>({});
  const [editingLoops, setEditingLoops] = useState(false);

  // UI state
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
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
      const [corpusData, details, messages] = await Promise.all([
        getUserCorpus(user.phone_number),
        getUserDetails(user.phone_number),
        getUserMessages(user.phone_number, 1000),
      ]);

      setCorpus(corpusData);
      setEditedCorpus(corpusData);
      setUserDetails(details);
      setEditedSettings(details);
      setEditedLoops(details.open_loops || {});
      setMessageCount(messages.length);
      setEditingCorpus(false);
      setEditingSettings(false);
      setEditingLoops(false);
    } catch (error) {
      console.error('Failed to load user data:', error);
      alert('Failed to load user data.');
    } finally {
      setLoading(false);
    }
  };

  const handleSaveCorpus = async () => {
    if (!selectedUser) return;
    setSaving(true);
    try {
      await updateUserCorpus(selectedUser.phone_number, editedCorpus);
      setCorpus(editedCorpus);
      setEditingCorpus(false);
      alert('Corpus saved successfully!');
    } catch (error) {
      console.error('Failed to save corpus:', error);
      alert('Failed to save corpus.');
    } finally {
      setSaving(false);
    }
  };

  const handleResetCorpus = async () => {
    if (!selectedUser) return;
    if (!confirm('Are you sure you want to reset the corpus? This will delete all knowledge and cannot be undone.')) {
      return;
    }

    setSaving(true);
    try {
      await resetUserCorpus(selectedUser.phone_number);
      // Reload data
      await loadUserData(selectedUser);
      alert('Corpus reset successfully!');
    } catch (error) {
      console.error('Failed to reset corpus:', error);
      alert('Failed to reset corpus.');
    } finally {
      setSaving(false);
    }
  };

  const handleDeleteMessages = async () => {
    if (!selectedUser) return;
    if (!confirm(`Are you sure you want to delete ALL ${messageCount} messages? This cannot be undone.`)) {
      return;
    }

    setSaving(true);
    try {
      const count = await deleteUserMessages(selectedUser.phone_number);
      setMessageCount(0);
      alert(`Deleted ${count} messages successfully!`);
    } catch (error) {
      console.error('Failed to delete messages:', error);
      alert('Failed to delete messages.');
    } finally {
      setSaving(false);
    }
  };

  const handleSaveSettings = async () => {
    if (!selectedUser || !editedSettings) return;
    setSaving(true);
    try {
      await updateUserSettings(selectedUser.phone_number, {
        display_name: editedSettings.display_name,
        timezone: editedSettings.timezone,
        quiet_hours_start: editedSettings.quiet_hours_start,
        quiet_hours_end: editedSettings.quiet_hours_end,
        onboarding_step: editedSettings.onboarding_step,
      });
      setUserDetails(editedSettings as UserDetails);
      setEditingSettings(false);
      alert('Settings saved successfully!');
    } catch (error) {
      console.error('Failed to save settings:', error);
      alert('Failed to save settings.');
    } finally {
      setSaving(false);
    }
  };

  const handleSaveLoops = async () => {
    if (!selectedUser) return;
    setSaving(true);
    try {
      await updateUserSettings(selectedUser.phone_number, {
        open_loops: editedLoops,
      });
      if (userDetails) {
        setUserDetails({ ...userDetails, open_loops: editedLoops });
      }
      setEditingLoops(false);
      alert('Open loops saved successfully!');
    } catch (error) {
      console.error('Failed to save loops:', error);
      alert('Failed to save loops.');
    } finally {
      setSaving(false);
    }
  };

  const tabs: { id: Tab; label: string; icon: string }[] = [
    { id: 'corpus', label: 'Knowledge Graph', icon: '📚' },
    { id: 'settings', label: 'Settings', icon: '⚙️' },
    { id: 'loops', label: 'Open Loops', icon: '🔄' },
    { id: 'messages', label: 'Messages', icon: '💬' },
  ];

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
    <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
      {/* User List */}
      <div className="lg:col-span-1">
        <div className="bg-white rounded-lg shadow">
          <div className="px-6 py-4 border-b border-gray-200">
            <h2 className="text-lg font-semibold text-gray-900">Users ({users.length})</h2>
            <p className="text-sm text-gray-500">Select to manage</p>
          </div>

          <div className="divide-y divide-gray-200 max-h-[700px] overflow-y-auto">
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
                  Last: {formatDistanceToNow(new Date(user.last_message_at), { addSuffix: true })}
                </p>
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="lg:col-span-3">
        {selectedUser ? (
          <div className="bg-white rounded-lg shadow">
            {/* Header */}
            <div className="px-6 py-4 border-b border-gray-200">
              <div className="flex items-center justify-between mb-4">
                <div>
                  <h3 className="text-lg font-semibold text-gray-900">
                    {userDetails?.display_name || selectedUser.phone_number}
                  </h3>
                  <p className="text-sm text-gray-500">
                    {messageCount} messages • Onboarding: {userDetails?.onboarding_step === 99 ? 'Complete ✅' : `Step ${userDetails?.onboarding_step}`}
                  </p>
                </div>
              </div>

              {/* Tabs */}
              <div className="flex space-x-1 border-b border-gray-200">
                {tabs.map((tab) => (
                  <button
                    key={tab.id}
                    onClick={() => setActiveTab(tab.id)}
                    className={`px-4 py-2 text-sm font-medium transition ${
                      activeTab === tab.id
                        ? 'text-blue-600 border-b-2 border-blue-600'
                        : 'text-gray-500 hover:text-gray-700'
                    }`}
                  >
                    {tab.icon} {tab.label}
                  </button>
                ))}
              </div>
            </div>

            {/* Tab Content */}
            <div className="p-6">
              {loading ? (
                <div className="flex items-center justify-center py-12">
                  <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
                </div>
              ) : (
                <>
                  {/* Corpus Tab */}
                  {activeTab === 'corpus' && (
                    <div>
                      <div className="flex gap-3 mb-4">
                        <button
                          onClick={() => setEditingCorpus(!editingCorpus)}
                          className="px-4 py-2 text-sm font-medium text-blue-600 bg-blue-50 rounded-lg hover:bg-blue-100"
                        >
                          {editingCorpus ? 'Cancel Edit' : 'Edit Corpus'}
                        </button>
                        <button
                          onClick={handleResetCorpus}
                          disabled={saving}
                          className="px-4 py-2 text-sm font-medium text-red-600 bg-red-50 rounded-lg hover:bg-red-100 disabled:opacity-50"
                        >
                          Reset Corpus
                        </button>
                      </div>

                      {editingCorpus ? (
                        <div>
                          <textarea
                            value={editedCorpus}
                            onChange={(e) => setEditedCorpus(e.target.value)}
                            rows={20}
                            className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 outline-none font-mono text-sm text-gray-900"
                          />
                          <div className="mt-4 flex gap-3">
                            <button
                              onClick={handleSaveCorpus}
                              disabled={saving}
                              className="px-6 py-2 bg-green-600 hover:bg-green-700 text-white font-semibold rounded-lg disabled:opacity-50"
                            >
                              {saving ? 'Saving...' : 'Save Changes'}
                            </button>
                            <button
                              onClick={() => {
                                setEditedCorpus(corpus);
                                setEditingCorpus(false);
                              }}
                              className="px-6 py-2 bg-gray-200 hover:bg-gray-300 text-gray-700 font-semibold rounded-lg"
                            >
                              Discard
                            </button>
                          </div>
                        </div>
                      ) : (
                        <div className="prose prose-sm max-w-none text-gray-900">
                          <ReactMarkdown>{corpus}</ReactMarkdown>
                        </div>
                      )}
                    </div>
                  )}

                  {/* Settings Tab */}
                  {activeTab === 'settings' && userDetails && (
                    <div>
                      <div className="flex gap-3 mb-6">
                        <button
                          onClick={() => setEditingSettings(!editingSettings)}
                          className="px-4 py-2 text-sm font-medium text-blue-600 bg-blue-50 rounded-lg hover:bg-blue-100"
                        >
                          {editingSettings ? 'Cancel' : 'Edit Settings'}
                        </button>
                      </div>

                      <div className="space-y-6">
                        {/* Display Name */}
                        <div>
                          <label className="block text-sm font-medium text-gray-700 mb-2">Display Name</label>
                          <input
                            type="text"
                            value={editingSettings ? (editedSettings.display_name || '') : (userDetails.display_name || '')}
                            onChange={(e) => setEditedSettings({ ...editedSettings, display_name: e.target.value })}
                            disabled={!editingSettings}
                            className="w-full px-4 py-2 border border-gray-300 rounded-lg text-gray-900 disabled:bg-gray-50"
                          />
                        </div>

                        {/* Timezone */}
                        <div>
                          <label className="block text-sm font-medium text-gray-700 mb-2">Timezone</label>
                          <input
                            type="text"
                            value={editingSettings ? (editedSettings.timezone || '') : (userDetails.timezone || '')}
                            onChange={(e) => setEditedSettings({ ...editedSettings, timezone: e.target.value })}
                            disabled={!editingSettings}
                            className="w-full px-4 py-2 border border-gray-300 rounded-lg text-gray-900 disabled:bg-gray-50"
                            placeholder="Europe/Amsterdam"
                          />
                        </div>

                        {/* Quiet Hours */}
                        <div className="grid grid-cols-2 gap-4">
                          <div>
                            <label className="block text-sm font-medium text-gray-700 mb-2">Quiet Hours Start</label>
                            <input
                              type="number"
                              min="0"
                              max="23"
                              value={editingSettings ? (editedSettings.quiet_hours_start || 22) : (userDetails.quiet_hours_start || 22)}
                              onChange={(e) => setEditedSettings({ ...editedSettings, quiet_hours_start: parseInt(e.target.value) })}
                              disabled={!editingSettings}
                              className="w-full px-4 py-2 border border-gray-300 rounded-lg text-gray-900 disabled:bg-gray-50"
                            />
                          </div>
                          <div>
                            <label className="block text-sm font-medium text-gray-700 mb-2">Quiet Hours End</label>
                            <input
                              type="number"
                              min="0"
                              max="23"
                              value={editingSettings ? (editedSettings.quiet_hours_end || 9) : (userDetails.quiet_hours_end || 9)}
                              onChange={(e) => setEditedSettings({ ...editedSettings, quiet_hours_end: parseInt(e.target.value) })}
                              disabled={!editingSettings}
                              className="w-full px-4 py-2 border border-gray-300 rounded-lg text-gray-900 disabled:bg-gray-50"
                            />
                          </div>
                        </div>

                        {/* Onboarding Step */}
                        <div>
                          <label className="block text-sm font-medium text-gray-700 mb-2">Onboarding Step</label>
                          <input
                            type="number"
                            min="0"
                            max="99"
                            value={editingSettings ? (editedSettings.onboarding_step || 0) : (userDetails.onboarding_step || 0)}
                            onChange={(e) => setEditedSettings({ ...editedSettings, onboarding_step: parseInt(e.target.value) })}
                            disabled={!editingSettings}
                            className="w-full px-4 py-2 border border-gray-300 rounded-lg text-gray-900 disabled:bg-gray-50"
                          />
                          <p className="text-xs text-gray-500 mt-1">0=New, 1-3=Onboarding, 99=Complete</p>
                        </div>

                        {editingSettings && (
                          <div className="flex gap-3">
                            <button
                              onClick={handleSaveSettings}
                              disabled={saving}
                              className="px-6 py-2 bg-green-600 hover:bg-green-700 text-white font-semibold rounded-lg disabled:opacity-50"
                            >
                              {saving ? 'Saving...' : 'Save Settings'}
                            </button>
                            <button
                              onClick={() => {
                                setEditedSettings(userDetails);
                                setEditingSettings(false);
                              }}
                              className="px-6 py-2 bg-gray-200 hover:bg-gray-300 text-gray-700 font-semibold rounded-lg"
                            >
                              Cancel
                            </button>
                          </div>
                        )}
                      </div>
                    </div>
                  )}

                  {/* Open Loops Tab */}
                  {activeTab === 'loops' && userDetails && (
                    <div>
                      <div className="flex gap-3 mb-6">
                        <button
                          onClick={() => setEditingLoops(!editingLoops)}
                          className="px-4 py-2 text-sm font-medium text-blue-600 bg-blue-50 rounded-lg hover:bg-blue-100"
                        >
                          {editingLoops ? 'Cancel' : 'Edit as JSON'}
                        </button>
                      </div>

                      {editingLoops ? (
                        <div>
                          <textarea
                            value={JSON.stringify(editedLoops, null, 2)}
                            onChange={(e) => {
                              try {
                                setEditedLoops(JSON.parse(e.target.value));
                              } catch (error) {
                                // Invalid JSON, ignore
                              }
                            }}
                            rows={15}
                            className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 outline-none font-mono text-sm text-gray-900"
                          />
                          <div className="mt-4 flex gap-3">
                            <button
                              onClick={handleSaveLoops}
                              disabled={saving}
                              className="px-6 py-2 bg-green-600 hover:bg-green-700 text-white font-semibold rounded-lg disabled:opacity-50"
                            >
                              {saving ? 'Saving...' : 'Save Loops'}
                            </button>
                            <button
                              onClick={() => {
                                setEditedLoops(userDetails.open_loops || {});
                                setEditingLoops(false);
                              }}
                              className="px-6 py-2 bg-gray-200 hover:bg-gray-300 text-gray-700 font-semibold rounded-lg"
                            >
                              Cancel
                            </button>
                          </div>
                        </div>
                      ) : (
                        <div>
                          {Object.keys(userDetails.open_loops || {}).length === 0 ? (
                            <p className="text-gray-500 text-center py-8">No open loops yet</p>
                          ) : (
                            <div className="space-y-4">
                              {Object.entries(userDetails.open_loops || {}).map(([topic, data]: [string, any]) => (
                                <div key={topic} className="border border-gray-200 rounded-lg p-4">
                                  <div className="flex items-start justify-between mb-2">
                                    <h4 className="font-semibold text-gray-900">{topic}</h4>
                                    <span className={`px-2 py-1 text-xs rounded ${
                                      data.status === 'active' ? 'bg-green-100 text-green-700' :
                                      data.status === 'decaying' ? 'bg-yellow-100 text-yellow-700' :
                                      'bg-gray-100 text-gray-700'
                                    }`}>
                                      {data.status}
                                    </span>
                                  </div>
                                  <p className="text-sm text-gray-600 mb-2">{data.description}</p>
                                  <div className="text-xs text-gray-500 space-y-1">
                                    <p>Weight: {data.weight}/5</p>
                                    <p>Last Updated: {new Date(data.last_updated).toLocaleDateString()}</p>
                                    {data.next_event_date && <p>Next Event: {new Date(data.next_event_date).toLocaleDateString()}</p>}
                                  </div>
                                </div>
                              ))}
                            </div>
                          )}
                        </div>
                      )}
                    </div>
                  )}

                  {/* Messages Tab */}
                  {activeTab === 'messages' && (
                    <div>
                      <div className="mb-6">
                        <h4 className="text-lg font-semibold text-gray-900 mb-2">Message Management</h4>
                        <p className="text-sm text-gray-500 mb-4">Total messages: {messageCount}</p>
                        <button
                          onClick={handleDeleteMessages}
                          disabled={saving || messageCount === 0}
                          className="px-6 py-2 bg-red-600 hover:bg-red-700 text-white font-semibold rounded-lg disabled:opacity-50"
                        >
                          {saving ? 'Deleting...' : 'Delete All Messages'}
                        </button>
                      </div>

                      <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
                        <p className="text-sm text-yellow-800">
                          ⚠️ <strong>Warning:</strong> Deleting messages cannot be undone. The message history will be permanently removed from the database.
                        </p>
                      </div>
                    </div>
                  )}
                </>
              )}
            </div>
          </div>
        ) : (
          <div className="bg-white rounded-lg shadow p-12 text-center text-gray-500">
            <svg className="mx-auto h-16 w-16 text-gray-400 mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4.354a4 4 0 110 5.292M15 21H3v-1a6 6 0 0112 0v1zm0 0h6v-1a6 6 0 00-9-5.197M13 7a4 4 0 11-8 0 4 4 0 018 0z" />
            </svg>
            <p className="text-lg font-medium text-gray-900 mb-1">No user selected</p>
            <p className="text-sm">Select a user from the list to manage their data</p>
          </div>
        )}
      </div>
    </div>
  );
}
