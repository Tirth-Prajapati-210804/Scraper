import {
  History,
  LayoutDashboard,
  LogOut,
  Plane,
  Table,
  Users,
} from "lucide-react";
import { NavLink } from "react-router-dom";
import { useAuth } from "../../context/AuthContext";
import { cn } from "../../utils/cn";

const BASE_NAV = [
  { to: "/", icon: LayoutDashboard, label: "Dashboard" },
  { to: "/explorer", icon: Table, label: "Data Explorer" },
  { to: "/logs", icon: History, label: "Collection Logs" },
];

export function Sidebar() {
  const { user, logout } = useAuth();
  const navItems = [
    ...BASE_NAV,
    ...(user?.role === "admin"
      ? [{ to: "/users", icon: Users, label: "User Management" }]
      : []),
  ];

  return (
    <aside className="flex w-56 flex-shrink-0 flex-col bg-slate-900">
      {/* Logo */}
      <div className="flex h-14 items-center gap-2.5 border-b border-slate-700/60 px-4">
        <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-brand-500">
          <Plane className="h-4 w-4 text-white" />
        </div>
        <span className="text-sm font-semibold text-white">
          Flight Tracker
        </span>
      </div>

      {/* Navigation */}
      <nav aria-label="Main navigation" className="flex-1 space-y-0.5 p-2 pt-3">
        {navItems.map(({ to, icon: Icon, label }) => (
          <NavLink
            key={to}
            to={to}
            end={to === "/"}
            className={({ isActive }) =>
              cn(
                "flex items-center gap-2.5 rounded-lg px-3 py-2 text-sm font-medium transition-colors",
                isActive
                  ? "bg-brand-600 text-white"
                  : "text-slate-400 hover:bg-slate-800 hover:text-white",
              )
            }
          >
            {({ isActive }) => (
              <>
                <Icon className="h-4 w-4 flex-shrink-0" aria-hidden="true" />
                <span aria-current={isActive ? "page" : undefined}>{label}</span>
              </>
            )}
          </NavLink>
        ))}
      </nav>

      {/* User info + logout */}
      <div className="border-t border-slate-700/60 p-3">
        <div className="mb-0.5 truncate px-2 text-xs font-semibold text-slate-200">
          {user?.full_name}
        </div>
        <div className="mb-2 px-2">
          <span className="truncate text-xs text-slate-500">{user?.email}</span>
        </div>
        <button
          onClick={logout}
          aria-label="Sign out"
          className="flex w-full items-center gap-2 rounded-lg px-3 py-2 text-sm text-slate-400 transition-colors hover:bg-red-900/40 hover:text-red-400"
        >
          <LogOut className="h-4 w-4" aria-hidden="true" />
          Sign out
        </button>
      </div>
    </aside>
  );
}
