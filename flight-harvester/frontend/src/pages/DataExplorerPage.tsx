import { useQuery } from "@tanstack/react-query";
import { Download, Search } from "lucide-react";
import { useCallback, useMemo, useRef, useState } from "react";
import type { DailyPrice } from "../types/price";
import { fetchPriceTrend, fetchPrices } from "../api/prices";
import { listRouteGroups } from "../api/route-groups";
import { ErrorBoundary } from "../components/ErrorBoundary";
import { PriceChart } from "../components/PriceChart";
import { PriceTable } from "../components/PriceTable";
import { Button } from "../components/ui/Button";
import { Card } from "../components/ui/Card";
import { usePageTitle } from "../utils/usePageTitle";
import { DateRangeInput } from "../components/ui/DateRangeInput";
import { Select } from "../components/ui/Select";

interface Filters {
  route_group_id: string;
  origin: string;
  date_from: string;
  date_to: string;
}

const EMPTY_FILTERS: Filters = {
  route_group_id: "",
  origin: "",
  date_from: "",
  date_to: "",
};

const PAGE_SIZE = 100;

function exportCsv(rows: DailyPrice[]) {
  const header = "Date,Origin,Destination,Airline,Price,Currency,Stops,Duration(min),Provider\n";
  const lines = rows.map((r) =>
    [
      r.depart_date,
      r.origin,
      r.destination,
      r.airline,
      r.price,
      r.currency ?? "",
      r.stops ?? "",
      r.duration_minutes ?? "",
      r.provider,
    ].join(","),
  );
  const blob = new Blob([header + lines.join("\n")], { type: "text/csv" });
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = "prices.csv";
  a.click();
  URL.revokeObjectURL(a.href);
}

