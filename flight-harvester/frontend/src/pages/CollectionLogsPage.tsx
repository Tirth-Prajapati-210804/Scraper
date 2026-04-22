import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Square } from "lucide-react";
import { useMemo, useState } from "react";
import {
  fetchCollectionRuns,
  fetchScrapeLogs,
  getCollectionStatus,
  stopCollection,
} from "../api/collection";
import { listRouteGroups } from "../api/route-groups";
import { CollectionRunsTable } from "../components/CollectionRunsTable";
import { ErrorBoundary } from "../components/ErrorBoundary";
import { ScrapeLogsTable } from "../components/ScrapeLogsTable";
import { Card } from "../components/ui/Card";
import { Select } from "../components/ui/Select";
import { useToast } from "../context/ToastContext";
import type { ScrapeLogEntry } from "../types/price";
import { usePageTitle } from "../utils/usePageTitle";

export function CollectionLogsPage() {
  usePageTitle("Collection Logs");
  const qc = useQueryClient();
  const { showToast } = useToast();
  const [filterGroupId, setFilterGroupId] = useState("");
  const [filterProvider, setFilterProvider] = useState("");
  const [filterStatus, setFilterStatus] = useState("");

  const groupsQuery = useQuery({
    queryKey: ["route-groups"],
    queryFn: listRouteGroups,
  });

  const statusQuery = useQuery({
    queryKey: ["collection-status"],
    queryFn: getCollectionStatus,
    // Poll faster when collecting so the banner disappears quickly after stop
    refetchInterval: (query) => (query.state.data?.is_collecting ? 3_000 : 15_000),
  });

  const runsQuery = useQuery({
    queryKey: ["collection-runs"],
    queryFn: () => fetchCollectionRuns(20),
    // Refresh more often while a run is in progress
    refetchInterval: statusQuery.data?.is_collecting ? 5_000 : 30_000,
  });

  const logsQuery = useQuery({
    queryKey: ["scrape-logs", filterGroupId],
    queryFn: () =>
      fetchScrapeLogs({
        route_group_id: filterGroupId || undefined,
        limit: 100,
      }),
    refetchInterval: 30_000,
  });

  const stopMut = useMutation({
    mutationFn: stopCollection,
    onSuccess: (data) => {
      if (data.status === "stop_requested") {
        showToast("Stop signal sent — collection will finish its current batch", "success");
      } else {
        showToast("No collection is running", "info");
      }
      // Invalidate status + runs so the UI updates promptly
      qc.invalidateQueries({ queryKey: ["collection-status"] });
      qc.invalidateQueries({ queryKey: ["collection-runs"] });
    },
    onError: () => showToast("Failed to stop collection", "error"),
  });

  // Client-side filter by provider and status
  const filteredLogs = useMemo<ScrapeLogEntry[]>(() => {
    let logs = logsQuery.data ?? [];
    if (filterProvider)
      logs = logs.filter((l) => l.provider === filterProvider);
    if (filterStatus)
      logs = logs.filter((l) => l.status === filterStatus);
    return logs;
  }, [logsQuery.data, filterProvider, filterStatus]);

  // Unique providers from current logs for filter dropdown
  const providers = useMemo(() => {
    const set = new Set((logsQuery.data ?? []).map((l) => l.provider));
    return [...set].sort();
  }, [logsQuery.data]);

  const isCollecting = statusQuery.data?.is_collecting ?? false;

  return (
    <ErrorBoundary>
      <div className="space-y-6">
        {/* Running banner with stop button */}
        {isCollecting && (
          <div className="flex items-center justify-between rounded-xl border border-brand-200 bg-brand-50 px-4 py-3">
            <div className="flex items-center gap-2 text-sm text-brand-700">
              <span className="inline-block h-2 w-2 animate-pulse rounded-full bg-brand-500" />
              Collection in progress…
            </div>
            <button
              onClick={() => stopMut.mutate()}
              disabled={stopMut.isPending}
              className="inline-flex items-center gap-1.5 rounded-lg bg-red-600 px-3 py-1.5 text-xs font-semibold text-white hover:bg-red-700 disabled:opacity-60"
            >
              <Square className="h-3 w-3" />
              {stopMut.isPending ? "Stopping…" : "Stop collection"}
            </button>
          </div>
        )}

        {/* Last run error summary */}
        {(() => {
          const last = runsQuery.data?.[0];
          if (!last || !last.errors?.length) return null;
          return (
            <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800">
              <p className="font-semibold">Last collection had {last.errors.length} route failure(s):</p>
              <ul className="mt-1 list-inside list-disc space-y-0.5 text-red-700">
                {last.errors.slice(0, 5).map((e: string, i: number) => (
                  <li key={i} className="font-mono text-xs">{e}</li>
                ))}
                {last.errors.length > 5 && (
                  <li className="text-xs">…and {last.errors.length - 5} more. Check scrape logs below.</li>
                )}
              </ul>
            </div>
          );
        })()}

        {/* Collection Runs */}
        <Card>
          <h3 className="mb-4 text-sm font-semibold text-slate-700">
            Collection Runs
          </h3>
          <CollectionRunsTable
            runs={runsQuery.data ?? []}
            isLoading={runsQuery.isLoading}
            onStop={() => stopMut.mutate()}
            stopping={stopMut.isPending}
          />
        </Card>

        {/* Scrape Logs */}
        <Card>
          <div className="mb-4 space-y-3">
            <h3 className="text-sm font-semibold text-slate-700">
              Recent Scrape Logs (latest 100)
            </h3>
            {/* Filters */}
            <div className="flex flex-wrap items-end gap-3">
              <div className="min-w-[180px]">
                <Select
                  label="Route Group"
                  value={filterGroupId}
                  onChange={(e) => setFilterGroupId(e.target.value)}
                >
                  <option value="">All groups</option>
                  {groupsQuery.data?.map((g) => (
                    <option key={g.id} value={g.id}>
                      {g.name}
                    </option>
                  ))}
                </Select>
              </div>

              <div className="min-w-[130px]">
                <Select
                  label="Provider"
                  value={filterProvider}
                  onChange={(e) => setFilterProvider(e.target.value)}
                >
                  <option value="">All providers</option>
                  {providers.map((p) => (
                    <option key={p} value={p}>
                      {p}
                    </option>
                  ))}
                </Select>
              </div>

              <div className="min-w-[130px]">
                <Select
                  label="Status"
                  value={filterStatus}
                  onChange={(e) => setFilterStatus(e.target.value)}
                >
                  <option value="">All statuses</option>
                  <option value="success">Success</option>
                  <option value="error">Error</option>
                  <option value="no_results">No results</option>
                  <option value="rate_limited">Rate limited</option>
                </Select>
              </div>

              {filteredLogs.length !== (logsQuery.data?.length ?? 0) && (
                <span className="mt-5 text-xs text-slate-400">
                  {filteredLogs.length} / {logsQuery.data?.length ?? 0} shown
                </span>
              )}
            </div>
          </div>

          <ScrapeLogsTable
            logs={filteredLogs}
            isLoading={logsQuery.isLoading}
          />
        </Card>
      </div>
    </ErrorBoundary>
  );
}
