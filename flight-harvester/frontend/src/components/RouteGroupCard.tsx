import { useQuery, useQueryClient } from "@tanstack/react-query";
import {
  AlertTriangle,
  Ban,
  Download,
  ExternalLink,
  KeyRound,
  Play,
  RefreshCw,
} from "lucide-react";
import { useState } from "react";
import { Link } from "react-router-dom";
import {
  downloadExport,
  getRouteGroupProgress,
  saveBlobAsFile,
} from "../api/route-groups";
import { triggerGroupCollection } from "../api/collection";
import { getErrorMessage } from "../api/client";
import type {
  RouteGroup,
  RouteGroupProgress,
  ScrapeHealthStatus,
} from "../types/route-group";
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
  const qc = useQueryClient();
  const [downloading, setDownloading] = useState(false);
  const [triggering, setTriggering] = useState(false);
  const [refreshing, setRefreshing] = useState(false);

  const progressQuery = useQuery({
    queryKey: ["route-group-progress", group.id],
    queryFn: () => getRouteGroupProgress(group.id),
    refetchInterval: 30_000,
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
      showToast("Collection started — progress will update shortly", "success");
      // Refresh progress right after triggering so the user sees movement
      await qc.invalidateQueries({
        queryKey: ["route-group-progress", group.id],
      });
    } catch (err) {
      showToast(getErrorMessage(err, "Failed to trigger collection"), "error");
    } finally {
      setTriggering(false);
    }
  }

  async function handleRefresh() {
    setRefreshing(true);
    try {
      await progressQuery.refetch();
    } finally {
      setRefreshing(false);
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

      {/* Health banner (quota / auth / error) */}
      {progress && <HealthBanner progress={progress} />}

      {/* Progress */}
      {progressQuery.isLoading ? (
        <div className="space-y-2">
          <Skeleton className="h-2 w-full" />
          <Skeleton className="h-4 w-1/2" />
        </div>
      ) : progress ? (
        <div className="space-y-1.5">
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
            {progress.last_scraped_at ? (
              <span title={new Date(progress.last_scraped_at).toLocaleString()}>
                updated {formatRelativeTime(progress.last_scraped_at)}
              </span>
            ) : (
              <span className="text-slate-400">not started yet</span>
            )}
          </div>
        </div>
      ) : (
        <div className="space-y-1.5">
          <span className="inline-flex items-center rounded-full bg-amber-100 px-2 py-0.5 text-xs font-medium text-amber-700">
            Never scraped — click Start to begin
          </span>
          <ProgressBar value={0} max={1} />
        </div>
      )}

      {/* Actions */}
      <div className="flex flex-wrap gap-2 pt-1">
        <Button
          variant="primary"
          onClick={handleTrigger}
          loading={triggering}
          className="flex-1"
          title="Start or resume collection for this route group"
        >
          <Play className="h-4 w-4" />
          {progress && progress.dates_with_data > 0 ? "Resume collection" : "Start collection"}
        </Button>
        <Button
          variant="secondary"
          onClick={handleRefresh}
          loading={refreshing}
          title="Refresh progress now"
          aria-label="Refresh progress"
        >
          <RefreshCw className="h-4 w-4" />
        </Button>
        <Button
          variant="secondary"
          onClick={handleDownload}
          loading={downloading}
          title="Download collected data as Excel"
        >
          <Download className="h-4 w-4" />
          Excel
        </Button>
      </div>
    </Card>
  );
}

// ── Health banner ────────────────────────────────────────────────────────────

interface HealthBannerProps {
  progress: RouteGroupProgress;
}

function HealthBanner({ progress }: HealthBannerProps) {
  const { status, last_error_message, errors_last_hour, last_attempt_at } =
    progress.health;

  if (status === "ok") return null;
  if (status === "never_scraped" && progress.dates_with_data === 0) return null;

  const style = bannerStyles(status);
  const Icon = style.icon;

  return (
    <div
      className={`flex items-start gap-2 rounded-lg border px-3 py-2 text-xs ${style.classes}`}
      role="status"
    >
      <Icon className="mt-0.5 h-4 w-4 shrink-0" />
      <div className="min-w-0 flex-1">
        <p className="font-medium">{style.title}</p>
        {style.description && (
          <p className="mt-0.5 opacity-90">{style.description}</p>
        )}
        {last_error_message && (
          <p className="mt-0.5 truncate opacity-80" title={last_error_message}>
            {last_error_message}
          </p>
        )}
        {last_attempt_at && (
          <p className="mt-0.5 text-[10px] opacity-70">
            {errors_last_hour} errors in last hour · last attempt{" "}
            {formatRelativeTime(last_attempt_at)}
          </p>
        )}
      </div>
    </div>
  );
}

function bannerStyles(status: ScrapeHealthStatus): {
  title: string;
  description?: string;
  icon: typeof AlertTriangle;
  classes: string;
} {
  switch (status) {
    case "quota_exhausted":
      return {
        title: "Flight API quota exhausted",
        description:
          "The SerpAPI plan has run out of searches for this billing period. Upgrade the plan or wait for renewal.",
        icon: Ban,
        classes: "border-rose-200 bg-rose-50 text-rose-800",
      };
    case "auth_error":
      return {
        title: "Flight API key is invalid",
        description:
          "Check that SERPAPI_KEY is set correctly on the backend (Render → Environment).",
        icon: KeyRound,
        classes: "border-rose-200 bg-rose-50 text-rose-800",
      };
    case "rate_limited":
      return {
        title: "Temporarily rate-limited",
        description: "Provider is throttling requests. Collection will resume automatically.",
        icon: AlertTriangle,
        classes: "border-amber-200 bg-amber-50 text-amber-800",
      };
    case "error":
      return {
        title: "Recent scrape errors",
        icon: AlertTriangle,
        classes: "border-amber-200 bg-amber-50 text-amber-800",
      };
    case "never_scraped":
    default:
      return {
        title: "Not started yet",
        icon: AlertTriangle,
        classes: "border-slate-200 bg-slate-50 text-slate-700",
      };
  }
}
