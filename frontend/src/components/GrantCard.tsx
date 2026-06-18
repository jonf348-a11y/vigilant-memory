import { ExternalLink, PoundSterling, Calendar, Tag } from "lucide-react";
import type { Grant } from "../types";
import StatusBadge from "./StatusBadge";

interface Props {
  grant: Grant;
  onSelect?: (grant: Grant) => void;
  actions?: React.ReactNode;
}

export default function GrantCard({ grant, onSelect, actions }: Props) {
  const maxAmountStr = grant.max_amount
    ? `£${grant.max_amount.toLocaleString()}`
    : null;

  return (
    <div
      className="bg-white rounded-xl border border-leaf-200 p-5 shadow-sm hover:shadow-md transition-shadow"
      onClick={onSelect ? () => onSelect(grant) : undefined}
      style={onSelect ? { cursor: "pointer" } : undefined}
    >
      <div className="flex items-start justify-between gap-3 mb-2">
        <div className="flex-1 min-w-0">
          <h3 className="font-semibold text-gray-900 leading-snug">{grant.title}</h3>
          <p className="text-sm text-leaf-700 font-medium mt-0.5">{grant.funder}</p>
        </div>
        <StatusBadge status={grant.status} />
      </div>

      <p className="text-sm text-gray-600 mb-3 line-clamp-3">{grant.description}</p>

      <div className="flex flex-wrap gap-3 text-xs text-gray-500 mb-3">
        {maxAmountStr && (
          <span className="flex items-center gap-1">
            <PoundSterling className="w-3 h-3" /> Up to {maxAmountStr}
          </span>
        )}
        {grant.deadline && (
          <span className="flex items-center gap-1">
            <Calendar className="w-3 h-3" /> {grant.deadline}
          </span>
        )}
      </div>

      {grant.focus_areas.length > 0 && (
        <div className="flex flex-wrap gap-1 mb-3">
          {grant.focus_areas.slice(0, 5).map((area) => (
            <span
              key={area}
              className="inline-flex items-center gap-1 bg-leaf-50 text-leaf-700 text-xs px-2 py-0.5 rounded-full border border-leaf-200"
            >
              <Tag className="w-2.5 h-2.5" />
              {area}
            </span>
          ))}
        </div>
      )}

      <div className="flex items-center justify-between mt-2">
        {grant.url ? (
          <a
            href={grant.url}
            target="_blank"
            rel="noreferrer"
            className="inline-flex items-center gap-1 text-xs text-leaf-600 hover:text-leaf-800 font-medium"
            onClick={(e) => e.stopPropagation()}
          >
            <ExternalLink className="w-3 h-3" /> View grant
          </a>
        ) : (
          <span />
        )}
        {actions && <div className="flex gap-2">{actions}</div>}
      </div>
    </div>
  );
}
