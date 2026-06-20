import { Quote, ExternalLink } from "lucide-react";
import { Badge } from "@/components/ui/badge";

interface CitationChipProps {
  source: {
    file_name: string;
    file_key: string;
    page?: number;
    section?: string;
  };
}

const MINIO_URL = import.meta.env.VITE_MINIO_URL || "http://localhost:9000";
const BUCKET = "assets";

export function CitationChip({ source }: CitationChipProps) {
  const href = `${MINIO_URL}/${BUCKET}/${source.file_key}`;

  return (
    <a
      href={href}
      target="_blank"
      rel="noopener noreferrer"
      className="inline-flex items-center gap-1.5 rounded-full border border-border bg-secondary px-3 py-1 text-xs text-foreground max-w-[200px] hover:bg-accent hover:text-accent-foreground transition-colors no-underline"
    >
      <Quote className="h-3.5 w-3.5 shrink-0" />
      <span className="truncate">{source.file_name}</span>
      {(source.page || source.section) && (
        <Badge variant="outline" className="text-[10px] px-1.5 py-0 leading-none h-4 shrink-0">
          {source.section || `p. ${source.page}`}
        </Badge>
      )}
      <ExternalLink className="h-3 w-3 shrink-0 text-muted-foreground" />
    </a>
  );
}
