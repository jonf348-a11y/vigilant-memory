import { NavLink } from "react-router-dom";
import {
  LayoutDashboard,
  Search,
  ClipboardList,
  MessageSquare,
  Leaf,
} from "lucide-react";

const links = [
  { to: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { to: "/find", label: "Find Grants", icon: Search },
  { to: "/tracker", label: "Track Applications", icon: ClipboardList },
  { to: "/apply", label: "Apply Helper", icon: MessageSquare },
];

export default function Sidebar() {
  return (
    <aside className="w-64 bg-leaf-800 text-white flex flex-col min-h-screen shrink-0">
      <div className="p-5 border-b border-leaf-700">
        <div className="flex items-center gap-2 mb-1">
          <Leaf className="w-6 h-6 text-leaf-300" />
          <span className="font-bold text-lg text-leaf-100">Grant Agent</span>
        </div>
        <p className="text-xs text-leaf-400">HEAT &amp; HEAG · Hethersett</p>
      </div>

      <nav className="flex-1 p-3 space-y-1">
        {links.map(({ to, label, icon: Icon }) => (
          <NavLink
            key={to}
            to={to}
            className={({ isActive }) =>
              `flex items-center gap-3 px-4 py-2.5 rounded-lg text-sm font-medium transition-colors ${
                isActive
                  ? "bg-leaf-600 text-white"
                  : "text-leaf-200 hover:bg-leaf-700 hover:text-white"
              }`
            }
          >
            <Icon className="w-4 h-4 shrink-0" />
            {label}
          </NavLink>
        ))}
      </nav>

      <div className="p-4 border-t border-leaf-700">
        <p className="text-xs text-leaf-500 leading-relaxed">
          Helping Hethersett reach net zero, one grant at a time.
        </p>
      </div>
    </aside>
  );
}
