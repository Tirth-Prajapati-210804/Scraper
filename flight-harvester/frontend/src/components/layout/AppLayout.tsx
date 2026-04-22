import { type ReactNode } from "react";
import { useLocation, useMatch } from "react-router-dom";
import { TopBar } from "./TopBar";
import { Sidebar } from "./Sidebar";

function usePageTitle(): string {
  const location = useLocation();
  const isDetail = useMatch("/route-groups/:id");
  if (isDetail) return "Route Group Detail";
  const titles: Record<string, string> = {
    "/": "Dashboard",
    "/explorer": "Data Explorer",
    "/logs": "Collection Logs",
  };
  return titles[location.pathname] ?? "Flight Price Tracker";
}

interface AppLayoutProps {
  children: ReactNode;
}

export function AppLayout({ children }: AppLayoutProps) {
  const title = usePageTitle();

  return (
    <div className="flex h-screen overflow-hidden">
      <Sidebar />
      <div className="flex flex-1 flex-col overflow-hidden">
        <TopBar title={title} />
        <main className="flex-1 overflow-y-auto p-6">{children}</main>
      </div>
    </div>
  );
}
