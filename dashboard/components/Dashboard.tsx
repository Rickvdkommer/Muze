'use client';

import { useState, useEffect } from 'react';
import { clearAuthCookie } from '@/lib/auth';
import {
  getUnprocessedMessages,
  getUserMessages,
  getUserCorpus,
  generateAIResponse,
  sendWhatsAppMessage,
  markMessageProcessed,
  Message,
} from '@/lib/api';
import MessageQueue from './MessageQueue';
import MessageDetail from './MessageDetail';
import UserManagement from './UserManagement';

interface DashboardProps {
  onLogout: () => void;
}

export default function Dashboard({ onLogout }: DashboardProps) {
  const [activeTab, setActiveTab] = useState<'queue' | 'users'>('queue');
  const [messages, setMessages] = useState<Message[]>([]);
  const [selectedMessage, setSelectedMessage] = useState<Message | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  const loadMessages = async () => {
    try {
      setRefreshing(true);
      const data = await getUnprocessedMessages(100);
      setMessages(data);
    } catch (error) {
      console.error('Failed to load messages:', error);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => {
    loadMessages();
    // Auto-refresh every 30 seconds
    const interval = setInterval(loadMessages, 30000);
    return () => clearInterval(interval);
  }, []);

  const handleLogout = () => {
    clearAuthCookie();
    onLogout();
  };

  const handleMessageSelect = (message: Message) => {
    setSelectedMessage(message);
  };

  const handleMessageProcessed = async () => {
    await loadMessages();
    setSelectedMessage(null);
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-xl">Loading dashboard...</div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white shadow-sm border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-2xl font-bold text-gray-900">Muze Admin</h1>
              <p className="text-sm text-gray-500">Human-in-the-loop message management</p>
            </div>
            <div className="flex items-center gap-4">
              <button
                onClick={loadMessages}
                disabled={refreshing}
                className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 disabled:opacity-50"
              >
                {refreshing ? 'Refreshing...' : 'Refresh'}
              </button>
              <button
                onClick={handleLogout}
                className="px-4 py-2 text-sm font-medium text-white bg-red-600 rounded-lg hover:bg-red-700"
              >
                Logout
              </button>
            </div>
          </div>
        </div>
      </header>

      {/* Tabs */}
      <div className="bg-white border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <nav className="flex space-x-8" aria-label="Tabs">
            <button
              onClick={() => setActiveTab('queue')}
              className={`py-4 px-1 border-b-2 font-medium text-sm ${
                activeTab === 'queue'
                  ? 'border-blue-500 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`}
            >
              Message Queue
              {messages.length > 0 && (
                <span className="ml-2 bg-blue-100 text-blue-600 py-0.5 px-2 rounded-full text-xs font-semibold">
                  {messages.length}
                </span>
              )}
            </button>
            <button
              onClick={() => setActiveTab('users')}
              className={`py-4 px-1 border-b-2 font-medium text-sm ${
                activeTab === 'users'
                  ? 'border-blue-500 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`}
            >
              Users & Corpus
            </button>
          </nav>
        </div>
      </div>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {activeTab === 'queue' ? (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
            <div>
              <MessageQueue
                messages={messages}
                selectedMessage={selectedMessage}
                onSelect={handleMessageSelect}
              />
            </div>
            <div>
              {selectedMessage ? (
                <MessageDetail
                  message={selectedMessage}
                  onProcessed={handleMessageProcessed}
                />
              ) : (
                <div className="bg-white rounded-lg shadow p-8 text-center text-gray-500">
                  Select a message to view details and respond
                </div>
              )}
            </div>
          </div>
        ) : (
          <UserManagement />
        )}
      </main>
    </div>
  );
}
