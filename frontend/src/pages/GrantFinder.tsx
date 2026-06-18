import { useState, useEffect, useRef } from "react";
import { Search, Loader2, CheckCircle, XCircle, Plus } from "lucide-react";
import { api } from "../api";
import GrantCard from "../components/GrantCard";
import type { Grant, SearchJob } from "../types";

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

export default function GrantFinder() {
  const [selected, setSelected] = useState<string[]>(DEFAULT_AREAS);
  const [custom, setCustom] = useState("");
  const [job, setJob] = useState<SearchJob | null>(null);
  const [polling, setPolling] = useState(false);
  const [newGrants, setNewGrants] = useState<Grant[]>([]);
  const [error, setError] = useState<string | null>(null);
  const pollRef = useRef<number | null>(null);

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

  const startSearch = async () => {
    if (selected.length === 0) return;
    setError(null);
    setNewGrants([]);

    try {
      const res = await api.startSearch(selected);
      const initialJob: SearchJob = {
        job_id: res.job_id,
        status: "pending",
        grants_found: 0,
        error: null,
        created_at: new Date().toISOString(),
        completed_at: null,
      };
      setJob(initialJob);
      setPolling(true);

      pollRef.current = window.setInterval(async () => {
        const status = await api.getSearchStatus(res.job_id);
        setJob(status);
        if (status.status === "complete" || status.status === "failed") {
          clearInterval(pollRef.current!);
          setPolling(false);
          if (status.status === "complete" && status.grants_found > 0) {
            const all = await api.listGrants();
            setNewGrants(all.slice(0, status.grants_found));
          }
          if (status.error) setError(status.error);
        }
      }, 3000);
    } catch (e) {
      setError(String(e));
    }
  };

  const isSearching = job && (job.status === "pending" || job.status === "running");

  return (
    <div>
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-leaf-900">Find Grants</h1>
        <p className="text-gray-500 mt-1">
          The AI will search the web for grants matching your chosen topics.
        </p>
      </div>

      <div className="bg-white rounded-xl border border-leaf-200 p-6 shadow-sm mb-6">
        <h2 className="font-semibold text-gray-800 mb-3">Choose Focus Areas</h2>
        <p className="text-sm text-gray-500 mb-4">
          Select the topics you want to find grants for. You can also add your own.
        </p>

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
          disabled={!!isSearching || selected.length === 0}
          className="flex items-center gap-2 px-6 py-2.5 bg-leaf-600 text-white rounded-lg font-medium hover:bg-leaf-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          {isSearching ? (
            <Loader2 className="w-4 h-4 animate-spin" />
          ) : (
            <Search className="w-4 h-4" />
          )}
          {isSearching ? "Searching…" : "Search for Grants"}
        </button>
      </div>

      {/* Status panel */}
      {job && (
        <div
          className={`rounded-xl border p-4 mb-6 flex items-center gap-3 ${
            job.status === "complete"
              ? "bg-leaf-50 border-leaf-300"
              : job.status === "failed"
                ? "bg-red-50 border-red-300"
                : "bg-yellow-50 border-yellow-300"
          }`}
        >
          {polling ? (
            <Loader2 className="w-5 h-5 text-yellow-600 animate-spin shrink-0" />
          ) : job.status === "complete" ? (
            <CheckCircle className="w-5 h-5 text-leaf-600 shrink-0" />
          ) : (
            <XCircle className="w-5 h-5 text-red-500 shrink-0" />
          )}
          <div>
            <p className="font-medium text-sm">
              {job.status === "pending" && "Search queued — starting shortly…"}
              {job.status === "running" && "Searching the web for grants… this may take a minute."}
              {job.status === "complete" &&
                `Search complete! Found ${job.grants_found} new grant${job.grants_found !== 1 ? "s" : ""}.`}
              {job.status === "failed" && "Search failed."}
            </p>
            {error && <p className="text-xs text-red-600 mt-1">{error}</p>}
          </div>
        </div>
      )}

      {/* Results */}
      {newGrants.length > 0 && (
        <div>
          <h2 className="font-semibold text-gray-800 mb-3">
            Newly Found Grants ({newGrants.length})
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
