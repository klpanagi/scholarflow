import { useState } from "react"
import { Bot, Puzzle, MessageSquare } from "lucide-react"
import AgentsPage from "./AgentsPage"
import SkillsPage from "./SkillsPage"
import ChatPage from "./ChatPage"

const TABS = [
  { id: "agents" as const, label: "Agents", icon: Bot },
  { id: "skills" as const, label: "Skills", icon: Puzzle },
  { id: "chat" as const, label: "Chat", icon: MessageSquare },
]

type TabId = (typeof TABS)[number]["id"]

export default function CultPage() {
  const [activeTab, setActiveTab] = useState<TabId>("agents")

  const isChat = activeTab === "chat"

  return (
    <div className="flex flex-col" style={{ height: "calc(100vh - 8rem)" }}>
      <div className="flex gap-1 border-b border-border/60 shrink-0 px-1">
        {TABS.map((tab) => {
          const Icon = tab.icon
          const isActive = activeTab === tab.id
          return (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`
                relative flex items-center gap-2 px-5 py-3 text-sm font-medium
                transition-colors rounded-t-lg
                ${
                  isActive
                    ? "text-primary bg-background"
                    : "text-muted-foreground hover:text-foreground hover:bg-muted/50"
                }
              `}
            >
              <Icon className="h-4 w-4" />
              {tab.label}
              {isActive && (
                <span className="absolute bottom-0 left-2 right-2 h-0.5 bg-primary rounded-full" />
              )}
            </button>
          )
        })}
      </div>

      <div
        className={`flex-1 overflow-hidden ${isChat ? "-mx-4 md:-mx-8 -mb-8" : "mt-6"}`}
      >
        {activeTab === "agents" && <AgentsPage />}
        {activeTab === "skills" && <SkillsPage />}
        {activeTab === "chat" && <ChatPage />}
      </div>
    </div>
  )
}
