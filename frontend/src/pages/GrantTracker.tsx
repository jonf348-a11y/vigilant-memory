import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  Loader2,
  Filter,
  MessageSquare,
  Trash2,
  StickyNote,
} from "lucide-react";
import { api } from "../api";
import type { Grant, GrantStatus } from "../types";
import GrantCard from "../components/GrantCard";

const STATUSES: { value: string; label: string }[] = [
  { value: "", label: "All" },
  { value: "discovered", label: "Discovered" },
  { value: "reviewing", label: "Reviewing" },
  { value: "applied", label: "Applied" },
  { value: "awarded", label: "Awarded" },
  { value: "rejected", label: "Rejected" },
  { value: "not_eligible", label: "Not Eligible" },
];

export default function GrantTracker() {
  const [grants, setGrants] = useState<Grant[]>([]);
  const [loading, setLoading] = useState(true);
  const [filterStatus, setFilterStatus] = useState("");
  const [editing, setEditing] = useState<Grant | null>(null);
  const [noteText, setNoteText] = useState("");
  const [saving, setSaving] = useState(false);
  const navigate = useNavigate();

  const load = (status?: string) => {
    setLoading(true);
    api
      .listGrants(status || undefined)
      .then(setGrants)
      .catch(console.error)
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    load(filterStatus);
  }, [filterStatus]);

  const updateStatus = async (grant: Grant, status: GrantStatus) => {
    const updated = await api.updateGrant(grant.id, { status });
    setGrants((prev) => prev.map((g) => (g.id === updated.id ? updated : g)));
  };

  const saveNotes = async () => {
    if (!editing) return;
    setSaving(true);
    const updated = await api.updateGrant(editing.id, {
      application_notes: noteText,
    });
    setGrants((prev) => prev.map((g) => (g.id === updated.id ? updated : g)));
    setEditing(null);
    setSaving(false);
  };

  const deleteGrant = async (id: number) => {
    if (!confirm("Remove this grant?")) return;
    await api.deleteGrant(id);
    setGrants((prev) => prev.filter((g) => g.id !== id));
  };

  return (
    <div>
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-leaf-900">Track Applications</h1>
        <p className="text-gray-500 mt-1">
          Manage your grant pipeline, update statuses, and add notes.
        </p>
      </div>

      {/* Filter bar */}
      <div className="flex items-center gap-2 mb-5 flex-wrap">
        <Filter className="w-4 h-4 text-gray-400" />
        {STATUSES.map(({ value, label }) => (
          <button
            key={value}
            onClick={() => setFilterStatus(value)}
            className={`px-3 py-1 rounded-full text-sm font-medium transition-colors ${
              filterStatus === value
                ? "bg-leaf-600 text-white"
                : "bg-white border border-gray-300 text-gray-600 hover:bg-leaf-50"
            }`}
          >
            {label}
          </button>
        ))}
      </div>

      {loading ? (
        <div className="flex items-center gap-2 text-leaf-600 py-10">
          <Loader2 className="w-5 h-5 animate-spin" /> Loading grants…
        </div>
      ) : grants.length === 0 ? (
        <div className="text-center py-16 text-gray-400">
          <p className="text-lg font-medium">No grants here yet.</p>
          <p className="text-sm mt-1">
            Use <strong>Find Grants</strong> to search for opportunities.
          </p>
        </div>
      ) : (
        <div className="grid gap-4 md:grid-cols-2">
          {grants.map((grant) => (
            <GrantCard
              key={grant.id}
              grant={grant}
              actions={
                <>
                  <select
                    value={grant.status}
                    onChange={(e) => updateStatus(grant, e.target.value as GrantStatus)}
                    className="text-xs border border-gray-300 rounded px-1.5 py-1 bg-white focus:outline-none focus:ring-1 focus:ring-leaf-400"
                    onClick={(e) => e.stopPropagation()}
                  >
                    {STATUSES.filter((s) => s.value).map(({ value, label }) => (
                      <option key={value} value={value}>
                        {label}
                      </option>
                    ))}
                  </select>
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      setEditing(grant);
                      setNoteText(grant.application_notes ?? "");
                    }}
                    title="Add note"
                    className="p-1.5 rounded hover:bg-leaf-100 text-gray-500 hover:text-leaf-700 transition-colors"
                  >
                    <StickyNote className="w-3.5 h-3.5" />
                  </button>
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      navigate(`/apply/${grant.id}`);
                    }}
                    title="Apply helper"
                    className="p-1.5 rounded hover:bg-purple-100 text-gray-500 hover:text-purple-700 transition-colors"
                  >
                    <MessageSquare className="w-3.5 h-3.5" />
                  </button>
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      deleteGrant(grant.id);
                    }}
                    title="Delete"
                    className="p-1.5 rounded hover:bg-red-100 text-gray-500 hover:text-red-600 transition-colors"
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                  </button>
                </>
              }
            />
          ))}
        </div>
      )}

      {/* Notes modal */}
      {editing && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-2xl shadow-xl w-full max-w-md p-6">
            <h3 className="font-semibold text-gray-900 mb-1">{editing.title}</h3>
            <p className="text-sm text-gray-500 mb-3">Application notes</p>
            <textarea
              value={noteText}
              onChange={(e) => setNoteText(e.target.value)}
              rows={6}
              placeholder="Add your notes here…"
              className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-leaf-400 resize-none"
            />
            <div className="flex gap-3 mt-4">
              <button
                onClick={saveNotes}
                disabled={saving}
                className="flex-1 py-2 bg-leaf-600 text-white rounded-lg font-medium hover:bg-leaf-700 disabled:opacity-50 transition-colors"
              >
                {saving ? "Saving…" : "Save"}
              </button>
              <button
                onClick={() => setEditing(null)}
                className="flex-1 py-2 bg-gray-100 text-gray-700 rounded-lg font-medium hover:bg-gray-200 transition-colors"
              >
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
