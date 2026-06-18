import { useState, useEffect, useRef } from "react";
import {
  Search,
  Loader2,
  CheckCircle,
  XCircle,
  Plus,
  Activity,
} from "lucide-react";
import { api } from "../api";
import GrantCard from "../components/GrantCard";
import type { Grant } from "../types";

interface LogEntry {
  ts: string;
  msg: string;
  level: string;
}

interface LogResponse {
  job_id: number;
  status: string;
  grants_found: number;
  total_entries: number;
  entries: LogEntry[];
}

const DEFAULT_AREAS = [
  "tree planting",
  "rewilding",
  "solar energy",
  "insulation",
  "heat pumps",
  "biodiversity",
  "community education",
  "electric vehicles",
  "net zero",
];


function levelClasses(level: string) {
  switch (level) {
    case "phase":
      return "text-leaf-300 font-bold";
    case "found":
      return "text-emerald-400 font-semibold";
    case "error":
      return "text-red-400";
    default:
      return "text-gray-400";
  }
}

export default function GrantFinder() {
  const [selected, setSelected] = useState<string[]>(DEFAULT_AREAS);
  const [custom, setCustom] = useState("");
  const [jobStatus, setJobStatus] = useState<string>("idle");
  const [grantsFound, setGrantsFound] = useState(0);
  const [logEntries, setLogEntries] = useState<LogEntry[]>([]);
  const logCursorRef = useRef(0);
  const [newGrants, setNewGrants] = useState<Grant[]>([]);
  const pollRef = useRef<number | null>(null);
  const logBottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    logBottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [logEntries]);

  useEffect(() => {
    return () => {
      if (pollRef.current) clearInterval(pollRef.current);
    };
  }, []);

  const toggleArea = (area: string) => {
    setSelected((prev) =>
      prev.includes(area) ? prev.filter((a) => a !== area) : [...prev, area]
    );
  };

  const addCustom = () => {
    const trimmed = custom.trim().toLowerCase();
    if (trimmed && !selected.includes(trimmed)) {
      setSelected((prev) => [...prev, trimmed]);
    }
    setCustom("");
  };

  const pollLog = async (id: number, cursor: number) => {
    try {
      const res: LogResponse = await fetch(`/api/search/${id}/log?since=${cursor}`).then((r) =>
        r.json()
      );
      if (res.entries.length > 0) {
        setLogEntries((prev) => [...prev, ...res.entries]);
        logCursorRef.current = res.total_entries;
      }
      setGrantsFound(res.grants_found);

      if (res.status === "complete" || res.status === "failed") {
        clearInterval(pollRef.current!);
        setJobStatus(res.status);
        if (res.status === "complete") {
          const all = await api.listGrants();
          setNewGrants(all.slice(0, Math.min(res.grants_found, all.length)));
        }
      }
    } catch (e) {
      // polling errors are transient — keep going
    }
  };

  const startSearch = async () => {
    if (selected.length === 0) return;
    setNewGrants([]);
    setLogEntries([]);
    logCursorRef.current = 0;
    setGrantsFound(0);

    try {
      const res = await api.startSearch(selected);
      setJobStatus("running");

      pollRef.current = window.setInterval(async () => {
        await pollLog(res.job_id, logCursorRef.current);
      }, 4000);
    } catch (_e) {
      setJobStatus("failed");
    }
  };

  const isSearching = jobStatus === "running" || jobStatus === "pending";

  return (
    <div>
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-leaf-900">Find Grants</h1>
        <p className="text-gray-500 mt-1">
          The AI runs a deep, multi-phase search across the entire UK environmental grant
          landscape. It takes a while — that's deliberate. Thoroughness over speed.
        </p>
      </div>

      <div className="bg-white rounded-xl border border-leaf-200 p-6 shadow-sm mb-6">
        <h2 className="font-semibold text-gray-800 mb-3">Choose Focus Areas</h2>
        <div className="flex flex-wrap gap-2 mb-4">
          {selected.map((area) => (
            <button
              key={area}
              onClick={() => toggleArea(area)}
              className="px-3 py-1.5 rounded-full text-sm font-medium bg-leaf-600 text-white hover:bg-leaf-700 transition-colors"
            >
              {area} ×
            </button>
          ))}
          {DEFAULT_AREAS.filter((a) => !selected.includes(a)).map((area) => (
            <button
              key={area}
              onClick={() => toggleArea(area)}
              className="px-3 py-1.5 rounded-full text-sm font-medium bg-gray-100 text-gray-600 hover:bg-leaf-100 hover:text-leaf-700 border border-gray-200 transition-colors"
            >
              {area}
            </button>
          ))}
        </div>

        <div className="flex gap-2 mb-5">
          <input
            type="text"
            value={custom}
            onChange={(e) => setCustom(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && addCustom()}
            placeholder="Add custom topic…"
            className="flex-1 border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-leaf-400"
          />
          <button
            onClick={addCustom}
            className="flex items-center gap-1 px-3 py-2 bg-leaf-100 text-leaf-700 rounded-lg hover:bg-leaf-200 text-sm font-medium transition-colors"
          >
            <Plus className="w-4 h-4" /> Add
          </button>
        </div>

        <button
          onClick={startSearch}
          disabled={isSearching || selected.length === 0}
          className="flex items-center gap-2 px-6 py-2.5 bg-leaf-600 text-white rounded-lg font-medium hover:bg-leaf-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          {isSearching ? (
            <Loader2 className="w-4 h-4 animate-spin" />
          ) : (
            <Search className="w-4 h-4" />
          )}
          {isSearching ? "Researching…" : "Start Deep Research"}
        </button>

        {!isSearching && jobStatus === "idle" && (
          <p className="text-xs text-gray-400 mt-3">
            Covers 10 research phases: National Lottery · Government · Energy schemes ·
            Wildlife charities · Norfolk funders · Major trusts · Corporate CSR · and more.
          </p>
        )}
      </div>

      {/* Live research log */}
      {(isSearching || logEntries.length > 0) && (
        <div className="bg-gray-950 rounded-xl border border-gray-800 mb-6 overflow-hidden">
          <div className="flex items-center gap-2 px-4 py-3 border-b border-gray-800">
            <Activity className="w-4 h-4 text-leaf-400" />
            <span className="text-sm font-medium text-gray-300">Research Log</span>
            {isSearching && (
              <span className="ml-auto flex items-center gap-1.5 text-xs text-yellow-400">
                <Loader2 className="w-3 h-3 animate-spin" /> Researching…
              </span>
            )}
            {jobStatus === "complete" && (
              <span className="ml-auto flex items-center gap-1.5 text-xs text-emerald-400">
                <CheckCircle className="w-3 h-3" /> Complete — {grantsFound} grants found
              </span>
            )}
            {jobStatus === "failed" && (
              <span className="ml-auto flex items-center gap-1.5 text-xs text-red-400">
                <XCircle className="w-3 h-3" /> Failed
              </span>
            )}
          </div>
          <div className="p-4 font-mono text-xs h-64 overflow-y-auto space-y-0.5">
            {logEntries.length === 0 && (
              <div className="text-gray-600 italic">Starting up…</div>
            )}
            {logEntries.map((entry, i) => (
              <div key={i} className={`leading-relaxed ${levelClasses(entry.level)}`}>
                <span className="text-gray-600 mr-2">
                  {new Date(entry.ts).toLocaleTimeString()}
                </span>
                {entry.msg}
              </div>
            ))}
            {isSearching && (
              <div className="text-gray-600 animate-pulse">▋</div>
            )}
            <div ref={logBottomRef} />
          </div>
        </div>
      )}

      {/* Results */}
      {newGrants.length > 0 && (
        <div>
          <h2 className="font-semibold text-gray-800 mb-3">
            Grants Found ({newGrants.length})
          </h2>
          <div className="grid gap-4 md:grid-cols-2">
            {newGrants.map((grant) => (
              <GrantCard key={grant.id} grant={grant} />
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
