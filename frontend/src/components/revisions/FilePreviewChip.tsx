import { File, X } from "lucide-react";
import { Button } from "@/components/ui/button";

interface FilePreviewChipProps {
  file: { file_key: string; file_name: string };
  onRemove: () => void;
  onPreview?: () => void;
}

export function FilePreviewChip({ file, onRemove, onPreview }: FilePreviewChipProps) {
  return (
    <div className="group inline-flex items-center gap-1.5 rounded-full border border-border bg-secondary px-3 py-1 text-xs text-foreground max-w-[200px] hover:bg-accent transition-colors">
      <button
        type="button"
        className="flex items-center gap-1.5 min-w-0 cursor-pointer"
        onClick={onPreview}
        title={file.file_name}
      >
        <File className="h-3.5 w-3.5 shrink-0" />
        <span className="truncate">{file.file_name}</span>
      </button>
      <Button
        type="button"
        variant="ghost"
        size="icon"
        className="h-4 w-4 p-0 opacity-0 group-hover:opacity-100 transition-opacity text-muted-foreground hover:text-foreground shrink-0"
        onClick={onRemove}
        aria-label={`Remove ${file.file_name}`}
      >
        <X className="h-3 w-3" />
      </Button>
    </div>
  );
}
