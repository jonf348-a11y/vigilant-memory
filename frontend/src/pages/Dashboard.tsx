import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  Leaf,
  TrendingUp,
  CheckCircle,
  Clock,
  AlertCircle,
  Search,
  ArrowRight,
  Bell,
  ExternalLink,
} from "lucide-react";
import { api } from "../api";
import type { DashboardStats, Grant } from "../types";

const statusColor: Record<string, string> = {
  discovered: "text-blue-600",
  reviewing: "text-yellow-600",
  applied: "text-purple-600",
  awarded: "text-leaf-600",
  rejected: "text-red-500",
  not_eligible: "text-gray-400",
};

export default function Dashboard() {
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [toReview, setToReview] = useState<Grant[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([
      api.getStats(),
      api.listGrants("discovered"),
    ])
      .then(([s, discovered]) => {
        setStats(s);
        setToReview(discovered.sort((a, b) => (b.max_amount ?? 0) - (a.max_amount ?? 0)).slice(0, 5));
      })
      .catch(console.error)
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64 text-leaf-600">
        <Leaf className="w-6 h-6 animate-spin mr-2" />
        Loading…
      </div>
    );
  }

  const total = stats?.total_grants ?? 0;
  const potential = stats?.total_potential_value ?? 0;
  const awarded = stats?.by_status?.awarded ?? 0;
  const active =
    (stats?.by_status?.reviewing ?? 0) + (stats?.by_status?.applied ?? 0);
  const totalSearches = stats?.total_searches ?? 0;

  return (
    <div>
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-leaf-900">Dashboard</h1>
        <p className="text-gray-500 mt-1">
          Welcome to the Hethersett Grant Agent — helping HEAT &amp; HEAG fund a
          greener future.
        </p>
      </div>

      {/* Key metrics */}
      <div className="grid grid-cols-2 lg:grid-cols-5 gap-4 mb-8">
        <StatCard
          icon={<Search className="w-5 h-5 text-blue-500" />}
          label="Grants Found"
          value={total}
          bg="bg-blue-50"
        />
        <StatCard
          icon={<Clock className="w-5 h-5 text-yellow-500" />}
          label="In Progress"
          value={active}
          bg="bg-yellow-50"
        />
        <StatCard
          icon={<CheckCircle className="w-5 h-5 text-leaf-500" />}
          label="Awarded"
          value={awarded}
          bg="bg-leaf-50"
        />
        <StatCard
          icon={<TrendingUp className="w-5 h-5 text-purple-500" />}
          label="Potential Value"
          value={potential > 0 ? `£${potential.toLocaleString()}` : "—"}
          bg="bg-purple-50"
        />
        <StatCard
          icon={<Search className="w-5 h-5 text-gray-500" />}
          label="Searches Run"
          value={totalSearches}
          bg="bg-gray-50"
        />
      </div>

      {/* Grants needing review */}
      {toReview.length > 0 && (
        <div className="bg-blue-50 border border-blue-200 rounded-xl p-5 shadow-sm mb-6">
          <div className="flex items-center justify-between mb-3">
            <h2 className="font-semibold text-blue-900 flex items-center gap-2">
              <Bell className="w-4 h-4 text-blue-600" />
              Grants to Review ({stats?.by_status?.discovered ?? toReview.length})
            </h2>
            <Link
              to="/tracker"
              className="text-xs text-blue-600 hover:text-blue-800 font-medium flex items-center gap-1"
            >
              View all <ArrowRight className="w-3 h-3" />
            </Link>
          </div>
          <div className="space-y-2">
            {toReview.map((g) => (
              <div
                key={g.id}
                className="bg-white rounded-lg border border-blue-100 px-3 py-2.5 flex items-center gap-3"
              >
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-gray-900 truncate">{g.title}</p>
                  <p className="text-xs text-leaf-700">{g.funder}</p>
                </div>
                {g.max_amount && (
                  <span className="text-sm font-semibold text-gray-700 shrink-0">
                    £{g.max_amount.toLocaleString()}
                  </span>
                )}
                {g.url && (
                  <a
                    href={g.url}
                    target="_blank"
                    rel="noreferrer"
                    className="text-leaf-600 hover:text-leaf-800 shrink-0"
                    title="Open grant page"
                  >
                    <ExternalLink className="w-4 h-4" />
                  </a>
                )}
              </div>
            ))}
          </div>
          <Link
            to="/tracker"
            className="mt-3 flex items-center justify-center gap-2 w-full py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 transition-colors"
          >
            Review all discovered grants <ArrowRight className="w-4 h-4" />
          </Link>
        </div>
      )}

      <div className="grid lg:grid-cols-2 gap-6">
        {/* By status breakdown */}
        <div className="bg-white rounded-xl border border-leaf-200 p-5 shadow-sm">
          <h2 className="font-semibold text-gray-800 mb-4 flex items-center gap-2">
            <AlertCircle className="w-4 h-4 text-leaf-600" />
            Grants by Status
          </h2>
          {stats && Object.keys(stats.by_status).length > 0 ? (
            <ul className="space-y-2">
              {Object.entries(stats.by_status).map(([status, count]) => (
                <li key={status} className="flex items-center justify-between">
                  <Link
                    to={`/tracker?status=${status}`}
                    className={`capitalize text-sm font-medium hover:underline ${statusColor[status] ?? "text-gray-600"}`}
                  >
                    {status === "discovered" ? "To Review" : status.replace(/_/g, " ")}
                  </Link>
                  <span className="text-sm text-gray-700 font-semibold">{count}</span>
                </li>
              ))}
            </ul>
          ) : (
            <p className="text-sm text-gray-400">No grants yet — run a search to get started.</p>
          )}
        </div>

        {/* Quick actions */}
        <div className="bg-white rounded-xl border border-leaf-200 p-5 shadow-sm">
          <h2 className="font-semibold text-gray-800 mb-4 flex items-center gap-2">
            <Leaf className="w-4 h-4 text-leaf-600" />
            Quick Actions
          </h2>
          <div className="space-y-3">
            <QuickAction
              to="/tracker"
              title="Review Discovered Grants"
              desc="See all found grants, update statuses and add notes"
              icon="📋"
            />
            <QuickAction
              to="/find"
              title="Search for New Grants"
              desc="Run a targeted search or a full deep research sweep"
              icon="🔍"
            />
            <QuickAction
              to="/apply"
              title="Get Application Help"
              desc="Use this programme to help complete an application form"
              icon="✍️"
            />
          </div>
        </div>
      </div>

      {/* Recent searches */}
      {stats && stats.recent_searches.length > 0 && (
        <div className="mt-6 bg-white rounded-xl border border-leaf-200 p-5 shadow-sm">
          <h2 className="font-semibold text-gray-800 mb-4">Recent Searches</h2>
          <div className="divide-y divide-gray-100">
            {stats.recent_searches.map((s) => (
              <div key={s.job_id} className="py-2 flex items-center justify-between text-sm">
                <span className="text-gray-600">
                  Search #{s.job_id} ·{" "}
                  <span
                    className={
                      s.status === "complete"
                        ? "text-leaf-600"
                        : s.status === "failed"
                          ? "text-red-500"
                          : "text-yellow-600"
                    }
                  >
                    {s.status}
                  </span>
                </span>
                <span className="text-gray-500">
                  {s.grants_found} grant{s.grants_found !== 1 ? "s" : ""} found
                </span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function StatCard({
  icon,
  label,
  value,
  bg,
}: {
  icon: React.ReactNode;
  label: string;
  value: string | number;
  bg: string;
}) {
  return (
    <div className={`${bg} rounded-xl p-4 border border-white shadow-sm`}>
      <div className="flex items-center gap-2 mb-2">{icon}</div>
      <div className="text-2xl font-bold text-gray-900">{value}</div>
      <div className="text-xs text-gray-500 mt-0.5">{label}</div>
    </div>
  );
}

function QuickAction({
  to,
  title,
  desc,
  icon,
}: {
  to: string;
  title: string;
  desc: string;
  icon: string;
}) {
  return (
    <Link
      to={to}
      className="flex items-center gap-3 p-3 rounded-lg hover:bg-leaf-50 border border-transparent hover:border-leaf-200 transition-colors group"
    >
      <span className="text-2xl">{icon}</span>
      <div className="flex-1">
        <div className="text-sm font-medium text-gray-800">{title}</div>
        <div className="text-xs text-gray-500">{desc}</div>
      </div>
      <ArrowRight className="w-4 h-4 text-leaf-400 group-hover:text-leaf-600 transition-colors" />
    </Link>
  );
}
