import { useQuery } from "@tanstack/react-query";
import { fetchHealth } from "../../api/stats";
import { formatRelativeTime } from "../../utils/format";

interface TopBarProps {
  title: string;
}

export function TopBar({ title }: TopBarProps) {
  const { data: health } = useQuery({
    queryKey: ["health"],
    queryFn: fetchHealth,
    refetchInterval: 30_000,
  });

  const isRunning = health?.scheduler_running ?? false;

  return (
    <header className="flex h-14 items-center justify-between border-b border-slate-200 bg-white px-6">
      <h1 className="text-base font-semibold text-slate-900">{title}</h1>

      <div className="flex items-center gap-3 text-sm text-slate-500">
        <span className="flex items-center gap-1.5">
          <span
            className={`inline-block h-2 w-2 rounded-full ${
              isRunning ? "bg-green-500" : "bg-slate-300"
            }`}
          />
          {isRunning ? "Scheduler running" : "Scheduler stopped"}
        </span>
        {health && (
          <span className="text-slate-400">
            DB:{" "}
            <span
              className={
                health.database_status === "ok"
                  ? "text-green-600"
                  : "text-red-500"
              }
            >
              {health.database_status}
            </span>
          </span>
        )}
      </div>
    </header>
  );
}

export function TopBarWithLastRun({
  title,
  lastRunAt,
}: {
  title: string;
  lastRunAt?: string | null;
}) {
  const { data: health } = useQuery({
    queryKey: ["health"],
    queryFn: fetchHealth,
    refetchInterval: 30_000,
  });

  const isRunning = health?.scheduler_running ?? false;

  return (
    <header className="flex h-14 items-center justify-between border-b border-slate-200 bg-white px-6">
      <h1 className="text-base font-semibold text-slate-900">{title}</h1>

      <div className="flex items-center gap-4 text-sm text-slate-500">
        {lastRunAt && (
          <span>Last collection: {formatRelativeTime(lastRunAt)}</span>
        )}
        <span className="flex items-center gap-1.5">
          <span
            className={`inline-block h-2 w-2 rounded-full ${
              isRunning ? "bg-green-500" : "bg-slate-300"
            }`}
          />
          {isRunning ? "Scheduler active" : "Scheduler idle"}
        </span>
      </div>
    </header>
  );
}
