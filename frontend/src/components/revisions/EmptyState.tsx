import { Sparkles, ArrowRight } from "lucide-react"
import { Button } from "@/components/ui/button"

interface EmptyStateProps {
  onSendPrompt?: (text: string) => void
}

const SUGGESTED_PROMPTS = [
  "What are the main strengths?",
  "Where are the methodology gaps?",
  "How can I improve the related work section?",
  "Summarize the recommendation",
] as const

export function EmptyState({ onSendPrompt }: EmptyStateProps) {
  return (
    <div className="flex items-center justify-center min-h-[50vh]">
      <div className="flex flex-col items-center text-center max-w-[600px] py-16 gap-6">
        <div className="h-16 w-16 rounded-full bg-primary/10 flex items-center justify-center">
          <Sparkles className="h-8 w-8 text-primary" />
        </div>

        <div className="space-y-2">
          <h2 className="font-semibold text-xl">Start discussing the review</h2>
          <p className="text-muted-foreground text-sm">
            Ask questions, request changes, or explore the methodology and findings.
          </p>
        </div>

        <div className="grid grid-cols-2 gap-3 w-full">
          {SUGGESTED_PROMPTS.map((prompt) => (
            <Button
              key={prompt}
              variant="outline"
              className="w-full justify-start text-left h-auto py-3 px-4"
              onClick={onSendPrompt ? () => onSendPrompt(prompt) : undefined}
            >
              <span className="flex-1 text-sm">{prompt}</span>
              <ArrowRight className="h-4 w-4 ml-2 shrink-0 text-muted-foreground" />
            </Button>
          ))}
        </div>
      </div>
    </div>
  )
}
