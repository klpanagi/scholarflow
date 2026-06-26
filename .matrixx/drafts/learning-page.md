# Draft: Learning Page

## Requirements (confirmed)
- Build a "Learning" page explaining every aspect of the scholarflow platform
- 6 major sections: Assets, The Cult (skills/assignments), Agent Roles, Agent Strategies, Default Skills, Default Agent Configs
- Focus: non-experts should understand the value and easily start working

## Technical Decisions
- **Page Access**: Authenticated (inside AppShell)
- **Section Layout**: Card grid - overview cards that expand to show detailed content
- **Card Expansion**: Modal overlay - clicking a card opens a modal with detailed content
- **Sidebar Nav**: Add to "Overview" group (alongside Dashboard)
- **Content Depth**: Concise overview - 1-2 paragraphs + visual diagram per section
- **Visual Polish**: Rich & interactive - animated diagrams, interactive flowcharts, code examples with syntax highlighting, mini-demos

## Card Grid Design
- Each card shows: icon, title, 1-sentence description, preview diagram, difficulty badge (Beginner/Intermediate/Advanced), estimated reading time
- Cards expand to modal overlay on click
- 6 cards total, one per topic

## Modal Content Design
- Animated flowchart showing how components connect
- Interactive elements: expandable sections, toggles, step-by-step walkthroughs
- No code examples or screenshots (per user preference)

## Section Organization
1. **Assets** (Beginner) - What are assets, how they're uploaded, processed, and used
2. **The Cult** (Beginner) - Frontend namespace, skills, assignments, how they connect
3. **Agent Roles** (Intermediate) - 9 agents, their roles, how they differ from agent runtime
4. **Agent Strategies** (Advanced) - 4 strategies, when to use each, how they work
5. **Default Skills** (Intermediate) - 8 seed skills, how to use them
6. **Agent Configurations** (Intermediate) - Default configs, how to customize them

## Research Findings
- Frontend: React 19, React Router v6, AppShell layout, shadcn/ui, 8 themes
- 9 agents, 4 strategies, 8 seed skills
- Assets: uploaded PDFs → MinIO → GROBID → chunking → Elasticsearch → LLM analysis
- "The Cult" = frontend route namespace /cult for Intelligence section
- Skills = reusable prompt templates with tool bindings
- Assignments = stage-to-agent-config mapping for workflow execution

## Test Strategy Decision
- **Infrastructure exists**: YES (vitest + @testing-library/react + @testing-library/jest-dom)
- **Automated tests**: YES (TDD)
- **Framework**: vitest
- **Agent-Executed QA**: ALWAYS (mandatory for all tasks regardless of test choice)

## Final Design Summary
- **Page**: `/learning` (authenticated, inside AppShell)
- **Sidebar**: Added to "Overview" group (alongside Dashboard)
- **Layout**: 6 cards in a responsive grid (1-2-3 columns)
- **Cards**: Lucide icon + title + 1-sentence description + preview diagram + difficulty badge + reading time
- **Expansion**: Dedicated routes (/learning/assets, /learning/cult, etc.) - NOT modals
- **Difficulty**: Mixed (Beginner: Assets, Cult; Intermediate: Agent Roles, Skills, Configs; Advanced: Strategies)
- **Icons**: Lucide icons (consistent with existing design)
- **Tests**: TDD with vitest
- **Content**: Concise 1-2 paragraphs per section + animated diagrams
- **Content Source**: Typed TypeScript data file (frontend/src/content/learning.ts)
- **Terminology**: Replace "Assignments" with clearer term (likely "Workflows" or "Stages")

## Seraph Findings Addressed
- **Content source**: Data file approach (not hardcoded JSX) for maintainability
- **Modal → Route switch**: Better a11y, deep linking, mobile UX, sharing
- **Counts reconciliation**: Use CULT_SYSTEM.md as authoritative (9 roles, 10 agents, 4 strategies, 10 skills, 14 configs)
- **"Assignments" → clearer term**: Replace with "Workflows" or "Stages"
- **Asset pipeline**: Verify actual pipeline before drawing diagrams (GROBID vs Tika)
- **prefers-reduced-motion**: Must honor in all animations
- **a11y**: Focus trap, screen reader support, axe-core compliance

## Scope Boundaries
- INCLUDE: Learning page with 6 cards linking to dedicated routes
- INCLUDE: Add "Learning" to sidebar Overview group
- INCLUDE: TDD approach with vitest
- INCLUDE: Lucide icons for cards
- INCLUDE: Typed TypeScript data file for content
- INCLUDE: Dedicated routes for each section (/learning/assets, etc.)
- EXCLUDE: Modal overlays for card expansion
- EXCLUDE: Code examples or screenshots in content
- EXCLUDE: Public access (authenticated only)
- EXCLUDE: Custom SVG icons
- EXCLUDE: New sidebar group (using existing Overview group)
- EXCLUDE: Backend changes
- EXCLUDE: Analytics/telemetry
