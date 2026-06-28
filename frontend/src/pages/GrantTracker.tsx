import { useEffect, useState, useMemo } from "react";
import { useNavigate } from "react-router-dom";
import {
  Loader2,
  MessageSquare,
  Trash2,
  StickyNote,
  Search,
  ArrowUpDown,
  ExternalLink,
  ChevronDown,
} from "lucide-react";
import { api } from "../api";
import type { Grant, GrantStatus } from "../types";
import StatusBadge from "../components/StatusBadge";

const STATUSES: { value: string; label: string; color: string }[] = [
  { value: "discovered", label: "To Review", color: "bg-blue-600" },
  { value: "reviewing", label: "Reviewing", color: "bg-yellow-500" },
  { value: "applied", label: "Applied", color: "bg-purple-600" },
  { value: "awarded", label: "Awarded", color: "bg-leaf-600" },
  { value: "rejected", label: "Rejected", color: "bg-red-500" },
  { value: "not_eligible", label: "Not Eligible", color: "bg-gray-400" },
];

const ALL_STATUSES = [{ value: "", label: "All", color: "bg-gray-600" }, ...STATUSES];

type SortKey = "amount_desc" | "amount_asc" | "newest" | "deadline";

export default function GrantTracker() {
  const [grants, setGrants] = useState<Grant[]>([]);
  const [loading, setLoading] = useState(true);
  const [filterStatus, setFilterStatus] = useState("discovered");
  const [searchText, setSearchText] = useState("");
  const [sortKey, setSortKey] = useState<SortKey>("amount_desc");
  const [editing, setEditing] = useState<Grant | null>(null);
  const [noteText, setNoteText] = useState("");
  const [saving, setSaving] = useState(false);
  const [expandedId, setExpandedId] = useState<number | null>(null);
  const navigate = useNavigate();

  const load = () => {
    setLoading(true);
    api
      .listGrants()
      .then(setGrants)
      .catch(console.error)
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    load();
  }, []);

  const counts = useMemo(() => {
    const c: Record<string, number> = { "": grants.length };
    for (const g of grants) {
      c[g.status] = (c[g.status] ?? 0) + 1;
    }
    return c;
  }, [grants]);

  const visible = useMemo(() => {
    let list = grants;
    if (filterStatus) list = list.filter((g) => g.status === filterStatus);
    if (searchText.trim()) {
      const q = searchText.toLowerCase();
      list = list.filter(
        (g) =>
          g.title.toLowerCase().includes(q) ||
          g.funder.toLowerCase().includes(q) ||
          g.description.toLowerCase().includes(q)
      );
    }
    switch (sortKey) {
      case "amount_desc":
        return [...list].sort((a, b) => (b.max_amount ?? 0) - (a.max_amount ?? 0));
      case "amount_asc":
        return [...list].sort((a, b) => (a.max_amount ?? 0) - (b.max_amount ?? 0));
      case "newest":
        return [...list].sort((a, b) => b.id - a.id);
      case "deadline":
        return [...list].sort((a, b) => {
          if (!a.deadline) return 1;
          if (!b.deadline) return -1;
          return a.deadline.localeCompare(b.deadline);
        });
      default:
        return list;
    }
  }, [grants, filterStatus, searchText, sortKey]);

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
    if (!confirm("Remove this grant from the database?")) return;
    await api.deleteGrant(id);
    setGrants((prev) => prev.filter((g) => g.id !== id));
  };

  return (
    <div>
      <div className="mb-5">
        <h1 className="text-2xl font-bold text-leaf-900">Grant Pipeline</h1>
        <p className="text-gray-500 mt-1">
          Review discovered grants, update statuses, and add notes.
        </p>
      </div>

      {/* Status filter tabs */}
      <div className="flex flex-wrap gap-2 mb-4">
        {ALL_STATUSES.map(({ value, label }) => {
          const count = counts[value] ?? 0;
          const active = filterStatus === value;
          return (
            <button
              key={value}
              onClick={() => setFilterStatus(value)}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-full text-sm font-medium transition-colors ${
                active
                  ? "bg-leaf-600 text-white shadow-sm"
                  : "bg-white border border-gray-300 text-gray-600 hover:bg-leaf-50"
              }`}
            >
              {label}
              {count > 0 && (
                <span
                  className={`text-xs px-1.5 py-0.5 rounded-full font-semibold ${
                    active ? "bg-white/20 text-white" : "bg-gray-100 text-gray-600"
                  }`}
                >
                  {count}
                </span>
              )}
            </button>
          );
        })}
      </div>

      {/* Search + sort bar */}
      <div className="flex gap-2 mb-5">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
          <input
            type="text"
            value={searchText}
            onChange={(e) => setSearchText(e.target.value)}
            placeholder="Search grants by name, funder or description…"
            className="w-full pl-9 pr-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-leaf-400"
          />
        </div>
        <div className="flex items-center gap-1.5">
          <ArrowUpDown className="w-4 h-4 text-gray-400" />
          <select
            value={sortKey}
            onChange={(e) => setSortKey(e.target.value as SortKey)}
            className="border border-gray-300 rounded-lg px-2 py-2 text-sm bg-white focus:outline-none focus:ring-1 focus:ring-leaf-400"
          >
            <option value="amount_desc">Highest amount</option>
            <option value="amount_asc">Lowest amount</option>
            <option value="newest">Newest first</option>
            <option value="deadline">Deadline</option>
          </select>
        </div>
      </div>

      {loading ? (
        <div className="flex items-center gap-2 text-leaf-600 py-10">
          <Loader2 className="w-5 h-5 animate-spin" /> Loading grants…
        </div>
      ) : visible.length === 0 ? (
        <div className="text-center py-16 text-gray-400">
          <p className="text-lg font-medium">
            {searchText
              ? `No grants match "${searchText}"`
              : filterStatus
              ? `No grants with status "${filterStatus}"`
              : "No grants yet — run a search to get started."}
          </p>
          {!searchText && filterStatus === "discovered" && grants.length === 0 && (
            <p className="text-sm mt-1">
              Use <strong>Find Grants</strong> to search for opportunities.
            </p>
          )}
        </div>
      ) : (
        <div className="space-y-3">
          {visible.map((grant) => (
            <GrantRow
              key={grant.id}
              grant={grant}
              expanded={expandedId === grant.id}
              onToggle={() => setExpandedId(expandedId === grant.id ? null : grant.id)}
              onStatusChange={(s) => updateStatus(grant, s)}
              onNote={() => { setEditing(grant); setNoteText(grant.application_notes ?? ""); }}
              onApply={() => navigate(`/apply/${grant.id}`)}
              onDelete={() => deleteGrant(grant.id)}
            />
          ))}
        </div>
      )}

      {/* Notes modal */}
      {editing && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-2xl shadow-xl w-full max-w-md p-6">
            <h3 className="font-semibold text-gray-900 mb-0.5">{editing.title}</h3>
            <p className="text-sm text-leaf-700 font-medium mb-3">{editing.funder}</p>
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
                {saving ? "Saving…" : "Save Notes"}
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

interface RowProps {
  grant: Grant;
  expanded: boolean;
  onToggle: () => void;
  onStatusChange: (s: GrantStatus) => void;
  onNote: () => void;
  onApply: () => void;
  onDelete: () => void;
}

function GrantRow({ grant, expanded, onToggle, onStatusChange, onNote, onApply, onDelete }: RowProps) {
  const amountStr = grant.max_amount ? `£${grant.max_amount.toLocaleString()}` : null;

  return (
    <div className="bg-white rounded-xl border border-leaf-200 shadow-sm overflow-hidden">
      {/* Summary row — always visible */}
      <div
        className="flex items-center gap-3 px-4 py-3 cursor-pointer hover:bg-leaf-50 transition-colors"
        onClick={onToggle}
      >
        <ChevronDown
          className={`w-4 h-4 text-gray-400 shrink-0 transition-transform ${expanded ? "rotate-180" : ""}`}
        />
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="font-medium text-gray-900 text-sm leading-snug">{grant.title}</span>
            <span className="text-xs text-leaf-700 font-medium">{grant.funder}</span>
          </div>
          <div className="flex items-center gap-3 mt-0.5 text-xs text-gray-500">
            {amountStr && <span>Up to {amountStr}</span>}
            {grant.deadline && <span>Deadline: {grant.deadline}</span>}
            {grant.application_notes && (
              <span className="text-amber-600 font-medium">Has notes</span>
            )}
          </div>
        </div>
        <StatusBadge status={grant.status} />
      </div>

      {/* Expanded detail */}
      {expanded && (
        <div className="border-t border-gray-100 px-4 py-4 space-y-3">
          <p className="text-sm text-gray-700 leading-relaxed">{grant.description}</p>

          {grant.eligibility_notes && (
            <div className="bg-blue-50 border border-blue-100 rounded-lg p-3 text-xs text-blue-800">
              <span className="font-semibold">Eligibility: </span>{grant.eligibility_notes}
            </div>
          )}

          {grant.application_notes && (
            <div className="bg-amber-50 border border-amber-100 rounded-lg p-3 text-xs text-amber-800">
              <span className="font-semibold">Notes: </span>{grant.application_notes}
            </div>
          )}

          {grant.focus_areas.length > 0 && (
            <div className="flex flex-wrap gap-1">
              {grant.focus_areas.map((area) => (
                <span
                  key={area}
                  className="bg-leaf-50 text-leaf-700 text-xs px-2 py-0.5 rounded-full border border-leaf-100"
                >
                  {area}
                </span>
              ))}
            </div>
          )}

          {/* Status change buttons */}
          <div>
            <p className="text-xs text-gray-500 mb-2 font-medium">Move to:</p>
            <div className="flex flex-wrap gap-2">
              {STATUSES.filter((s) => s.value !== grant.status).map(({ value, label, color }) => (
                <button
                  key={value}
                  onClick={() => onStatusChange(value as GrantStatus)}
                  className={`px-3 py-1 text-xs rounded-full text-white font-medium transition-opacity hover:opacity-80 ${color}`}
                >
                  {label}
                </button>
              ))}
            </div>
          </div>

          {/* Actions */}
          <div className="flex items-center gap-2 pt-1">
            {grant.url && (
              <a
                href={grant.url}
                target="_blank"
                rel="noreferrer"
                className="flex items-center gap-1.5 text-xs text-leaf-600 hover:text-leaf-800 font-medium"
              >
                <ExternalLink className="w-3.5 h-3.5" /> Open grant page
              </a>
            )}
            <div className="ml-auto flex items-center gap-1.5">
              <button
                onClick={onNote}
                title="Add note"
                className="flex items-center gap-1 px-2.5 py-1 rounded-lg text-xs text-gray-600 hover:bg-leaf-100 hover:text-leaf-800 border border-gray-200 transition-colors"
              >
                <StickyNote className="w-3.5 h-3.5" /> Note
              </button>
              <button
                onClick={onApply}
                title="Apply helper"
                className="flex items-center gap-1 px-2.5 py-1 rounded-lg text-xs text-gray-600 hover:bg-purple-100 hover:text-purple-800 border border-gray-200 transition-colors"
              >
                <MessageSquare className="w-3.5 h-3.5" /> Apply help
              </button>
              <button
                onClick={onDelete}
                title="Delete"
                className="flex items-center gap-1 px-2.5 py-1 rounded-lg text-xs text-gray-600 hover:bg-red-100 hover:text-red-700 border border-gray-200 transition-colors"
              >
                <Trash2 className="w-3.5 h-3.5" /> Remove
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
