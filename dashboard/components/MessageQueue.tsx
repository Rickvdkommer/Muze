'use client';

import { Message } from '@/lib/api';
import { formatDistanceToNow } from 'date-fns';

interface MessageQueueProps {
  messages: Message[];
  selectedMessage: Message | null;
  onSelect: (message: Message) => void;
}

export default function MessageQueue({ messages, selectedMessage, onSelect }: MessageQueueProps) {
  if (messages.length === 0) {
    return (
      <div className="bg-white rounded-lg shadow p-8 text-center">
        <div className="text-gray-400 mb-2">
          <svg
            className="mx-auto h-12 w-12"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M20 13V6a2 2 0 00-2-2H6a2 2 0 00-2 2v7m16 0v5a2 2 0 01-2 2H6a2 2 0 01-2-2v-5m16 0h-2.586a1 1 0 00-.707.293l-2.414 2.414a1 1 0 01-.707.293h-3.172a1 1 0 01-.707-.293l-2.414-2.414A1 1 0 006.586 13H4"
            />
          </svg>
        </div>
        <h3 className="text-lg font-medium text-gray-900 mb-1">No pending messages</h3>
        <p className="text-sm text-gray-500">All messages have been processed!</p>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-lg shadow">
      <div className="px-6 py-4 border-b border-gray-200">
        <h2 className="text-lg font-semibold text-gray-900">
          Unprocessed Messages ({messages.length})
        </h2>
        <p className="text-sm text-gray-500">Click on a message to respond</p>
      </div>

      <div className="divide-y divide-gray-200 max-h-[600px] overflow-y-auto">
        {messages.map((message) => (
          <button
            key={message.id}
            onClick={() => onSelect(message)}
            className={`w-full text-left px-6 py-4 hover:bg-gray-50 transition ${
              selectedMessage?.id === message.id ? 'bg-blue-50 border-l-4 border-blue-500' : ''
            }`}
          >
            <div className="flex items-start justify-between mb-2">
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium text-gray-900 truncate">
                  {message.phone_number}
                </p>
                <p className="text-xs text-gray-500">
                  {formatDistanceToNow(new Date(message.timestamp), { addSuffix: true })}
                </p>
              </div>
              <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-yellow-100 text-yellow-800">
                Pending
              </span>
            </div>
            <p className="text-sm text-gray-700 line-clamp-2">{message.text}</p>
          </button>
        ))}
      </div>
    </div>
  );
}
