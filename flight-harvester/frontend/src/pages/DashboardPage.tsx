import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Activity,
  Database,
  FolderOpen,
  Globe,
  MapPin,
  Play,
  Plus,
  Square,
} from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { fetchCollectionRuns, getCollectionStatus, stopCollection, triggerCollection } from "../api/collection";
import { getErrorMessage } from "../api/client";
import { listRouteGroups } from "../api/route-groups";
import { fetchHealth, fetchOverviewStats } from "../api/stats";
import { CollectionProgressBar } from "../components/CollectionProgressBar";
import { ErrorBoundary } from "../components/ErrorBoundary";
import { ProviderStatus } from "../components/ProviderStatus";
import { RouteGroupCard } from "../components/RouteGroupCard";
import { RouteGroupForm } from "../components/RouteGroupForm";
import { StatCard } from "../components/StatCard";
import { Button } from "../components/ui/Button";
import { Skeleton } from "../components/ui/Skeleton";
import { useToast } from "../context/ToastContext";
import { formatRelativeTime, formatNumber } from "../utils/format";
import { usePageTitle } from "../utils/usePageTitle";

export function DashboardPage() {
  usePageTitle("Dashboard");
  const { showToast } = useToast();
  const qc = useQueryClient();
  const [triggering, setTriggering] = useState(false);
  const [createOpen, setCreateOpen] = useState(false);
  const wasCollecting = useRef(false);

  const statsQuery = useQuery({
    queryKey: ["stats"],
    queryFn: fetchOverviewStats,
    refetchInterval: 60_000,
  });

  const groupsQuery = useQuery({
    queryKey: ["route-groups"],
    queryFn: listRouteGroups,
  });

  const healthQuery = useQuery({
    queryKey: ["health"],
    queryFn: fetchHealth,
    refetchInterval: 30_000,
  });

  const statusQuery = useQuery({
    queryKey: ["collection-status"],
    queryFn: getCollectionStatus,
    refetchInterval: (query) => (query.state.data?.is_collecting ? 3_000 : 15_000),
  });

  const stopMut = useMutation({
    mutationFn: stopCollection,
    onSuccess: () => {
      showToast("Stop signal sent", "success");
      qc.invalidateQueries({ queryKey: ["collection-status"] });
    },
    onError: () => showToast("Failed to stop collection", "error"),
  });

  const isCollecting = statusQuery.data?.is_collecting ?? false;

  // Detect when collection finishes and show a summary toast
  useEffect(() => {
    if (wasCollecting.current && !isCollecting) {
      fetchCollectionRuns(1).then((runs) => {
        const last = runs[0];
        if (!last) return;
        if (last.status === "completed") {
          const errors = last.routes_failed ?? 0;
          const success = last.routes_success ?? 0;
          if (errors > 0) {
            showToast(
              `Collection finished — ${success} prices collected, ${errors} route(s) failed. Check Collection Logs for details.`,
              "error"
            );
          } else {
            showToast(`Collection finished — ${success} prices collected successfully.`, "success");
          }
        } else if (last.status === "stopped") {
          showToast("Collection was stopped.", "info");
        } else if (last.status === "failed") {
          showToast("Collection failed. Check Collection Logs for details.", "error");
        }
        qc.invalidateQueries({ queryKey: ["stats"] });
        qc.invalidateQueries({ queryKey: ["route-groups"] });
      }).catch(() => {});
    }
    wasCollecting.current = isCollecting;
  }, [isCollecting, showToast, qc]);

  const stats = statsQuery.data;
  const groups = groupsQuery.data ?? [];
  const health = healthQuery.data;
  const noProvider =
    !healthQuery.isLoading &&
    health?.provider_status?.serpapi !== "configured" &&
    !health?.demo_mode;

  async function handleTriggerAll() {
    setTriggering(true);
    try {
      const res = await triggerCollection();
      if (res.status === "already_running") {
        showToast("Collection is already running", "info");
      } else {
        showToast("Collection triggered successfully", "success");
        qc.invalidateQueries({ queryKey: ["collection-status"] });
      }
    } catch (err) {
      showToast(getErrorMessage(err, "Failed to trigger collection"), "error");
    } finally {
      setTriggering(false);
    }
  }

  return (
    <ErrorBoundary>
      <div className="space-y-6">
        {/* No-provider warning banner */}
        {noProvider && (
          <div className="flex items-start gap-3 rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800">
            <span className="mt-0.5 text-lg leading-none">⚠️</span>
            <div>
              <p className="font-semibold">No API key configured</p>
              <p className="mt-0.5 text-amber-700">
                Add <code className="rounded bg-amber-100 px-1 font-mono text-xs">SERPAPI_KEY</code> to{" "}
                <code className="rounded bg-amber-100 px-1 font-mono text-xs">backend/.env</code> to collect real prices.
                Or set <code className="rounded bg-amber-100 px-1 font-mono text-xs">DEMO_MODE=true</code> to use fake data for testing.
              </p>
            </div>
          </div>
        )}

        {/* Demo mode notice */}
        {health?.demo_mode && (
          <div className="flex items-center gap-3 rounded-lg border border-blue-200 bg-blue-50 px-4 py-3 text-sm text-blue-800">
            <span className="text-lg leading-none">🧪</span>
            <p>
              <span className="font-semibold">Demo mode active</span> — prices are fake and generated locally. Switch to a real{" "}
              <code className="rounded bg-blue-100 px-1 font-mono text-xs">SERPAPI_KEY</code> for production use.
            </p>
          </div>
        )}

        {/* Header row */}
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-lg font-semibold text-slate-900">Overview</h2>
            {stats?.last_collection_at && (
              <p className="text-sm text-slate-500">
                Last collection: {formatRelativeTime(stats.last_collection_at)}
              </p>
            )}
          </div>
          <div className="flex gap-2">
            <Button
              variant="secondary"
              onClick={() => setCreateOpen(true)}
            >
              <Plus className="h-4 w-4" />
              New group
            </Button>
            {isCollecting ? (
              <Button
                variant="secondary"
                onClick={() => stopMut.mutate()}
                loading={stopMut.isPending}
                className="border-red-200 text-red-600 hover:bg-red-50"
              >
                <Square className="h-4 w-4" />
                Stop collection
              </Button>
            ) : (
              <Button
                variant="secondary"
                onClick={handleTriggerAll}
                loading={triggering}
              >
                <Play className="h-4 w-4" />
                Trigger collection
              </Button>
            )}
          </div>
        </div>

        {/* Live collection progress bar */}
        {isCollecting && statusQuery.data?.progress && (
          <CollectionProgressBar progress={statusQuery.data.progress} />
        )}

        {/* Stat cards */}
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {statsQuery.isLoading ? (
            <>
              {[...Array(4)].map((_, i) => (
                <Skeleton key={i} className="h-20 rounded-xl" />
              ))}
            </>
          ) : (
            <>
              <StatCard
                label="Route Groups"
                value={stats?.active_route_groups ?? 0}
                icon={Globe}
              />
              <StatCard
                label="Prices Collected"
                value={stats ? formatNumber(stats.total_prices_collected) : "0"}
                icon={Database}
              />
              <StatCard
                label="Origins"
                value={stats?.total_origins ?? 0}
                icon={MapPin}
              />
              <StatCard
                label="Last Run"
                value={
                  stats?.last_collection_at
                    ? formatRelativeTime(stats.last_collection_at)
                    : "Never"
                }
                icon={Activity}
              />
            </>
          )}
        </div>

        {/* Route Group Cards */}
        <div>
          <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-slate-500">
            Route Groups
          </h2>
          {groupsQuery.isLoading ? (
            <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
              {[...Array(2)].map((_, i) => (
                <Skeleton key={i} className="h-52 rounded-xl" />
              ))}
            </div>
          ) : groups.length === 0 ? (
            <div className="flex flex-col items-center gap-3 rounded-xl border border-dashed border-slate-200 p-12 text-center">
              <FolderOpen className="h-10 w-10 text-slate-300" />
              <div>
                <p className="text-sm font-medium text-slate-500">No route groups yet</p>
                <p className="mt-1 text-xs text-slate-400">
                  Create a group to start collecting flight prices.
                </p>
              </div>
              <button
                onClick={() => setCreateOpen(true)}
                className="mt-1 flex items-center gap-1.5 rounded-lg bg-brand-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-brand-700"
              >
                <Plus className="h-4 w-4" />
                New group
              </button>
            </div>
          ) : (
            <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
              {groups.map((group) => (
                <RouteGroupCard key={group.id} group={group} />
              ))}
            </div>
          )}
        </div>

        {/* Provider Status */}
        <div>
          <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-slate-500">
            Provider Status
          </h2>
          {healthQuery.isLoading ? (
            <Skeleton className="h-16 rounded-xl" />
          ) : (
            <ProviderStatus health={health} />
          )}
        </div>
      </div>

      {createOpen && (
        <RouteGroupForm
          open={createOpen}
          onClose={() => setCreateOpen(false)}
          initial={null}
        />
      )}
    </ErrorBoundary>
  );
}
