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
      <div className="bg-white rounded-lg shadow p-6">
        <h2 className="text-lg font-semibold mb-4">⏳ Pending Nudges</h2>
        <div className="text-center py-4 text-gray-500">Loading...</div>
      </div>
    );
  }

  if (nudges.length === 0) {
    return (
      <div className="bg-white rounded-lg shadow p-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold">⏳ Pending Nudges</h2>
          <span className="text-sm text-gray-500">Auto-refreshes every 30s</span>
        </div>
        <div className="text-center py-8 text-gray-500">
          <p>✨ No pending nudges</p>
          <p className="text-sm mt-2">Nudges will appear here for your approval before sending</p>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-lg shadow p-6 mb-6">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-lg font-semibold">⏳ Pending Nudges ({nudges.length})</h2>
        <button
          onClick={loadNudges}
          className="text-sm text-blue-600 hover:text-blue-700"
        >
          Refresh
        </button>
      </div>

      <div className="space-y-4">
        {nudges.map((nudge) => (
          <div key={nudge.id} className="border border-gray-200 rounded-lg p-4 hover:border-blue-300 transition">
            {/* Header */}
            <div className="flex items-start justify-between mb-3">
              <div>
                <h3 className="font-semibold text-gray-900">{nudge.display_name || nudge.phone_number}</h3>
                <p className="text-sm text-gray-500">
                  Topic: <span className="font-medium text-gray-700">{nudge.topic}</span> (Weight: {nudge.weight}/5)
                </p>
              </div>
              <span className="text-xs bg-yellow-100 text-yellow-700 px-2 py-1 rounded">
                Pending Approval
              </span>
            </div>

            {/* Message */}
            {editingId === nudge.id ? (
              <div className="mb-3">
                <textarea
                  value={editedText}
                  onChange={(e) => setEditedText(e.target.value)}
                  rows={4}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 outline-none text-sm"
                />
              </div>
            ) : (
              <div className="bg-blue-50 border border-blue-200 rounded-lg p-3 mb-3">
                <p className="text-sm text-gray-800 whitespace-pre-wrap">{nudge.message_text}</p>
              </div>
            )}

            {/* Metadata */}
            <div className="text-xs text-gray-500 mb-3 space-y-1">
              <p>
                Scheduled: <span className="font-medium text-gray-700">
                  {new Date(nudge.scheduled_send_time).toLocaleString()}
                  ({formatDistanceToNow(new Date(nudge.scheduled_send_time), { addSuffix: true })})
                </span>
              </p>
              <p>
                Created: {formatDistanceToNow(new Date(nudge.created_at), { addSuffix: true })}
              </p>
            </div>

            {/* Actions */}
            <div className="flex gap-2">
              {editingId === nudge.id ? (
                <>
                  <button
                    onClick={() => handleSaveEdit(nudge.id)}
                    disabled={processing === nudge.id}
                    className="flex-1 px-4 py-2 bg-green-600 hover:bg-green-700 text-white text-sm font-medium rounded-lg disabled:opacity-50"
                  >
                    {processing === nudge.id ? 'Saving...' : 'Save'}
                  </button>
                  <button
                    onClick={() => setEditingId(null)}
                    disabled={processing === nudge.id}
                    className="px-4 py-2 bg-gray-200 hover:bg-gray-300 text-gray-700 text-sm font-medium rounded-lg disabled:opacity-50"
                  >
                    Cancel
                  </button>
                </>
              ) : (
                <>
                  <button
                    onClick={() => handleEdit(nudge)}
                    disabled={processing === nudge.id}
                    className="px-4 py-2 bg-white border border-gray-300 text-gray-700 text-sm font-medium rounded-lg hover:bg-gray-50 disabled:opacity-50"
                  >
                    Edit
                  </button>
                  <button
                    onClick={() => handleApprove(nudge.id)}
                    disabled={processing === nudge.id}
                    className="flex-1 px-4 py-2 bg-green-600 hover:bg-green-700 text-white text-sm font-semibold rounded-lg disabled:opacity-50"
                  >
                    {processing === nudge.id ? 'Approving...' : '✓ Approve & Send'}
                  </button>
                  <button
                    onClick={() => handleSkip(nudge.id)}
                    disabled={processing === nudge.id}
                    className="px-4 py-2 bg-red-600 hover:bg-red-700 text-white text-sm font-medium rounded-lg disabled:opacity-50"
                  >
                    {processing === nudge.id ? 'Skipping...' : '✕ Skip'}
                  </button>
                </>
              )}
            </div>
          </div>
        ))}
      </div>

      <div className="mt-4 p-3 bg-blue-50 border border-blue-200 rounded-lg">
        <p className="text-xs text-blue-800">
          <strong>ℹ️ How it works:</strong> Approve nudges to send them at the scheduled time. Edit the message before approving if needed. Skipped nudges won't be sent.
        </p>
      </div>
    </div>
  );
}
