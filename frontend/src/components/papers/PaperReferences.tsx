import { BookMarked, ExternalLink } from "lucide-react"

interface ExtractionReference {
  raw_text?: string
  title?: string
  authors?: string
  year?: string | number
  doi?: string
}

interface PaperReferencesProps {
  references: ExtractionReference[]
}

export function PaperReferences({ references }: PaperReferencesProps) {
  if (!references || references.length === 0) {
    return (
      <div className="flex items-center justify-center py-16 text-sm text-muted-foreground">
        No references extracted from this document.
      </div>
    )
  }

  return (
    <div className="space-y-3">
      <h3 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
        References ({references.length})
      </h3>
      <div className="space-y-2">
        {references.map((ref, i) => (
          <div
            key={i}
            className="group rounded-lg border border-border/40 bg-card/30 p-3 transition-colors hover:bg-accent/20"
          >
            <div className="flex items-start gap-3">
              <span className="mt-0.5 shrink-0 text-xs tabular-nums text-muted-foreground/50">
                [{i + 1}]
              </span>
              <div className="min-w-0 flex-1 space-y-1">
                {ref.title && (
                  <p className="text-sm font-medium leading-snug text-foreground">{ref.title}</p>
                )}
                {ref.authors && (
                  <p className="text-xs text-muted-foreground">{ref.authors}</p>
                )}
                <div className="flex flex-wrap items-center gap-2 text-[11px] text-muted-foreground/70">
                  {ref.year && <span>{ref.year}</span>}
                  {ref.doi && (
                    <a
                      href={`https://doi.org/${ref.doi}`}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="inline-flex items-center gap-1 text-primary hover:underline"
                    >
                      <ExternalLink className="h-3 w-3" />
                      DOI
                    </a>
                  )}
                </div>
                {!ref.title && ref.raw_text && (
                  <p className="text-xs italic text-muted-foreground/60">{ref.raw_text.slice(0, 200)}</p>
                )}
              </div>
              <BookMarked className="mt-1 h-3.5 w-3.5 shrink-0 text-muted-foreground/30" />
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
