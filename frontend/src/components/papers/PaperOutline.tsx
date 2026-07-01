import { useState } from "react"
import { cn } from "@/lib/utils"
import { ChevronRight, ChevronDown } from "lucide-react"

interface ExtractionSection {
  heading?: string
  text?: string
}

interface PaperOutlineProps {
  sections: ExtractionSection[]
  className?: string
}

export function PaperOutline({ sections, className }: PaperOutlineProps) {
  const [activeSection, setActiveSection] = useState<number | null>(null)

  if (!sections || sections.length === 0) {
    return (
      <div className="flex items-center justify-center py-16 text-sm text-muted-foreground">
        No sections available for this document.
      </div>
    )
  }

  return (
    <div className={cn("flex flex-col gap-6 lg:flex-row", className)}>
      {/* Section headings sidebar */}
      <nav className="lg:w-72 shrink-0">
        <h3 className="mb-2 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
          Document Outline ({sections.length} sections)
        </h3>
        <div className="max-h-[65vh] overflow-y-auto rounded-lg border border-border/40 bg-muted/30">
          {sections.map((s, i) => {
            const label = s.heading || `Section ${i + 1}`
            const isActive = activeSection === i
            return (
              <button
                key={i}
                onClick={() => setActiveSection(i)}
                className={cn(
                  "flex w-full items-center gap-2 px-3 py-2 text-left text-xs transition-colors",
                  "hover:bg-accent/40 border-b border-border/20 last:border-0",
                  isActive && "bg-accent/60 font-medium text-accent-foreground",
                )}
              >
                {isActive ? (
                  <ChevronDown className="h-3 w-3 shrink-0 text-primary" />
                ) : (
                  <ChevronRight className="h-3 w-3 shrink-0 text-muted-foreground" />
                )}
                <span className="truncate">{label}</span>
                <span className="ml-auto shrink-0 text-[10px] tabular-nums text-muted-foreground/60">
                  {i + 1}
                </span>
              </button>
            )
          })}
        </div>
      </nav>

      {/* Section content */}
      <div className="min-w-0 flex-1">
        {activeSection !== null ? (
          <div className="space-y-3">
            <h2 className="text-lg font-semibold leading-snug">
              {sections[activeSection].heading || `Section ${activeSection + 1}`}
            </h2>
            <p className="whitespace-pre-wrap text-sm leading-relaxed text-muted-foreground">
              {sections[activeSection].text || "(No content)"}
            </p>
          </div>
        ) : (
          <div className="flex items-center justify-center py-16 text-sm text-muted-foreground">
            Select a section from the outline to view its content.
          </div>
        )}
      </div>
    </div>
  )
}
