import { useMemo, useState } from "react";
import type { DailyPrice } from "../types/price";
import { formatRelativeTime } from "../utils/format";
import { Button } from "./ui/Button";
import { Skeleton } from "./ui/Skeleton";

interface Column {
  key: keyof DailyPrice;
  label: string;
  align?: "left" | "right";
}

const COLUMNS: Column[] = [
  { key: "depart_date", label: "Date" },
  { key: "origin", label: "Origin" },
  { key: "destination", label: "Destination" },
  { key: "airline", label: "Airline" },
  { key: "stops", label: "Stops" },
  { key: "duration_minutes", label: "Duration" },
  { key: "price", label: "Price", align: "right" },
  { key: "provider", label: "Provider" },
  { key: "scraped_at", label: "Scraped At" },
];

interface PriceTableProps {
  prices: DailyPrice[];
  isLoading: boolean;
  hasMore?: boolean;
  onLoadMore?: () => void;
  loadingMore?: boolean;
  groupCurrency?: string;
}

export function PriceTable({ prices, isLoading, hasMore, onLoadMore, loadingMore, groupCurrency }: PriceTableProps) {
  const [sortKey, setSortKey] = useState<keyof DailyPrice>("depart_date");
  const [sortDir, setSortDir] = useState<"asc" | "desc">("asc");

  function toggleSort(key: keyof DailyPrice) {
    if (sortKey === key) {
      setSortDir((d) => (d === "asc" ? "desc" : "asc"));
    } else {
      setSortKey(key);
      setSortDir("asc");
    }
  }

  const sorted = useMemo(() => {
    return [...prices].sort((a, b) => {
      const av = a[sortKey];
      const bv = b[sortKey];
      if (av == null) return 1;
      if (bv == null) return -1;
      const cmp = av < bv ? -1 : av > bv ? 1 : 0;
      return sortDir === "asc" ? cmp : -cmp;
    });
  }, [prices, sortKey, sortDir]);

  if (isLoading) return <Skeleton className="h-64 rounded-xl" />;

  if (!prices.length) {
    return (
      <p className="py-10 text-center text-sm text-slate-400">
        No prices found. Run a collection to populate data.
      </p>
    );
  }

  return (
    <>
    <div className="overflow-x-auto">
      <table className="w-full text-left text-sm">
        <thead>
          <tr className="border-b border-slate-200 text-xs uppercase tracking-wider text-slate-500">
            {COLUMNS.map((col) => (
              <th
                key={col.key}
                className={`cursor-pointer select-none px-3 py-2.5 hover:text-slate-700 ${
                  col.align === "right" ? "text-right" : ""
                }`}
                onClick={() => toggleSort(col.key)}
              >
                {col.label}{" "}
                {sortKey === col.key ? (sortDir === "asc" ? "↑" : "↓") : ""}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {sorted.map((price, i) => (
            <tr
              key={price.id}
              className={`transition-colors hover:bg-brand-50/40 ${i % 2 !== 0 ? "bg-slate-50/50" : ""}`}
            >
              <td className="px-3 py-2 text-slate-700">{price.depart_date}</td>
              <td className="px-3 py-2 font-medium text-slate-800">
                {price.origin}
              </td>
              <td className="px-3 py-2 text-slate-700">{price.destination}</td>
              <td className="px-3 py-2 text-slate-700">{price.airline}</td>
              <td className="px-3 py-2 text-slate-700">
                {price.stops == null
                  ? "—"
                  : price.stops === 0
                    ? <span className="text-green-600 font-medium">Direct</span>
                    : `${price.stops} stop${price.stops > 1 ? "s" : ""}`}
              </td>
              <td className="px-3 py-2 text-slate-700">
                {price.duration_minutes == null
                  ? "—"
                  : `${Math.floor(price.duration_minutes / 60)}h ${price.duration_minutes % 60}m`}
              </td>
              <td className="px-3 py-2 text-right font-medium text-slate-900">
                {Math.round(price.price).toLocaleString()}{" "}
                <span className="text-xs text-slate-400">{groupCurrency ?? price.currency}</span>
              </td>
              <td className="px-3 py-2 text-slate-500 capitalize">
                {price.provider}
              </td>
              <td className="px-3 py-2 text-slate-400">
                {formatRelativeTime(price.scraped_at)}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
    {hasMore && (
      <div className="mt-3 flex justify-center">
        <Button variant="secondary" onClick={onLoadMore} loading={loadingMore}>
          Load more
        </Button>
      </div>
    )}
  </>
  );
}


