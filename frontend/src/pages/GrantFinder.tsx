import { useState, useEffect, useRef } from "react";
import { useNavigate } from "react-router-dom";
import {
  Search,
  Loader2,
  CheckCircle,
  XCircle,
  Activity,
  Clock,
  Lock,
  Target,
  AlertTriangle,
  ArrowRight,
} from "lucide-react";
import { api } from "../api";

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

interface Quota {
  currently_running: boolean;
  running_job_id: number | null;
  last_full_search_at: string | null;
  next_full_search_allowed_at: string | null;
  days_since_last: number | null;
  days_remaining: number | null;
  is_locked: boolean;
  total_grants_in_db: number;
}

interface RecentSearch {
  job_id: number;
  question: string;
  completed_at: string;
  days_since: number;
  days_remaining: number;
  grants_found: number;
}

const SEARCH_PHASES = [
  {
    name: "public_lottery",
    label: "Public Sector & Lottery",
    description: "National Lottery, NLCF, DEFRA, Forestry Commission, UKSPF, LEADER",
  },
  {
    name: "energy_climate",
    label: "Energy & Climate",
    description: "Community solar/wind, EV chargers, e-bikes, insulation, heat pumps, climate action",
  },
  {
    name: "nature_wildlife",
    label: "Nature & Wildlife",
    description: "Wildlife Trusts, RSPB, Woodland Trust, tree planting, biodiversity, rewilding",
  },
  {
    name: "community_norfolk",
    label: "Community & Norfolk Local",
    description: "Groundwork, Norfolk funders, offshore wind funds, S106/CIL, developer contributions",
  },
  {
    name: "trusts_corporate",
    label: "Major Trusts & Corporate",
    description: "Esmée Fairbairn, supermarkets, energy companies, Dulverton, Garfield Weston",
  },
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

function formatDate(iso: string) {
  return new Date(iso).toLocaleDateString("en-GB", {
    day: "numeric",
    month: "long",
    year: "numeric",
  });
}

export default function GrantFinder() {
  const navigate = useNavigate();
  const [selectedPhases, setSelectedPhases] = useState<string[]>(
    SEARCH_PHASES.map((p) => p.name)
  );
  const [jobStatus, setJobStatus] = useState<string>("idle");
  const [jobType, setJobType] = useState<"full" | "targeted">("full");
  const [grantsFound, setGrantsFound] = useState(0);
  const [logEntries, setLogEntries] = useState<LogEntry[]>([]);
  const logCursorRef = useRef(0);
  const pollRef = useRef<number | null>(null);
  const logBottomRef = useRef<HTMLDivElement>(null);
  const [elapsedSeconds, setElapsedSeconds] = useState(0);
  const timerRef = useRef<number | null>(null);
  const startTimeRef = useRef<number>(0);
  const [quota, setQuota] = useState<Quota | null>(null);
  const [targetedQuestion, setTargetedQuestion] = useState("");
  const [searchError, setSearchError] = useState<string | null>(null);
  const [recentSearches, setRecentSearches] = useState<RecentSearch[]>([]);
  // Track which panel just completed so we show the result summary in the right place
  const [completedType, setCompletedType] = useState<"full" | "targeted" | null>(null);
  const [completedCount, setCompletedCount] = useState(0);

  const loadRecentSearches = () => {
    api.getRecentTargetedSearches().then(setRecentSearches).catch(() => null);
  };

  useEffect(() => {
    api.getQuota().then(setQuota).catch(() => null);
    loadRecentSearches();
  }, []);

  useEffect(() => {
    logBottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [logEntries]);

  useEffect(() => {
    return () => {
      if (pollRef.current) clearInterval(pollRef.current);
      if (timerRef.current) clearInterval(timerRef.current);
    };
  }, []);

  const togglePhase = (name: string) => {
    setSelectedPhases((prev) =>
      prev.includes(name) ? prev.filter((p) => p !== name) : [...prev, name]
    );
  };

  const pollLog = async (id: number, cursor: number) => {
    try {
      const raw = await fetch(`/api/search/${id}/log?since=${cursor}`);
      if (!raw.ok) return;
      const res: LogResponse = await raw.json();
      if (res.entries.length > 0) {
        setLogEntries((prev) => [...prev, ...res.entries]);
        logCursorRef.current = res.total_entries;
      }
      setGrantsFound(res.grants_found);

      if (res.status === "complete" || res.status === "failed") {
        clearInterval(pollRef.current!);
        if (timerRef.current) clearInterval(timerRef.current);
        setJobStatus(res.status);
        if (res.status === "complete") {
          setCompletedCount(res.grants_found);
          // Refresh quota and recent targeted list
          api.getQuota().then(setQuota).catch(() => null);
          loadRecentSearches();
        }
      }
    } catch (_e) {
      // polling errors are transient — keep going
    }
  };

  const beginPolling = (jobId: number) => {
    startTimeRef.current = Date.now();
    timerRef.current = window.setInterval(() => {
      setElapsedSeconds(Math.floor((Date.now() - startTimeRef.current) / 1000));
    }, 1000);
    pollRef.current = window.setInterval(async () => {
      await pollLog(jobId, logCursorRef.current);
    }, 4000);
  };

  const startSearch = async () => {
    if (selectedPhases.length === 0) return;
    setLogEntries([]);
    logCursorRef.current = 0;
    setGrantsFound(0);
    setElapsedSeconds(0);
    setSearchError(null);
    setCompletedType(null);
    setCompletedCount(0);
    setJobType("full");

    try {
      const res = await api.startSearch(selectedPhases);
      setJobStatus("running");
      setCompletedType("full");
      beginPolling(res.job_id);
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : String(e);
      const detail = msg.replace(/^\d+:\s*/, "");
      setSearchError(detail);
      setJobStatus("idle");
    }
  };

  const startTargeted = async () => {
    const q = targetedQuestion.trim();
    if (q.length < 5) return;
    setLogEntries([]);
    logCursorRef.current = 0;
    setGrantsFound(0);
    setElapsedSeconds(0);
    setSearchError(null);
    setCompletedType(null);
    setCompletedCount(0);
    setJobType("targeted");

    try {
      const res = await api.startTargetedSearch(q);
      setJobStatus("running");
      setCompletedType("targeted");
      beginPolling(res.job_id);
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : String(e);
      setSearchError(msg.replace(/^\d+:\s*/, ""));
      setJobStatus("idle");
    }
  };

  const isSearching = jobStatus === "running" || jobStatus === "pending";

  const currentPhase = (() => {
    for (let i = logEntries.length - 1; i >= 0; i--) {
      const m = logEntries[i].msg.match(/^\[(\d+)\/(\d+)\]\s+(.+)/);
      if (m) return { current: parseInt(m[1]), total: parseInt(m[2]), label: m[3] };
    }
    return null;
  })();

  const formatElapsed = (s: number) => {
    const m = Math.floor(s / 60);
    const sec = s % 60;
    return m > 0 ? `${m}m ${sec}s` : `${sec}s`;
  };

  const isFullLocked = quota?.is_locked || quota?.currently_running;

  return (
    <div>
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-leaf-900">Find Grants</h1>
        <p className="text-gray-500 mt-1">
          The full search covers up to 6 research phases — select only the areas relevant to
          your project to save time and cost. Typically <strong>10–30 minutes</strong>.
          Use targeted search for specific questions any time.
        </p>
      </div>

      {/* Quota status banner */}
      {quota && (
        <div className={`rounded-xl border p-4 mb-5 flex items-start gap-3 ${
          isFullLocked
            ? "bg-amber-50 border-amber-200"
            : "bg-emerald-50 border-emerald-200"
        }`}>
          {isFullLocked ? (
            <Lock className="w-5 h-5 text-amber-500 mt-0.5 shrink-0" />
          ) : (
            <CheckCircle className="w-5 h-5 text-emerald-500 mt-0.5 shrink-0" />
          )}
          <div className="text-sm">
            {quota.currently_running ? (
              <p className="font-medium text-amber-800">
                A search is currently running (job #{quota.running_job_id}). Wait for it to finish before starting another.
              </p>
            ) : quota.is_locked ? (
              <>
                <p className="font-medium text-amber-800">
                  Full search locked — ran {quota.days_since_last} day(s) ago.
                  Next allowed on <strong>{formatDate(quota.next_full_search_allowed_at!)}</strong> ({quota.days_remaining} day(s)).
                </p>
                <p className="text-amber-700 mt-0.5">
                  {quota.total_grants_in_db} grants already in the database. Review those first — use targeted search for anything specific.
                </p>
              </>
            ) : (
              <>
                <p className="font-medium text-emerald-800">
                  Full search available.
                  {quota.last_full_search_at
                    ? ` Last run ${quota.days_since_last} day(s) ago.`
                    : " No full search has run yet."}
                </p>
                <p className="text-emerald-700 mt-0.5">
                  {quota.total_grants_in_db > 0
                    ? `${quota.total_grants_in_db} grants already in the database — the agent will skip funders it has already found.`
                    : "No grants in the database yet."}
                </p>
              </>
            )}
          </div>
        </div>
      )}

      {/* Error banner */}
      {searchError && (
        <div className="rounded-xl border border-red-200 bg-red-50 p-4 mb-5 flex items-start gap-3">
          <AlertTriangle className="w-5 h-5 text-red-500 mt-0.5 shrink-0" />
          <p className="text-sm text-red-700">{searchError}</p>
        </div>
      )}

      {/* Full search panel */}
      <div className={`bg-white rounded-xl border p-6 shadow-sm mb-5 ${isFullLocked ? "opacity-60" : "border-leaf-200"}`}>
        <div className="flex items-center gap-2 mb-3">
          <Search className="w-4 h-4 text-leaf-600" />
          <h2 className="font-semibold text-gray-800">Full Deep Search</h2>
          {isFullLocked && <span className="text-xs bg-amber-100 text-amber-700 px-2 py-0.5 rounded-full font-medium">Locked</span>}
        </div>

        <p className="text-sm text-gray-500 mb-3">
          Select which funding areas to research. Deselect any that aren't relevant to save time and cost.
          <span className="text-gray-400"> Verify & Deepen always runs last.</span>
        </p>

        <div className="space-y-2 mb-5">
          {SEARCH_PHASES.map((phase) => {
            const checked = selectedPhases.includes(phase.name);
            return (
              <label
                key={phase.name}
                className={`flex items-start gap-3 p-3 rounded-lg border cursor-pointer transition-colors ${
                  isFullLocked || isSearching
                    ? "opacity-50 cursor-not-allowed"
                    : checked
                    ? "border-leaf-300 bg-leaf-50"
                    : "border-gray-200 bg-white hover:border-leaf-200"
                }`}
              >
                <input
                  type="checkbox"
                  checked={checked}
                  disabled={isFullLocked || isSearching}
                  onChange={() => !isFullLocked && !isSearching && togglePhase(phase.name)}
                  className="mt-0.5 accent-leaf-600 shrink-0"
                />
                <div>
                  <span className="text-sm font-medium text-gray-800">{phase.label}</span>
                  <span className="text-xs text-gray-500 block mt-0.5">{phase.description}</span>
                </div>
              </label>
            );
          })}
        </div>

        <button
          onClick={startSearch}
          disabled={isFullLocked || isSearching || selectedPhases.length === 0}
          className="flex items-center gap-2 px-6 py-2.5 bg-leaf-600 text-white rounded-lg font-medium hover:bg-leaf-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          {isSearching && jobType === "full" ? (
            <Loader2 className="w-4 h-4 animate-spin" />
          ) : isFullLocked ? (
            <Lock className="w-4 h-4" />
          ) : (
            <Search className="w-4 h-4" />
          )}
          {isSearching && jobType === "full"
            ? "Researching…"
            : isFullLocked
            ? "Full Search Locked"
            : `Start Deep Research${selectedPhases.length < SEARCH_PHASES.length ? ` (${selectedPhases.length + 1} phases)` : ""}`}
        </button>

        {!isFullLocked && !isSearching && (
          <p className="text-xs text-gray-400 mt-3">
            {selectedPhases.length} of {SEARCH_PHASES.length} areas selected · Verify & Deepen always included · Once per 30 days.
          </p>
        )}

        {/* Full search result summary */}
        {jobStatus === "complete" && completedType === "full" && (
          <div className="flex items-center justify-between bg-emerald-50 border border-emerald-200 rounded-lg px-4 py-3 mt-4">
            <span className="text-sm text-emerald-800 font-medium">
              {completedCount > 0
                ? `✓ ${completedCount} new grant${completedCount !== 1 ? "s" : ""} added to the tracker`
                : "✓ Search complete — no new grants found (all already in database)"}
            </span>
            <button
              onClick={() => navigate("/tracker")}
              className="flex items-center gap-1.5 text-sm font-medium text-emerald-700 hover:text-emerald-900 transition-colors"
            >
              View in Grant Tracker <ArrowRight className="w-4 h-4" />
            </button>
          </div>
        )}
      </div>

      {/* Targeted search panel */}
      <div className="bg-white rounded-xl border border-leaf-200 p-6 shadow-sm mb-6">
        <div className="flex items-center gap-2 mb-2">
          <Target className="w-4 h-4 text-leaf-600" />
          <h2 className="font-semibold text-gray-800">Targeted Search</h2>
          <span className="text-xs bg-leaf-100 text-leaf-700 px-2 py-0.5 rounded-full font-medium">Available once per topic per 30 days</span>
        </div>
        <p className="text-sm text-gray-500 mb-4">
          Ask a specific question — for example, "grants for community composting in Norfolk" or
          "EV charging point funding for parish councils 2025". Cheaper and faster than the full search.
          Will not re-research funders already in the database.
        </p>
        <div className="flex gap-2 mb-4">
          <input
            type="text"
            value={targetedQuestion}
            onChange={(e) => setTargetedQuestion(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && !isSearching && startTargeted()}
            disabled={isSearching}
            placeholder="What specific grant or funder do you want to research?"
            className="flex-1 border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-leaf-400 disabled:opacity-50"
          />
          <button
            onClick={startTargeted}
            disabled={isSearching || targetedQuestion.trim().length < 5}
            className="flex items-center gap-2 px-5 py-2 bg-leaf-600 text-white rounded-lg font-medium hover:bg-leaf-700 disabled:opacity-50 disabled:cursor-not-allowed text-sm transition-colors"
          >
            {isSearching && jobType === "targeted" ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <Target className="w-4 h-4" />
            )}
            {isSearching && jobType === "targeted" ? "Searching…" : "Search"}
          </button>
        </div>

        {/* Completed targeted search result summary */}
        {jobStatus === "complete" && completedType === "targeted" && (
          <div className="flex items-center justify-between bg-emerald-50 border border-emerald-200 rounded-lg px-4 py-3 mb-4">
            <span className="text-sm text-emerald-800 font-medium">
              {completedCount > 0
                ? `✓ ${completedCount} new grant${completedCount !== 1 ? "s" : ""} added to the tracker`
                : "✓ Search complete — no new grants found (all already in database)"}
            </span>
            <button
              onClick={() => navigate("/tracker")}
              className="flex items-center gap-1.5 text-sm font-medium text-emerald-700 hover:text-emerald-900 transition-colors"
            >
              View in Grant Tracker <ArrowRight className="w-4 h-4" />
            </button>
          </div>
        )}

        {/* Recently searched topics */}
        {recentSearches.length > 0 && (
          <div>
            <p className="text-xs font-medium text-gray-500 mb-2">Recently searched (30-day cooldown per topic):</p>
            <div className="flex flex-wrap gap-2">
              {recentSearches.map((rs) => (
                <div
                  key={rs.job_id}
                  className="flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs bg-amber-50 border border-amber-200 text-amber-800"
                  title={`${rs.grants_found} grant${rs.grants_found !== 1 ? "s" : ""} found — next available in ${rs.days_remaining} day(s)`}
                >
                  <Lock className="w-3 h-3" />
                  <span className="font-medium truncate max-w-[200px]">{rs.question}</span>
                  <span className="text-amber-600 shrink-0">· {rs.days_remaining}d left</span>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Live research log */}
      {(isSearching || logEntries.length > 0) && (
        <div className="bg-gray-950 rounded-xl border border-gray-800 mb-6 overflow-hidden">
          <div className="flex items-center gap-2 px-4 py-3 border-b border-gray-800">
            <Activity className="w-4 h-4 text-leaf-400" />
            <span className="text-sm font-medium text-gray-300">
              {jobType === "targeted" ? "Targeted Search Log" : "Research Log"}
            </span>
            {isSearching && (
              <span className="ml-auto flex items-center gap-2 text-xs text-yellow-400">
                <Clock className="w-3 h-3" />
                {formatElapsed(elapsedSeconds)}
                <Loader2 className="w-3 h-3 animate-spin ml-1" /> Researching…
              </span>
            )}
            {jobStatus === "complete" && (
              <span className="ml-auto flex items-center gap-1.5 text-xs text-emerald-400">
                <CheckCircle className="w-3 h-3" /> Complete — {grantsFound} grants found
                {elapsedSeconds > 0 && (
                  <span className="text-gray-500 ml-1">in {formatElapsed(elapsedSeconds)}</span>
                )}
              </span>
            )}
            {jobStatus === "failed" && (
              <span className="ml-auto flex items-center gap-1.5 text-xs text-red-400">
                <XCircle className="w-3 h-3" /> Failed
              </span>
            )}
          </div>

          {(isSearching || currentPhase) && currentPhase && jobType === "full" && (
            <div className="px-4 py-3 border-b border-gray-800 bg-gray-900">
              <div className="flex justify-between text-xs text-gray-400 mb-1.5">
                <span>Phase {currentPhase.current} of {currentPhase.total}: {currentPhase.label}</span>
                <span>{Math.round((currentPhase.current / currentPhase.total) * 100)}%</span>
              </div>
              <div className="w-full bg-gray-800 rounded-full h-1.5">
                <div
                  className="bg-leaf-500 h-1.5 rounded-full transition-all duration-700"
                  style={{ width: `${(currentPhase.current / currentPhase.total) * 100}%` }}
                />
              </div>
            </div>
          )}

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

    </div>
  );
}
