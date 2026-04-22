import type { CollectionProgress } from "../api/collection";

interface Props {
  progress: CollectionProgress;
}

export function CollectionProgressBar({ progress }: Props) {
  const pct =
    progress.routes_total > 0
      ? Math.round((progress.routes_done / progress.routes_total) * 100)
      : 0;

  return (
    <div className="rounded-lg border border-brand-100 bg-brand-50 px-4 py-3">
      <div className="mb-1.5 flex items-center justify-between text-xs text-brand-700">
        <span className="font-medium">Collecting prices…</span>
        <span>
          {progress.routes_done}/{progress.routes_total} routes &middot;{" "}
          {progress.dates_scraped.toLocaleString()} prices
        </span>
      </div>
      <div className="h-1.5 w-full overflow-hidden rounded-full bg-brand-200">
        <div
          className="h-full rounded-full bg-brand-500 transition-all duration-500"
          style={{ width: `${pct}%` }}
        />
      </div>
      {progress.current_origin && (
        <p className="mt-1.5 text-xs text-brand-600">
          Current origin:{" "}
          <span className="font-mono font-semibold">{progress.current_origin}</span>
          {progress.routes_failed > 0 && (
            <span className="ml-3 text-red-500">
              {progress.routes_failed} failed
            </span>
          )}
        </p>
      )}
    </div>
  );
}
