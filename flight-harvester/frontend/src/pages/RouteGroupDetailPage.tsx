import { useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowLeft, Download, Pencil, RefreshCw } from "lucide-react";
import { useCallback, useRef, useState } from "react";
import type { DailyPrice } from "../types/price";
import { Link, useParams } from "react-router-dom";
import {
  downloadExport,
  getRouteGroup,
  getRouteGroupProgress,
  saveBlobAsFile,
} from "../api/route-groups";
import { triggerGroupCollection, triggerGroupCollectionDate } from "../api/collection";
import { getErrorMessage } from "../api/client";
import { fetchPriceTrend, fetchPrices } from "../api/prices";
import { ErrorBoundary } from "../components/ErrorBoundary";
import { DateCoverageGrid } from "../components/DateCoverageGrid";
import { PriceChart } from "../components/PriceChart";
import { PriceTable } from "../components/PriceTable";
import { RouteGroupForm } from "../components/RouteGroupForm";
import { Button } from "../components/ui/Button";
import { Card } from "../components/ui/Card";
import { Skeleton } from "../components/ui/Skeleton";
import { useToast } from "../context/ToastContext";
import { usePageTitle } from "../utils/usePageTitle";

export function RouteGroupDetailPage() {
  const { id } = useParams<{ id: string }>();
  const qc = useQueryClient();
  const { showToast } = useToast();
  const [editOpen, setEditOpen] = useState(false);
  const [downloading, setDownloading] = useState(false);
  const [triggering, setTriggering] = useState(false);
  const [confirmTrigger, setConfirmTrigger] = useState(false);
  const [selectedOrigin, setSelectedOrigin] = useState<string>("");
  const [allPrices, setAllPrices] = useState<DailyPrice[]>([]);
  const [pricesLoading, setPricesLoading] = useState(false);
  const [priceHasMore, setPriceHasMore] = useState(false);
  const priceOffsetRef = useRef(0);
  const PRICE_PAGE = 100;

  const groupQuery = useQuery({
    queryKey: ["route-group", id],
    queryFn: () => getRouteGroup(id!),
    enabled: !!id,
  });

  const progressQuery = useQuery({
    queryKey: ["route-group-progress", id],
    queryFn: () => getRouteGroupProgress(id!),
    enabled: !!id,
    refetchInterval: 60_000,
  });

  const group = groupQuery.data;
  const originForQuery = selectedOrigin || group?.origins[0] || "";
  const destForQuery = group?.destinations[0] || "";

  const trendQuery = useQuery({
    queryKey: ["price-trend", id, originForQuery, destForQuery],
    queryFn: () =>
      fetchPriceTrend({ origin: originForQuery, destination: destForQuery, route_group_id: id }),
    enabled: !!originForQuery && !!destForQuery,
  });

  const loadPrices = useCallback(async (origin: string, newOffset: number) => {
    if (!id) return;
    setPricesLoading(true);
    try {
      const data = await fetchPrices({
        route_group_id: id,
        origin: origin || undefined,
        limit: PRICE_PAGE,
        offset: newOffset,
      });
      setAllPrices((prev) => (newOffset === 0 ? data : [...prev, ...data]));
      setPriceHasMore(data.length === PRICE_PAGE);
      priceOffsetRef.current = newOffset;
    } finally {
      setPricesLoading(false);
    }
  }, [id, PRICE_PAGE]);

  // Load first page when group is ready
  const groupLoaded = !!groupQuery.data;
  const loadedRef = useRef(false);
  if (groupLoaded && !loadedRef.current) {
    loadedRef.current = true;
    loadPrices(selectedOrigin, 0);
  }

  const handlePriceLoadMore = useCallback(
    () => loadPrices(selectedOrigin, priceOffsetRef.current + PRICE_PAGE),
    [selectedOrigin, loadPrices, PRICE_PAGE],
  );

  usePageTitle(group?.name ?? "Route Group");

  async function handleDownload() {
    if (!group) return;
    setDownloading(true);
    try {
      const blob = await downloadExport(group.id);
      saveBlobAsFile(blob, `${group.name.replace(/[^a-z0-9_-]/gi, "_")}.xlsx`);
      showToast("Excel downloaded", "success");
    } catch {
      showToast("Download failed", "error");
    } finally {
      setDownloading(false);
    }
  }

  async function handleTrigger() {
    if (!id) return;
    setConfirmTrigger(false);
    setTriggering(true);
    try {
      await triggerGroupCollection(id);
      showToast("Collection triggered successfully", "success");
      qc.invalidateQueries({ queryKey: ["route-group-progress", id] });
    } catch (err) {
      showToast(getErrorMessage(err, "Failed to trigger collection"), "error");
    } finally {
      setTriggering(false);
    }
  }

  async function handleRescrapeDate(date: string) {
    if (!id) return;
    try {
      await triggerGroupCollectionDate(id, date);
      showToast(`Re-scrape triggered for ${date}`, "success");
      qc.invalidateQueries({ queryKey: ["route-group-progress", id] });
    } catch (err) {
      showToast(getErrorMessage(err, "Failed to trigger re-scrape"), "error");
    }
  }

  if (groupQuery.isLoading) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-8 w-64" />
        <Skeleton className="h-48 rounded-xl" />
      </div>
    );
  }

  if (!group) {
    return (
      <div className="py-16 text-center text-slate-400">
        Route group not found.{" "}
        <Link to="/" className="text-brand-600 hover:underline">
          Back to dashboard
        </Link>
      </div>
    );
  }

  return (
    <ErrorBoundary>
    <div className="space-y-6">
      {/* Back + Actions */}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <Link
          to="/"
          className="flex items-center gap-1.5 text-sm text-slate-500 hover:text-slate-800"
        >
          <ArrowLeft className="h-4 w-4" />
          Back to Dashboard
        </Link>
        <div className="flex items-center gap-2">
          <Button variant="secondary" onClick={() => setEditOpen(true)}>
            <Pencil className="h-4 w-4" />
            Edit
          </Button>
          <Button
            variant="secondary"
            onClick={() => setConfirmTrigger(true)}
            loading={triggering}
          >
            <RefreshCw className="h-4 w-4" />
            Trigger Scrape
          </Button>
          <Button
            variant="primary"
            onClick={handleDownload}
            loading={downloading}
          >
            <Download className="h-4 w-4" />
            Download Excel
          </Button>
        </div>
      </div>

      {/* Group Header */}
      <Card>
        <h2 className="text-lg font-bold text-slate-900">{group.name}</h2>
        <p className="mt-1 text-sm text-slate-500">
          Destination: {group.destination_label} · {group.nights} nights ·{" "}
          {group.days_ahead} days ahead · Currency: {group.currency}
          {` · Stops: ${group.max_stops == null ? "Any" : group.max_stops === 0 ? "Direct" : group.max_stops}`}
          {group.start_date && ` · From: ${group.start_date}`}
          {group.end_date && ` · To: ${group.end_date}`}
        </p>
        <p className="mt-1 text-sm text-slate-500">
          Origins: {group.origins.join(", ")}
        </p>
      </Card>

      {/* Progress */}
      <Card>
        <h3 className="mb-4 text-sm font-semibold text-slate-700">
          Collection Progress
        </h3>
        {progressQuery.isLoading ? (
          <Skeleton className="h-32" />
        ) : progressQuery.isError ? (
          <p className="text-sm text-red-500">Failed to load progress. Try refreshing the page.</p>
        ) : progressQuery.data ? (
          <DateCoverageGrid progress={progressQuery.data} onRescrapeDate={handleRescrapeDate} />
        ) : (
          <p className="text-sm text-slate-400">No data collected yet. Trigger a collection to start.</p>
        )}
      </Card>

      {/* Price Trend */}
      <Card>
        <div className="mb-4 flex items-center justify-between gap-4">
          <h3 className="text-sm font-semibold text-slate-700">Price Trend</h3>
          <div className="flex items-center gap-2">
            <span className="text-xs text-slate-500">Origin:</span>
            <select
              aria-label="Filter by origin"
              value={selectedOrigin || group.origins[0]}
              onChange={(e) => { const o = e.target.value; setSelectedOrigin(o); setAllPrices([]); loadPrices(o, 0); }}
              className="rounded-lg border border-slate-300 bg-white px-2 py-1 text-sm focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
            >
              {group.origins.map((o) => (
                <option key={o} value={o}>
                  {o}
                </option>
              ))}
            </select>
            {group.destinations.length > 1 && (
              <>
                <span className="text-xs text-slate-500">→ {destForQuery}</span>
              </>
            )}
          </div>
        </div>
        {trendQuery.isLoading ? (
          <Skeleton className="h-64" />
        ) : trendQuery.isError ? (
          <p className="py-8 text-center text-sm text-red-500">Failed to load price trend data.</p>
        ) : (trendQuery.data ?? []).length === 0 ? (
          <p className="py-8 text-center text-sm text-slate-400">No price data yet for this route. Trigger a collection first.</p>
        ) : (
          <PriceChart data={trendQuery.data ?? []} />
        )}
      </Card>

      {/* Price Table */}
      <Card>
        <div className="mb-4 flex items-center justify-between gap-4">
          <h3 className="text-sm font-semibold text-slate-700">Price Data</h3>
          <div className="flex items-center gap-2">
            <span className="text-xs text-slate-500">Filter by origin:</span>
            <select
              aria-label="Filter by origin"
              value={selectedOrigin}
              onChange={(e) => { const o = e.target.value; setSelectedOrigin(o); setAllPrices([]); loadPrices(o, 0); }}
              className="rounded-lg border border-slate-300 bg-white px-2 py-1 text-sm focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
            >
              <option value="">All origins</option>
              {group.origins.map((o) => (
                <option key={o} value={o}>
                  {o}
                </option>
              ))}
            </select>
            {allPrices.length > 0 && (
              <span className="text-xs text-slate-400">
                {allPrices.length} rows{priceHasMore ? "+" : ""}
              </span>
            )}
          </div>
        </div>
        <PriceTable
            prices={allPrices}
            isLoading={pricesLoading && allPrices.length === 0}
            hasMore={priceHasMore}
            onLoadMore={handlePriceLoadMore}
            loadingMore={pricesLoading && allPrices.length > 0}
            groupCurrency={group.currency}
          />
      </Card>

      {editOpen && (
        <RouteGroupForm
          open={editOpen}
          onClose={() => setEditOpen(false)}
          initial={group}
        />
      )}

      {confirmTrigger && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
          <div className="mx-4 w-full max-w-sm rounded-xl bg-white p-6 shadow-xl">
            <h3 className="text-base font-semibold text-slate-900">Trigger Full Scrape?</h3>
            <p className="mt-2 text-sm text-slate-500">
              This will start a collection run for all dates in <span className="font-medium">{group.name}</span>. Already-collected dates will be overwritten.
            </p>
            <div className="mt-5 flex justify-end gap-2">
              <Button variant="secondary" onClick={() => setConfirmTrigger(false)}>
                Cancel
              </Button>
              <Button variant="primary" onClick={handleTrigger} loading={triggering}>
                Yes, trigger
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
    </ErrorBoundary>
  );
}
