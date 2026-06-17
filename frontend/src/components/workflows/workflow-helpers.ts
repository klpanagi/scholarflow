import {
  CheckCircle,
  XCircle,
  Loader2,
  AlertTriangle,
  MinusCircle,
} from "lucide-react";

/* ── duration formatting ────────────────────────────── */

export function formatDuration(seconds?: number): string {
  if (!seconds) return "--";
  if (seconds < 60) return `${seconds.toFixed(1)}s`;
  const m = Math.floor(seconds / 60);
  const s = Math.round(seconds % 60);
  return `${m}m ${s}s`;
}

/* ── per-stage status icon + style config ───────────── */

interface StageStatusConfig {
  icon: React.ElementType;
  iconClass: string;
  badgeClass: string;
  label: string;
}

const stageStatusMap: Record<string, StageStatusConfig> = {
  completed: {
    icon: CheckCircle,
    iconClass: "text-emerald-500",
    badgeClass:
      "bg-emerald-100 text-emerald-700 dark:bg-emerald-900/40 dark:text-emerald-400 border-emerald-200 dark:border-emerald-800",
    label: "Done",
  },
  running: {
    icon: Loader2,
    iconClass: "text-blue-500 animate-spin",
    badgeClass:
      "bg-blue-100 text-blue-700 dark:bg-blue-900/40 dark:text-blue-400 border-blue-200 dark:border-blue-800",
    label: "Running",
  },
  in_progress: {
    icon: Loader2,
    iconClass: "text-blue-500 animate-spin",
    badgeClass:
      "bg-blue-100 text-blue-700 dark:bg-blue-900/40 dark:text-blue-400 border-blue-200 dark:border-blue-800",
    label: "Running",
  },
  failed: {
    icon: XCircle,
    iconClass: "text-red-500",
    badgeClass:
      "bg-red-100 text-red-700 dark:bg-red-900/40 dark:text-red-400 border-red-200 dark:border-red-800",
    label: "Failed",
  },
  error: {
    icon: XCircle,
    iconClass: "text-red-500",
    badgeClass:
      "bg-red-100 text-red-700 dark:bg-red-900/40 dark:text-red-400 border-red-200 dark:border-red-800",
    label: "Failed",
  },
  timeout: {
    icon: AlertTriangle,
    iconClass: "text-amber-500",
    badgeClass:
      "bg-amber-100 text-amber-700 dark:bg-amber-900/40 dark:text-amber-400 border-amber-200 dark:border-amber-800",
    label: "Timeout",
  },
  skipped: {
    icon: MinusCircle,
    iconClass: "text-gray-400 dark:text-gray-500",
    badgeClass: "bg-muted text-muted-foreground border-border",
    label: "Skipped",
  },
};

export function getStatusConfig(status: string): StageStatusConfig {
  return stageStatusMap[status] || stageStatusMap.skipped;
}

/* ── execution-level status badge ───────────────────── */

export const executionStatusStyles: Record<string, string> = {
  completed:
    "bg-emerald-100 text-emerald-700 dark:bg-emerald-900/40 dark:text-emerald-400 border-emerald-200 dark:border-emerald-800",
  partial:
    "bg-amber-100 text-amber-700 dark:bg-amber-900/40 dark:text-amber-400 border-amber-200 dark:border-amber-800",
  failed:
    "bg-red-100 text-red-700 dark:bg-red-900/40 dark:text-red-400 border-red-200 dark:border-red-800",
};
