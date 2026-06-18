import type { GrantStatus } from "../types";

const config: Record<GrantStatus, { label: string; classes: string }> = {
  discovered: { label: "Discovered", classes: "bg-blue-100 text-blue-800" },
  reviewing: { label: "Reviewing", classes: "bg-yellow-100 text-yellow-800" },
  applied: { label: "Applied", classes: "bg-purple-100 text-purple-800" },
  awarded: { label: "Awarded!", classes: "bg-leaf-100 text-leaf-800" },
  rejected: { label: "Rejected", classes: "bg-red-100 text-red-700" },
  not_eligible: { label: "Not Eligible", classes: "bg-gray-100 text-gray-600" },
};

export default function StatusBadge({ status }: { status: GrantStatus }) {
  const { label, classes } = config[status] ?? config.discovered;
  return (
    <span className={`inline-block px-2 py-0.5 rounded-full text-xs font-semibold ${classes}`}>
      {label}
    </span>
  );
}
