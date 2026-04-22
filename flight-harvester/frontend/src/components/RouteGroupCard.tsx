import { useQuery } from "@tanstack/react-query";
import { Download, ExternalLink, RefreshCw } from "lucide-react";
import { useState } from "react";
import { Link } from "react-router-dom";
import {
  downloadExport,
  getRouteGroupProgress,
  saveBlobAsFile,
} from "../api/route-groups";
import { triggerGroupCollection } from "../api/collection";
import { getErrorMessage } from "../api/client";
import type { RouteGroup } from "../types/route-group";
import { formatRelativeTime, formatNumber } from "../utils/format";
import { useToast } from "../context/ToastContext";
import { Button } from "./ui/Button";
import { Card } from "./ui/Card";
import { ProgressBar } from "./ui/ProgressBar";
import { Skeleton } from "./ui/Skeleton";

interface RouteGroupCardProps {
  group: RouteGroup;
}

export function RouteGroupCard({ group }: RouteGroupCardProps) {
  const { showToast } = useToast();
  const [downloading, setDownloading] = useState(false);
  const [triggering, setTriggering] = useState(false);

  const progressQuery = useQuery({
    queryKey: ["route-group-progress", group.id],
    queryFn: () => getRouteGroupProgress(group.id),
    refetchInterval: 60_000,
  });

  const progress = progressQuery.data;

  async function handleDownload() {
    setDownloading(true);
    try {
      const blob = await downloadExport(group.id);
      const safeName = group.name.replace(/[^a-z0-9_-]/gi, "_");
      saveBlobAsFile(blob, `${safeName}.xlsx`);
      showToast("Excel downloaded", "success");
    } catch (err) {
      showToast(getErrorMessage(err, "Download failed"), "error");
    } finally {
      setDownloading(false);
    }
  }

  async function handleTrigger() {
    setTriggering(true);
    try {
      await triggerGroupCollection(group.id);
      showToast("Collection triggered", "success");
    } catch (err) {
      showToast(getErrorMessage(err, "Failed to trigger collection"), "error");
    } finally {
      setTriggering(false);
    }
  }

  return (
    <Card className="flex flex-col gap-4 transition-shadow duration-200 hover:shadow-md">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <Link
            to={`/route-groups/${group.id}`}
            className="flex items-center gap-1 font-semibold text-slate-900 hover:text-brand-700"
          >
            {group.name}
            <ExternalLink className="h-3.5 w-3.5 text-slate-400" />
          </Link>
          <p className="mt-0.5 text-sm text-slate-500">
            {group.destination_label}
          </p>
        </div>
        <span
          className={`mt-1.5 inline-flex h-2 w-2 rounded-full ${
            group.is_active ? "bg-green-500" : "bg-slate-300"
          }`}
          title={group.is_active ? "Active" : "Inactive"}
        />
      </div>

      {/* Meta */}
      <div className="flex gap-4 text-sm text-slate-600">
        <span>{group.origins.length} origins</span>
        <span>{group.nights} nights</span>
        <span>{group.days_ahead} days ahead</span>
      </div>

      {/* Progress */}
      {progressQuery.isLoading ? (
        <div className="space-y-2">
          <Skeleton className="h-2 w-full" />
          <Skeleton className="h-4 w-1/2" />
        </div>
      ) : progress ? (
        <div className="space-y-1.5">
          {progress.dates_with_data === 0 && (
            <span className="inline-flex items-center rounded-full bg-amber-100 px-2 py-0.5 text-xs font-medium text-amber-700">
              Never scraped — trigger collection to start
            </span>
          )}
          <ProgressBar
            value={progress.dates_with_data}
            max={progress.total_dates}
          />
          <div className="flex justify-between text-xs text-slate-500">
            <span>
              {formatNumber(progress.dates_with_data)}/
              {formatNumber(progress.total_dates)} dates (
              {progress.coverage_percent.toFixed(1)}%)
            </span>
            {progress.last_scraped_at && (
              <span>{formatRelativeTime(progress.last_scraped_at)}</span>
            )}
          </div>
        </div>
      ) : (
        <div className="space-y-1.5">
          <span className="inline-flex items-center rounded-full bg-amber-100 px-2 py-0.5 text-xs font-medium text-amber-700">
            Never scraped — trigger collection to start
          </span>
          <ProgressBar value={0} max={1} />
        </div>
      )}

      {/* Actions */}
      <div className="flex gap-2 pt-1">
        <Button
          variant="primary"
          onClick={handleDownload}
          loading={downloading}
          className="flex-1"
        >
          <Download className="h-4 w-4" />
          Download Excel
        </Button>
        <Button
          variant="secondary"
          onClick={handleTrigger}
          loading={triggering}
          title="Trigger collection for this group"
        >
          <RefreshCw className="h-4 w-4" />
        </Button>
      </div>
    </Card>
  );
}
