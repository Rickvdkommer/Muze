'use client';

import { useState, useEffect } from 'react';
import { getPendingNudges, updatePendingNudge, approvePendingNudge, skipPendingNudge, PendingNudge } from '@/lib/api';
import { formatDistanceToNow } from 'date-fns';

export default function PendingNudges() {
  const [nudges, setNudges] = useState<PendingNudge[]>([]);
  const [loading, setLoading] = useState(true);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [editedText, setEditedText] = useState('');
  const [processing, setProcessing] = useState<number | null>(null);

  useEffect(() => {
    loadNudges();
    // Auto-refresh every 30 seconds
    const interval = setInterval(loadNudges, 30000);
    return () => clearInterval(interval);
  }, []);

  const loadNudges = async () => {
    try {
      const data = await getPendingNudges();
      setNudges(data);
    } catch (error) {
      console.error('Failed to load pending nudges:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleEdit = (nudge: PendingNudge) => {
    setEditingId(nudge.id);
    setEditedText(nudge.message_text);
  };

  const handleSaveEdit = async (nudgeId: number) => {
    setProcessing(nudgeId);
    try {
      await updatePendingNudge(nudgeId, editedText);
      await loadNudges();
      setEditingId(null);
    } catch (error) {
      console.error('Failed to update nudge:', error);
      alert('Failed to update message');
    } finally {
      setProcessing(null);
    }
  };

  const handleApprove = async (nudgeId: number) => {
    if (!confirm('Approve this nudge? It will be sent at the scheduled time.')) return;
    setProcessing(nudgeId);
    try {
      await approvePendingNudge(nudgeId);
      await loadNudges();
    } catch (error) {
      console.error('Failed to approve nudge:', error);
      alert('Failed to approve nudge');
    } finally {
      setProcessing(null);
    }
  };

  const handleSkip = async (nudgeId: number) => {
    if (!confirm('Skip this nudge? It will not be sent.')) return;
    setProcessing(nudgeId);
    try {
      await skipPendingNudge(nudgeId);
      await loadNudges();
    } catch (error) {
      console.error('Failed to skip nudge:', error);
      alert('Failed to skip nudge');
    } finally {
      setProcessing(null);
    }
  };

  if (loading) {
    return (
      <div className="bg-gradient-to-br from-purple-50 to-blue-50 rounded-xl shadow-sm border border-purple-100 p-6 mb-6">
        <div className="flex items-center gap-3 mb-4">
          <div className="w-10 h-10 bg-purple-100 rounded-lg flex items-center justify-center">
            <span className="text-2xl">⏳</span>
          </div>
          <h2 className="text-xl font-bold text-gray-900">Pending Nudges</h2>
        </div>
        <div className="text-center py-4 text-gray-500">Loading...</div>
      </div>
    );
  }

  if (nudges.length === 0) {
    return (
      <div className="bg-gradient-to-br from-purple-50 to-blue-50 rounded-xl shadow-sm border border-purple-100 p-6 mb-6">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-purple-100 rounded-lg flex items-center justify-center">
              <span className="text-2xl">⏳</span>
            </div>
            <div>
              <h2 className="text-xl font-bold text-gray-900">Pending Nudges</h2>
              <p className="text-xs text-purple-600">Auto-refreshes every 30s</p>
            </div>
          </div>
        </div>
        <div className="text-center py-8">
          <div className="w-16 h-16 bg-white rounded-full flex items-center justify-center mx-auto mb-3 shadow-sm">
            <span className="text-3xl">✨</span>
          </div>
          <p className="text-gray-700 font-medium">No pending nudges</p>
          <p className="text-sm text-gray-500 mt-2">Nudges created by the hourly cron will appear here for approval</p>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-gradient-to-br from-purple-50 to-blue-50 rounded-xl shadow-sm border border-purple-100 p-6 mb-6">
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 bg-purple-500 rounded-lg flex items-center justify-center shadow-sm">
            <span className="text-2xl">🔔</span>
          </div>
          <div>
            <h2 className="text-xl font-bold text-gray-900">Pending Nudges ({nudges.length})</h2>
            <p className="text-xs text-purple-600">Awaiting your approval</p>
          </div>
        </div>
        <button
          onClick={loadNudges}
          className="px-4 py-2 bg-white border border-purple-200 text-purple-700 text-sm font-medium rounded-lg hover:bg-purple-50 transition shadow-sm"
        >
          ↻ Refresh
        </button>
      </div>

      <div className="space-y-4">
        {nudges.map((nudge) => (
          <div key={nudge.id} className="bg-white border-2 border-purple-200 rounded-xl p-5 hover:border-purple-400 hover:shadow-md transition-all">
            {/* Header */}
            <div className="flex items-start justify-between mb-4">
              <div>
                <h3 className="font-bold text-gray-900 text-lg">{nudge.display_name || nudge.phone_number}</h3>
                <div className="flex items-center gap-3 mt-1">
                  <span className="text-sm text-gray-600">
                    📌 <span className="font-semibold text-purple-700">{nudge.topic}</span>
                  </span>
                  <span className="text-xs bg-purple-100 text-purple-700 px-2 py-1 rounded-full font-medium">
                    Priority: {nudge.weight}/5
                  </span>
                </div>
              </div>
              <span className="text-xs bg-yellow-100 text-yellow-700 px-3 py-1.5 rounded-full font-semibold shadow-sm">
                ⏸️ Awaiting Approval
              </span>
            </div>

            {/* Message */}
            {editingId === nudge.id ? (
              <div className="mb-4">
                <label className="block text-sm font-medium text-gray-700 mb-2">Edit Message:</label>
                <textarea
                  value={editedText}
                  onChange={(e) => setEditedText(e.target.value)}
                  rows={4}
                  className="w-full px-4 py-3 border-2 border-purple-200 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-purple-500 outline-none text-sm shadow-sm"
                />
              </div>
            ) : (
              <div className="bg-gradient-to-br from-blue-50 to-purple-50 border-2 border-blue-200 rounded-lg p-4 mb-4 shadow-sm">
                <p className="text-sm font-medium text-gray-800 leading-relaxed whitespace-pre-wrap">{nudge.message_text}</p>
              </div>
            )}

            {/* Metadata */}
            <div className="bg-gray-50 rounded-lg p-3 mb-4 border border-gray-200">
              <div className="grid grid-cols-2 gap-3 text-xs">
                <div>
                  <span className="text-gray-500">📅 Scheduled:</span>
                  <p className="font-semibold text-gray-900 mt-0.5">
                    {new Date(nudge.scheduled_send_time).toLocaleString('en-US', {
                      month: 'short',
                      day: 'numeric',
                      hour: '2-digit',
                      minute: '2-digit'
                    })}
                  </p>
                  <p className="text-purple-600 font-medium">
                    {formatDistanceToNow(new Date(nudge.scheduled_send_time), { addSuffix: true })}
                  </p>
                </div>
                <div>
                  <span className="text-gray-500">🕒 Created:</span>
                  <p className="font-semibold text-gray-900 mt-0.5">
                    {formatDistanceToNow(new Date(nudge.created_at), { addSuffix: true })}
                  </p>
                </div>
              </div>
            </div>

            {/* Actions */}
            <div className="flex gap-3">
              {editingId === nudge.id ? (
                <>
                  <button
                    onClick={() => handleSaveEdit(nudge.id)}
                    disabled={processing === nudge.id}
                    className="flex-1 px-5 py-3 bg-gradient-to-r from-green-500 to-green-600 hover:from-green-600 hover:to-green-700 text-white text-sm font-bold rounded-lg shadow-md disabled:opacity-50 disabled:cursor-not-allowed transition"
                  >
                    {processing === nudge.id ? '💾 Saving...' : '💾 Save Changes'}
                  </button>
                  <button
                    onClick={() => setEditingId(null)}
                    disabled={processing === nudge.id}
                    className="px-5 py-3 bg-gray-100 hover:bg-gray-200 text-gray-700 text-sm font-semibold rounded-lg disabled:opacity-50 transition"
                  >
                    Cancel
                  </button>
                </>
              ) : (
                <>
                  <button
                    onClick={() => handleEdit(nudge)}
                    disabled={processing === nudge.id}
                    className="px-5 py-3 bg-white border-2 border-purple-300 text-purple-700 text-sm font-semibold rounded-lg hover:bg-purple-50 hover:border-purple-400 disabled:opacity-50 shadow-sm transition"
                  >
                    ✏️ Edit
                  </button>
                  <button
                    onClick={() => handleApprove(nudge.id)}
                    disabled={processing === nudge.id}
                    className="flex-1 px-5 py-3 bg-gradient-to-r from-green-500 to-emerald-600 hover:from-green-600 hover:to-emerald-700 text-white text-sm font-bold rounded-lg shadow-md disabled:opacity-50 disabled:cursor-not-allowed transition"
                  >
                    {processing === nudge.id ? '⏳ Approving...' : '✅ Approve & Send'}
                  </button>
                  <button
                    onClick={() => handleSkip(nudge.id)}
                    disabled={processing === nudge.id}
                    className="px-5 py-3 bg-gradient-to-r from-red-500 to-red-600 hover:from-red-600 hover:to-red-700 text-white text-sm font-bold rounded-lg shadow-md disabled:opacity-50 disabled:cursor-not-allowed transition"
                  >
                    {processing === nudge.id ? '⏳ Skipping...' : '❌ Skip'}
                  </button>
                </>
              )}
            </div>
          </div>
        ))}
      </div>

      <div className="mt-6 p-4 bg-white border-2 border-blue-200 rounded-xl">
        <p className="text-sm text-gray-700 leading-relaxed">
          <strong className="text-blue-700">💡 How it works:</strong> These nudges were created by the hourly cron job.
          Approve them to send at the scheduled time (respecting quiet hours). Edit the message first if needed.
          Skipped nudges won't be sent.
        </p>
      </div>
    </div>
  );
}
