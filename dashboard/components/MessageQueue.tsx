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
      <div className="bg-gradient-to-br from-green-50 to-teal-50 rounded-xl shadow-sm border border-green-100 p-8">
        <div className="text-center">
          <div className="w-16 h-16 bg-white rounded-full flex items-center justify-center mx-auto mb-3 shadow-sm">
            <span className="text-3xl">✅</span>
          </div>
          <h3 className="text-lg font-bold text-gray-900 mb-1">No pending messages</h3>
          <p className="text-sm text-gray-600">All messages have been processed!</p>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-gradient-to-br from-orange-50 to-pink-50 rounded-xl shadow-sm border border-orange-100">
      <div className="px-6 py-4 border-b-2 border-orange-200">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 bg-orange-500 rounded-lg flex items-center justify-center shadow-sm">
            <span className="text-2xl">💬</span>
          </div>
          <div>
            <h2 className="text-xl font-bold text-gray-900">
              Unprocessed Messages ({messages.length})
            </h2>
            <p className="text-xs text-orange-600">Click on a message to respond</p>
          </div>
        </div>
      </div>

      <div className="divide-y divide-orange-100 max-h-[600px] overflow-y-auto">
        {messages.map((message) => (
          <button
            key={message.id}
            onClick={() => onSelect(message)}
            className={`w-full text-left px-6 py-4 hover:bg-white/50 transition-all ${
              selectedMessage?.id === message.id
                ? 'bg-white border-l-4 border-orange-500 shadow-sm'
                : 'bg-transparent'
            }`}
          >
            <div className="flex items-start justify-between mb-2">
              <div className="flex-1 min-w-0">
                <p className="text-sm font-bold text-gray-900 truncate">
                  {message.phone_number}
                </p>
                <p className="text-xs text-orange-600 font-medium">
                  {formatDistanceToNow(new Date(message.timestamp), { addSuffix: true })}
                </p>
              </div>
              <span className="inline-flex items-center px-2.5 py-1 rounded-full text-xs font-bold bg-yellow-100 text-yellow-700 shadow-sm">
                ⏸️ Pending
              </span>
            </div>
            <p className="text-sm text-gray-700 line-clamp-2 font-medium">{message.text}</p>
          </button>
        ))}
      </div>
    </div>
  );
}