export function DataExplorerPage() {
  usePageTitle("Data Explorer");
  const [pending, setPending] = useState<Filters>(EMPTY_FILTERS);
  const [applied, setApplied] = useState<Filters>(EMPTY_FILTERS);
  const [allPrices, setAllPrices] = useState<DailyPrice[]>([]);
  const [pricesLoading, setPricesLoading] = useState(false);
  const [hasMore, setHasMore] = useState(false);
  const offsetRef = useRef(0);

  // Client-side filters
  const [airlineFilter, setAirlineFilter] = useState("");
  const [minPrice, setMinPrice] = useState("");
  const [maxPrice, setMaxPrice] = useState("");

  const groupsQuery = useQuery({
    queryKey: ["route-groups"],
    queryFn: listRouteGroups,
  });

  const selectedGroup = groupsQuery.data?.find(
    (g) => g.id === pending.route_group_id,
  );

  function handleGroupChange(id: string) {
    setPending({ ...EMPTY_FILTERS, route_group_id: id });
  }

  const loadPrices = useCallback(async (filters: Filters, newOffset: number) => {
    if (!filters.route_group_id) return;
    setPricesLoading(true);
    try {
      const data = await fetchPrices({
        route_group_id: filters.route_group_id,
        origin: filters.origin || undefined,
        date_from: filters.date_from || undefined,
        date_to: filters.date_to || undefined,
        limit: PAGE_SIZE,
        offset: newOffset,
      });
      setAllPrices((prev) => (newOffset === 0 ? data : [...prev, ...data]));
      setHasMore(data.length === PAGE_SIZE);
      offsetRef.current = newOffset;
    } finally {
      setPricesLoading(false);
    }
  }, []);

  function handleApply() {
    const next = { ...pending };
    setApplied(next);
    setAllPrices([]);
    setAirlineFilter("");
    setMinPrice("");
    setMaxPrice("");
    loadPrices(next, 0);
  }

  const handleLoadMore = useCallback(() => {
    loadPrices(applied, offsetRef.current + PAGE_SIZE);
  }, [applied, loadPrices]);

  // Trend chart — needs origin + destination
  const appliedGroup = groupsQuery.data?.find(
    (g) => g.id === applied.route_group_id,
  );
  const trendOrigin = applied.origin || appliedGroup?.origins[0] || "";
  const trendDest = appliedGroup?.destinations[0] || "";

  const trendQuery = useQuery({
    queryKey: ["explorer-trend", applied, trendOrigin, trendDest],
    queryFn: () =>
      fetchPriceTrend({
        origin: trendOrigin,
        destination: trendDest,
        date_from: applied.date_from || undefined,
        date_to: applied.date_to || undefined,
      }),
    enabled: !!trendOrigin && !!trendDest,
  });

  // Unique airlines from fetched rows (for client-side filter dropdown)
  const airlines = useMemo(
    () => [...new Set(allPrices.map((p) => p.airline))].filter(Boolean).sort(),
    [allPrices],
  );

  // Apply client-side filters
  const filteredPrices = useMemo(() => {
    let rows = allPrices;
    if (airlineFilter) rows = rows.filter((p) => p.airline === airlineFilter);
    if (minPrice !== "") rows = rows.filter((p) => p.price >= Number(minPrice));
    if (maxPrice !== "") rows = rows.filter((p) => p.price <= Number(maxPrice));
    return rows;
  }, [allPrices, airlineFilter, minPrice, maxPrice]);

  return (
    <ErrorBoundary>
    <div className="space-y-6">
      {/* Filters */}
      <Card>
        <div className="flex flex-wrap items-end gap-3">
          <div className="min-w-[180px]">
            <Select
              label="Route Group"
              value={pending.route_group_id}
              onChange={(e) => handleGroupChange(e.target.value)}
            >
              <option value="">Select group…</option>
              {groupsQuery.data?.map((g) => (
                <option key={g.id} value={g.id}>
                  {g.name}
                </option>
              ))}
            </Select>
          </div>

          <div className="min-w-[120px]">
            <Select
              label="Origin"
              value={pending.origin}
              onChange={(e) =>
                setPending((f) => ({ ...f, origin: e.target.value }))
              }
              disabled={!selectedGroup}
            >
              <option value="">All origins</option>
              {selectedGroup?.origins.map((o) => (
                <option key={o} value={o}>
                  {o}
                </option>
              ))}
            </Select>
          </div>

          <DateRangeInput
            dateFrom={pending.date_from}
            dateTo={pending.date_to}
            onDateFromChange={(v) =>
              setPending((f) => ({ ...f, date_from: v }))
            }
            onDateToChange={(v) => setPending((f) => ({ ...f, date_to: v }))}
          />

          <Button
            variant="primary"
            onClick={handleApply}
            disabled={!pending.route_group_id}
          >
            Apply
          </Button>
        </div>
      </Card>

      {/* No group selected */}
      {!applied.route_group_id && (
        <div className="flex flex-col items-center gap-3 rounded-xl border border-dashed border-slate-200 p-16 text-center text-slate-400">
          <Search className="h-10 w-10 text-slate-300" />
          <p className="text-sm font-medium text-slate-500">Select a route group to explore its price data</p>
          <p className="text-xs">Choose a group above and click Apply to load prices.</p>
        </div>
      )}

      {/* Chart */}
      {applied.route_group_id && (
        <Card>
          <h3 className="mb-4 text-sm font-semibold text-slate-700">
            Price Trend
            {trendOrigin && trendDest && (
              <span className="ml-2 font-mono text-xs font-normal text-slate-400">
                {trendOrigin} → {trendDest}
              </span>
            )}
          </h3>
          <PriceChart data={trendQuery.data ?? []} />
        </Card>
      )}

      {/* Price Table */}
      {applied.route_group_id && (
        <Card>
          <div className="mb-3 flex flex-wrap items-center justify-between gap-3">
            <h3 className="text-sm font-semibold text-slate-700">Price Data</h3>
            <div className="flex flex-wrap items-center gap-2">
              {/* Airline filter */}
              {airlines.length > 0 && (
                <select
                  aria-label="Filter by airline"
                  value={airlineFilter}
                  onChange={(e) => setAirlineFilter(e.target.value)}
                  className="rounded-lg border border-slate-300 bg-white px-2 py-1 text-sm focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
                >
                  <option value="">All airlines</option>
                  {airlines.map((a) => (
                    <option key={a} value={a}>{a}</option>
                  ))}
                </select>
              )}
              {/* Price range */}
              <input
                type="number"
                aria-label="Min price"
                placeholder="Min $"
                value={minPrice}
                onChange={(e) => setMinPrice(e.target.value)}
                className="w-20 rounded-lg border border-slate-300 bg-white px-2 py-1 text-sm focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
              />
              <input
                type="number"
                aria-label="Max price"
                placeholder="Max $"
                value={maxPrice}
                onChange={(e) => setMaxPrice(e.target.value)}
                className="w-20 rounded-lg border border-slate-300 bg-white px-2 py-1 text-sm focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
              />
              {/* Row count */}
              {filteredPrices.length > 0 && (
                <span className="text-xs text-slate-400">
                  {filteredPrices.length} row{filteredPrices.length !== 1 ? "s" : ""}{hasMore && !airlineFilter && !minPrice && !maxPrice ? "+" : ""}
                </span>
              )}
              {/* CSV export */}
              {filteredPrices.length > 0 && (
                <Button
                  variant="secondary"
                  onClick={() => exportCsv(filteredPrices)}
                >
                  <Download className="h-3.5 w-3.5" aria-hidden="true" />
                  Download CSV
                </Button>
              )}
            </div>
          </div>
          <PriceTable
            prices={filteredPrices}
            isLoading={pricesLoading && allPrices.length === 0}
            hasMore={hasMore && !airlineFilter && !minPrice && !maxPrice}
            onLoadMore={handleLoadMore}
            loadingMore={pricesLoading && allPrices.length > 0}
            groupCurrency={appliedGroup?.currency}
          />
        </Card>
      )}
    </div>
    </ErrorBoundary>
  );
}
