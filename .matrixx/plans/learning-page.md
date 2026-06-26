# Learning Page — ScholarFlow Platform Guide

## TL;DR

> **Quick Summary**: Build a Learning section in the frontend that educates non-expert users on every aspect of ScholarFlow — assets, the Cult, agent roles, strategies, skills, and configurations — through an index page of 6 cards linking to dedicated detail pages with animated diagrams and interactive content.
> 
> **Deliverables**:
> - `frontend/src/content/learning.ts` — typed content data file (single source of truth)
> - `frontend/src/pages/LearningPage.tsx` — index page with 6 topic cards
> - `frontend/src/pages/learning/AssetsPage.tsx` — Assets deep dive
> - `frontend/src/pages/learning/CultPage.tsx` — The Cult explained
> - `frontend/src/pages/learning/RolesPage.tsx` — Agent Roles guide
> - `frontend/src/pages/learning/StrategiesPage.tsx` — Agent Strategies guide
> - `frontend/src/pages/learning/SkillsPage.tsx` — Default Skills guide
> - `frontend/src/pages/learning/ConfigsPage.tsx` — Agent Configurations guide
> - Sidebar integration (add "Learning" to Overview group)
> - Route integration (App.tsx)
> - TDD tests for data file and components
> 
> **Estimated Effort**: Medium (4-6 hours)
> **Parallel Execution**: YES — 3 waves
> **Critical Path**: Data file → Index page + Detail pages (parallel) → Route + Sidebar → Tests

---

## Context

### Original Request
User wants a "Learning" page explaining every aspect of the ScholarFlow platform for non-expert users: what assets are, what the Cult is, agent roles, agent strategies, default skills, and default agent configurations. The goal is to help users understand the value and easily start working with the platform's concepts and features.

### Interview Summary
**Key Discussions**:
- **Page Location**: Authenticated, inside AppShell, dedicated routes (not modals)
- **Content Structure**: 6 cards on index, each linking to a dedicated detail page
- **Content Source**: Typed TypeScript data file (`frontend/src/content/learning.ts`)
- **Visual Polish**: Animated flowcharts (Framer Motion SVG), interactive elements
- **Terminology**: Replace "Assignments" with clearer term ("Workflow Stages")
- **Counts**: Use CULT_SYSTEM.md as authoritative (9 roles, 10 agents, 4 strategies, 10 skills, 14 configs)

**Research Findings**:
- 8 themes via `data-theme` attribute, tokens: Gold primary, Navy backgrounds
- `motion.ts` provides `pageVariants`, `cardVariants`, `fadeInUp`, `staggerContainer`, `useReducedMotion`, `withReducedMotion`
- `AppShell` wraps all authenticated routes with sidebar + topbar
- Pages use `PageHeader`, `Card`, `EmptyState`, `LoadingState` components
- Sidebar has 5 nav groups: Overview, Research, Intelligence, Productivity, Settings
- Dashboard pattern: `animate-in fade-in duration-500` wrapper, section headers with icon + gradient line

### Seraph Review
**Identified Gaps** (addressed):
- Content maintenance: Data file approach prevents rot
- `prefers-reduced-motion`: Must honor in all animations
- a11y: Focus trap for mobile sheet, screen reader support, axe-core compliance
- Counts: Use CULT_SYSTEM.md numbers as authoritative
- Asset pipeline: Verified GROBID is primary (PyMuPDF fallback)

---

## Work Objectives

### Core Objective
Create a Learning section that serves as the platform's educational hub, enabling non-expert users to understand and confidently use ScholarFlow's core concepts.

### Concrete Deliverables
- 1 content data file with typed schema
- 1 index page (6 cards in responsive grid)
- 6 detail pages with animated diagrams and interactive content
- Sidebar navigation item
- Route configuration
- TDD tests

### Definition of Done
- [x] All 7 pages render correctly at `/learning` and `/learning/[slug]`
- [x] Sidebar shows "Learning" in Overview group, highlighted when active
- [x] All animations respect `prefers-reduced-motion: reduce`
- [x] All pages pass axe-core with zero violations
- [x] `pnpm build` succeeds with no errors
- [x] All vitest tests pass

### Must Have
- 6 topic cards with icon, title, description, difficulty badge, reading time
- Dedicated route per topic (not modals)
- Animated flowcharts using Framer Motion SVG
- Interactive expandable sections in detail pages
- `prefers-reduced-motion` support
- Responsive design (mobile → desktop)
- Content in typed TypeScript data file

### Must NOT Have (Guardrails)
- No modals for card expansion (use routes)
- No code examples or screenshots in content
- No new npm dependencies (Framer Motion is already installed)
- No backend changes
- No analytics or telemetry
- No custom SVG icons (use Lucide)
- No generic diagram engine (hardcode 6 specific SVG diagrams)
- No multi-step tour system (walkthrough = ordered stages array)
- No progress tracking or reading state
- No glossary or FAQ sub-pages
- No search within Learning section
- No print/export functionality
- No Learning-specific theme tokens
- Cards frozen at 6 for v1

---

## Verification Strategy

> **UNIVERSAL RULE: ZERO HUMAN INTERVENTION**
>
> ALL tasks in this plan MUST be verifiable WITHOUT any human action.

### Test Decision
- **Infrastructure exists**: YES (vitest configured in `frontend/vitest.config.ts`)
- **Automated tests**: YES (TDD — RED-GREEN-REFACTOR per task)
- **Framework**: vitest + jsdom + React Testing Library

### Agent-Executed QA Scenarios

**Verification Tool by Deliverable Type:**

| Type | Tool | How Agent Verifies |
|------|------|-------------------|
| **Frontend/UI** | Playwright (playwright skill) | Navigate, interact, assert DOM, screenshot |
| **Library/Module** | Bash (bun/node REPL) | Import, call functions, compare output |
| **Config/Infra** | Bash (shell commands) | Apply config, run state checks, validate |

**Each Scenario WILL Follow This Format:**

```
Scenario: [Descriptive name — what user action/flow is being verified]
  Tool: [Playwright / interactive_bash / Bash]
  Preconditions: [What must be true before this scenario runs]
  Steps:
    1. [Exact action with specific selector/command/endpoint]
    2. [Next action with expected intermediate state]
    3. [Assertion with exact expected value]
  Expected Result: [Concrete, observable outcome]
  Failure Indicators: [What would indicate failure]
  Evidence: [Screenshot path / output capture / response body path]
```

---

## Execution Strategy

### Parallel Execution Waves

```
Wave 1 (Start Immediately):
├── Task 1: Content data file (foundation — no dependencies)
└── Task 2: Vitest test setup for Learning section (foundation)

Wave 2 (After Wave 1):
├── Task 3: LearningPage.tsx (index with 6 cards) [depends: 1, 2]
├── Task 4: AssetsPage.tsx (detail page) [depends: 1, 2]
├── Task 5: CultPage.tsx (detail page) [depends: 1, 2]
├── Task 6: RolesPage.tsx (detail page) [depends: 1, 2]
├── Task 7: StrategiesPage.tsx (detail page) [depends: 1, 2]
├── Task 8: SkillsPage.tsx (detail page) [depends: 1, 2]
└── Task 9: ConfigsPage.tsx (detail page) [depends: 1, 2]

Wave 3 (After Wave 2):
├── Task 10: Route integration (App.tsx) [depends: 3-9]
├── Task 11: Sidebar integration [depends: 3-9]
└── Task 12: Build verification + final QA [depends: 10, 11]

Critical Path: Task 1 → Task 3 → Task 10 → Task 12
Parallel Speedup: ~60% faster than sequential (7 pages built in parallel)
```

### Dependency Matrix

| Task | Depends On | Blocks | Can Parallelize With |
|------|------------|--------|---------------------|
| 1 | None | 3-9 | 2 |
| 2 | None | 3-9 | 1 |
| 3 | 1, 2 | 10, 11 | 4-9 |
| 4 | 1, 2 | 10 | 3, 5-9 |
| 5 | 1, 2 | 10 | 3, 4, 6-9 |
| 6 | 1, 2 | 10 | 3-5, 7-9 |
| 7 | 1, 2 | 10 | 3-6, 8-9 |
| 8 | 1, 2 | 10 | 3-7, 9 |
| 9 | 1, 2 | 10 | 3-8 |
| 10 | 3-9 | 12 | 11 |
| 11 | 3-9 | 12 | 10 |
| 12 | 10, 11 | None | None (final) |

### Agent Dispatch Summary

| Wave | Tasks | Recommended Agents |
|------|-------|-------------------|
| 1 | 1, 2 | task(category="source", load_skills=["frontend-state-data", "frontend-build-tooling"]) |
| 2 | 3-9 | task(category="construct", load_skills=["frontend-ui-ux"]) × 7 parallel |
| 3 | 10, 11, 12 | task(category="bullet-time", load_skills=["frontend-ui-ux"]) × 3 parallel |

---

## TODOs

---

### Task 1: Create Content Data File

**What to do**:
- Create `frontend/src/content/learning.ts` with typed schema
- Define `LearningSection` interface with fields: `id`, `slug`, `title`, `description`, `icon` (Lucide icon name), `difficulty`, `readingMinutes`, `sections` (array of content blocks)
- Define content block types: `text`, `diagram`, `list`, `callout`
- Populate all 6 sections with content:
  1. Assets (Beginner, 5 min) — upload pipeline: PDF → MinIO → GROBID → chunking → Elasticsearch → LLM analysis
  2. The Cult (Beginner, 4 min) — frontend namespace /cult, skills system, workflow stages
  3. Agent Roles (Intermediate, 7 min) — 10 agents across 9 roles, how they differ from runtime
  4. Agent Strategies (Advanced, 6 min) — 4 strategies (Direct, Critique, Reflection, EvaluatorOptimizer)
  5. Default Skills (Intermediate, 5 min) — 10 seed skills, how to use them
  6. Agent Configurations (Intermediate, 5 min) — 14 seeded+default configs, how to customize
- Export `learningSections` array and `LearningSection` type
- Add Zod schema for runtime validation (prevents silent typos like "Intermidiate")

**Must NOT do**:
- No JSX or React components in this file
- No API calls
- No hardcoded "X min read" — calculate from word count

**Recommended Agent Profile**:
- **Category**: `source`
  - Reason: Logic-heavy data modeling, TypeScript types, Zod schema
- **Skills**: [`frontend-state-data`]
  - `frontend-state-data`: Zod validation, typed data structures

**Parallelization**:
- **Can Run In Parallel**: YES
- **Parallel Group**: Wave 1 (with Task 2)
- **Blocks**: Tasks 3-9
- **Blocked By**: None (can start immediately)

**References**:

**Pattern References**:
- `frontend/src/lib/motion.ts` — Animation presets to reference in diagram definitions
- `frontend/src/pages/DashboardPage.tsx` — Page structure pattern to match

**API/Type References**:
- `frontend/src/components/shared/PageHeader.tsx` — Reusable page header component
- `frontend/src/components/shared/EmptyState.tsx` — Empty state component pattern

**Documentation References**:
- `backend/seeds/scholarflow_skills.py` — Authoritative source for 10 seed skill names and descriptions
- `backend/app/agents/registry.py` — Authoritative source for 9 agent roles and 10 agents
- `backend/app/agents/strategies/__init__.py` — Authoritative source for 4 strategies

**External References**:
- Lucide icons: `https://lucide.dev/icons/` — Icon names for the `icon` field

**WHY Each Reference Matters**:
- `scholarflow_skills.py` contains the exact names and descriptions of the 10 seed skills — content must match
- `registry.py` contains the exact role enum values and agent class names — content must match
- `strategies/__init__.py` contains the exact strategy names — content must match
- `motion.ts` provides the animation variants that diagram components will use
- `DashboardPage.tsx` shows the card grid + section header pattern to replicate

**Acceptance Criteria**:

**If TDD (tests enabled):**
- [x] Test file created: `frontend/src/content/__tests__/learning.test.ts`
- [x] Test covers: schema validation (Zod), exactly 6 entries, each has required fields
- [x] Test covers: difficulties restricted to {Beginner, Intermediate, Advanced}
- [x] Test covers: readingMinutes is positive integer
- [x] Test covers: slugs are unique and URL-safe
- [x] `pnpm vitest run frontend/src/content/__tests__/learning.test.ts` → PASS

**Agent-Executed QA Scenarios:**

```
Scenario: Data file exports correct structure
  Tool: Bash (Node.js REPL)
  Preconditions: File created at frontend/src/content/learning.ts
  Steps:
    1. Run: cd frontend && npx tsx -e "import { learningSections } from './src/content/learning'; console.log(JSON.stringify(learningSections.map(s => ({ id: s.id, slug: s.slug, title: s.title, difficulty: s.difficulty })), null, 2))"
    2. Assert: output contains exactly 6 entries
    3. Assert: each entry has id, slug, title, difficulty
    4. Assert: difficulties are "Beginner", "Intermediate", or "Advanced"
    5. Assert: slugs are "assets", "cult", "roles", "strategies", "skills", "configs"
  Expected Result: 6 valid learning sections exported
  Evidence: Terminal output captured

Scenario: Zod schema rejects invalid data
  Tool: Bash (Node.js REPL)
  Preconditions: Zod schema defined in learning.ts
  Steps:
    1. Run: cd frontend && npx tsx -e "import { learningSectionSchema } from './src/content/learning'; const result = learningSectionSchema.safeParse({ id: 'test', difficulty: 'Intermidiate' }); console.log(result.success, result.error?.issues)"
    2. Assert: result.success is false
    3. Assert: error message mentions invalid enum value
  Expected Result: Zod catches typo in difficulty
  Evidence: Terminal output captured

Scenario: Reading time calculated from word count
  Tool: Bash (Node.js REPL)
  Preconditions: learningSections exported with readingMinutes field
  Steps:
    1. Run: cd frontend && npx tsx -e "import { learningSections } from './src/content/learning'; learningSections.forEach(s => { const wordCount = s.sections.reduce((acc, b) => acc + (b.type === 'text' ? b.content.split(/\s+/).length : 0), 0); const expected = Math.max(1, Math.ceil(wordCount / 200)); console.log(s.slug, wordCount, 'words', s.readingMinutes, 'min', expected, 'expected', s.readingMinutes === expected ? 'OK' : 'MISMATCH') }"
    2. Assert: all 6 sections show "OK" (readingMinutes matches word count / 200)
  Expected Result: Reading times are calculated, not hardcoded
  Evidence: Terminal output captured
```

**Commit**: YES
- Message: `feat(learning): add typed content data file with Zod schema`
- Files: `frontend/src/content/learning.ts`, `frontend/src/content/__tests__/learning.test.ts`
- Pre-commit: `pnpm vitest run frontend/src/content/__tests__/learning.test.ts`

---

### Task 2: Vitest Test Setup for Learning Section

**What to do**:
- Create test directory structure: `frontend/src/pages/__tests__/learning/`
- Create test helpers: `frontend/src/__test-utils__/learning-test-helpers.tsx`
  - Render wrapper with QueryClientProvider, MemoryRouter, ThemeProvider
  - Mock data factory for learning sections
- Verify vitest config supports the new test paths
- Create one smoke test to confirm test infrastructure works

**Must NOT do**:
- No production code changes
- No new dependencies

**Recommended Agent Profile**:
- **Category**: `bullet-time`
  - Reason: Small, focused setup task
- **Skills**: [`frontend-testing`]
  - `frontend-testing`: Vitest configuration, test utilities

**Parallelization**:
- **Can Run In Parallel**: YES
- **Parallel Group**: Wave 1 (with Task 1)
- **Blocks**: Tasks 3-9
- **Blocked By**: None (can start immediately)

**References**:

**Pattern References**:
- `frontend/vitest.config.ts` — Existing vitest configuration
- `frontend/src/__test-utils__/` — Existing test utilities (if any)

**API/Type References**:
- `frontend/src/components/theme/ThemeProvider.tsx` — Theme provider for test wrapper
- `frontend/src/main.tsx` — App providers layout to replicate in test wrapper

**WHY Each Reference Matters**:
- `vitest.config.ts` shows the existing test setup (jsdom, environment, thresholds)
- `ThemeProvider.tsx` is needed in test wrapper to prevent theme-related errors
- `main.tsx` shows the provider hierarchy to replicate

**Acceptance Criteria**:

**If TDD (tests enabled):**
- [x] Test file created: `frontend/src/__test-utils__/learning-test-helpers.tsx`
- [x] Test file created: `frontend/src/pages/__tests__/learning/smoke.test.tsx`
- [x] Test covers: render LearningPage with test wrapper → no errors
- [x] `pnpm vitest run frontend/src/pages/__tests__/learning/smoke.test.ts` → PASS

**Agent-Executed QA Scenarios:**

```
Scenario: Test infrastructure works
  Tool: Bash
  Preconditions: vitest configured, test helpers created
  Steps:
    1. Run: cd frontend && pnpm vitest run frontend/src/pages/__tests__/learning/smoke.test.tsx
    2. Assert: exit code 0
    3. Assert: output contains "1 passed"
  Expected Result: Smoke test passes
  Evidence: Terminal output captured

Scenario: vitest config supports new paths
  Tool: Bash
  Preconditions: vitest.config.ts exists
  Steps:
    1. Run: cd frontend && pnpm vitest run --reporter=verbose 2>&1 | head -20
    2. Assert: vitest starts without errors
    3. Assert: test files are discovered
  Expected Result: vitest recognizes test files
  Evidence: Terminal output captured
```

**Commit**: YES (groups with Task 1)
- Message: `feat(learning): add test infrastructure and smoke test`
- Files: `frontend/src/__test-utils__/learning-test-helpers.tsx`, `frontend/src/pages/__tests__/learning/smoke.test.tsx`
- Pre-commit: `pnpm vitest run frontend/src/pages/__tests__/learning/`

---

### Task 3: LearningPage.tsx — Index Page with 6 Cards

**What to do**:
- Create `frontend/src/pages/LearningPage.tsx`
- Import `learningSections` from content data file
- Render `PageHeader` with title "Learning", description, icon (GraduationCap from lucide-react)
- Render responsive grid: `grid-cols-1 md:grid-cols-2 lg:grid-cols-3`
- Each card uses shadcn `Card`, `CardHeader`, `CardContent`, `CardTitle`
- Card content: Lucide icon, title, description, difficulty badge (shadcn Badge), reading time
- Cards link to `/learning/{slug}` via React Router `Link`
- Wrap grid in `motion.div` with `staggerContainer` and each card with `motion.div` + `cardVariants`
- Add `prefers-reduced-motion` support via `useReducedMotion` + `withReducedMotion`
- Add preview diagram placeholder (small SVG teaser per card)
- Add CTA text "Read more →" at bottom of each card

**Must NOT do**:
- No modals
- No new shadcn components
- No backend calls
- No search functionality

**Recommended Agent Profile**:
- **Category**: `construct`
  - Reason: Frontend UI component with animations and design system integration
- **Skills**: [`frontend-ui-ux`]
  - `frontend-ui-ux`: Card layouts, animation patterns, responsive design

**Parallelization**:
- **Can Run In Parallel**: YES
- **Parallel Group**: Wave 2 (with Tasks 4-9)
- **Blocks**: Tasks 10, 11
- **Blocked By**: Tasks 1, 2

**References**:

**Pattern References**:
- `frontend/src/pages/DashboardPage.tsx` — Card grid layout, section headers, animation wrapper
- `frontend/src/components/shared/PageHeader.tsx` — PageHeader component API
- `frontend/src/components/shared/EmptyState.tsx` — Empty state pattern (if no sections)

**API/Type References**:
- `frontend/src/content/learning.ts:learningSections` — Content data to render
- `frontend/src/content/learning.ts:LearningSection` — Type for each section
- `frontend/src/lib/motion.ts:cardVariants` — Card entrance animation
- `frontend/src/lib/motion.ts:staggerContainer` — Staggered grid animation
- `frontend/src/lib/motion.ts:useReducedMotion` — Reduced motion hook
- `frontend/src/lib/motion.ts:withReducedMotion` — Animation selector

**External References**:
- Lucide icons: `GraduationCap`, `BookOpen`, `Sparkles`, `Users`, `Swords`, `ScrollText`, `Settings2`
- shadcn/ui Card: `https://ui.shadcn.com/docs/components/card`
- shadcn/ui Badge: `https://ui.shadcn.com/docs/components/badge`

**WHY Each Reference Matters**:
- `DashboardPage.tsx` is the closest existing pattern — card grid with animations
- `motion.ts` provides all animation variants needed for staggered card entrance
- `learningSections` is the data source — must match the type exactly
- Lucide icons must be pre-selected to avoid "pick icon" churn mid-build

**Acceptance Criteria**:

**If TDD (tests enabled):**
- [x] Test file created: `frontend/src/pages/__tests__/learning/LearningPage.test.tsx`
- [x] Test covers: renders 6 cards with correct titles
- [x] Test covers: each card has difficulty badge
- [x] Test covers: each card has reading time
- [x] Test covers: cards link to correct routes
- [x] Test covers: grid responsive classes present
- [x] `pnpm vitest run frontend/src/pages/__tests__/learning/LearningPage.test.tsx` → PASS

**Agent-Executed QA Scenarios:**

```
Scenario: Learning page renders 6 cards
  Tool: Playwright (playwright skill)
  Preconditions: Dev server running on localhost:3000, user authenticated
  Steps:
    1. Navigate to: http://localhost:3000/learning
    2. Wait for: [data-testid="learning-page"] visible (timeout: 5s)
    3. Assert: 6 card elements render with role="article"
    4. Assert: first card contains "Assets" text
    5. Assert: last card contains "Agent Configurations" text
    6. Assert: each card has a Badge element with difficulty text
    7. Screenshot: .matrixx/evidence/task-3-learning-index.png
  Expected Result: 6 cards render in responsive grid
  Evidence: .matrixx/evidence/task-3-learning-index.png

Scenario: Cards link to correct detail pages
  Tool: Playwright (playwright skill)
  Preconditions: Dev server running, Learning page loaded
  Steps:
    1. Click: first card's "Read more" link
    2. Wait for: navigation to /learning/assets (timeout: 5s)
    3. Assert: URL is /learning/assets
    4. Assert: page contains "Assets" heading
    5. Navigate back to /learning
    6. Click: second card's "Read more" link
    7. Assert: URL is /learning/cult
  Expected Result: Cards navigate to correct detail pages
  Evidence: .matrixx/evidence/task-3-card-navigation.png

Scenario: Reduced motion disables animations
  Tool: Playwright (playwright skill)
  Preconditions: Dev server running, browser with prefers-reduced-motion: reduce
  Steps:
    1. Set viewport with reduced motion preference
    2. Navigate to: http://localhost:3000/learning
    3. Wait for: cards visible (timeout: 5s)
    4. Assert: cards render without animation transitions (duration: 0)
    5. Screenshot: .matrixx/evidence/task-3-reduced-motion.png
  Expected Result: Cards render instantly without animation
  Evidence: .matrixx/evidence/task-3-reduced-motion.png
```

**Commit**: YES
- Message: `feat(learning): add LearningPage with 6 topic cards`
- Files: `frontend/src/pages/LearningPage.tsx`, `frontend/src/pages/__tests__/learning/LearningPage.test.tsx`
- Pre-commit: `pnpm vitest run frontend/src/pages/__tests__/learning/LearningPage.test.tsx`

---

### Tasks 4-9: Detail Pages (Assets, Cult, Roles, Strategies, Skills, Configs)

> These 6 tasks are structurally identical — each creates a detail page for one learning topic.
> They run in PARALLEL in Wave 2.

**What to do** (per page):
- Create `frontend/src/pages/learning/{Slug}Page.tsx`
- Import specific section from `learningSections` data file
- Render `PageHeader` with section title, description, icon
- Render content blocks from the section's `sections` array
- For `text` blocks: render as paragraphs with proper typography
- For `diagram` blocks: render animated SVG flowchart using Framer Motion
  - Each diagram is a hand-authored SVG (not a generic engine)
  - Use `motion.path`, `motion.circle`, `motion.rect` for animated elements
  - Animate path drawing with `pathLength` and `strokeDasharray`
  - Honor `prefers-reduced-motion` via `withReducedMotion`
- For `list` blocks: render as styled `<ul>` with icons
- For `callout` blocks: render as shadcn Alert or custom callout component
- Add interactive expandable sections using controlled state + CSS transitions
- Add breadcrumb navigation: Learning > [Section Title]
- Add "Back to Learning" link at bottom
- Add "Open [Feature]" CTA linking to the actual feature page (e.g., /cult/agents)

**Must NOT do**:
- No generic diagram engine
- No multi-step tour system
- No progress tracking
- No backend calls
- No code examples or screenshots

**Recommended Agent Profile** (for each):
- **Category**: `construct`
  - Reason: Frontend UI with animations, SVG diagrams, interactive elements
- **Skills**: [`frontend-ui-ux`]
  - `frontend-ui-ux`: SVG animation, interactive patterns, accessibility

**Parallelization**:
- **Can Run In Parallel**: YES
- **Parallel Group**: Wave 2 (all 6 in parallel)
- **Blocks**: Tasks 10, 11
- **Blocked By**: Tasks 1, 2

**References** (shared across all 6):

**Pattern References**:
- `frontend/src/pages/DashboardPage.tsx` — Page structure, section headers, animation wrapper
- `frontend/src/pages/LearningPage.tsx` (Task 3) — Index page pattern to link back to
- `frontend/src/components/shared/PageHeader.tsx` — PageHeader component API
- `frontend/src/lib/motion.ts` — All animation variants (pageVariants, fadeInUp, withReducedMotion)

**API/Type References**:
- `frontend/src/content/learning.ts:learningSections` — Content data (each page reads its section by slug)
- `frontend/src/content/learning.ts:ContentBlock` — Type for content blocks (text, diagram, list, callout)

**External References**:
- Framer Motion SVG: `https://www.framer.com/motion/animation/#svg-animation` — pathLength animation
- shadcn/ui Alert: `https://ui.shadcn.com/docs/components/alert` — callout blocks
- Lucide icons: `https://lucide.dev/icons/` — icons for list items and diagrams

**WHY Each Reference Matters**:
- `motion.ts` provides `pageVariants`, `fadeInUp`, `withReducedMotion` — all detail pages use these
- `learningSections` is the data source — each page filters by slug
- Framer Motion SVG docs explain `pathLength` animation for flowcharts
- shadcn Alert is the closest existing component for callout blocks

**Acceptance Criteria** (per page):

**If TDD (tests enabled):**
- [x] Test file created: `frontend/src/pages/__tests__/learning/{Slug}Page.test.tsx`
- [x] Test covers: renders page header with correct title
- [x] Test covers: renders content blocks from data file
- [x] Test covers: breadcrumb navigation present
- [x] Test covers: "Back to Learning" link present
- [x] Test covers: "Open [Feature]" CTA links to correct route
- [x] `pnpm vitest run frontend/src/pages/__tests__/learning/{Slug}Page.test.tsx` → PASS

**Agent-Executed QA Scenarios** (per page):

```
Scenario: Detail page renders content from data file
  Tool: Playwright (playwright skill)
  Preconditions: Dev server running, user authenticated
  Steps:
    1. Navigate to: http://localhost:3000/learning/{slug}
    2. Wait for: page heading visible (timeout: 5s)
    3. Assert: heading text matches section title from data file
    4. Assert: breadcrumb shows "Learning > {Section Title}"
    5. Assert: content sections render with correct text
    6. Assert: "Back to Learning" link present at bottom
    7. Assert: "Open [Feature]" CTA links to correct route
    8. Screenshot: .matrixx/evidence/task-{N}-{slug}-detail.png
  Expected Result: Detail page renders all content blocks
  Evidence: .matrixx/evidence/task-{N}-{slug}-detail.png

Scenario: Animated diagram renders with Framer Motion
  Tool: Playwright (playwright skill)
  Preconditions: Dev server running, detail page with diagram block loaded
  Steps:
    1. Navigate to: http://localhost:3000/learning/{slug}
    2. Wait for: SVG diagram visible (timeout: 5s)
    3. Assert: SVG elements have motion attributes (data-framer, style)
    4. Assert: path elements have stroke-dasharray animation
    5. Screenshot: .matrixx/evidence/task-{N}-{slug}-diagram.png
  Expected Result: Diagram animates on load
  Evidence: .matrixx/evidence/task-{N}-{slug}-diagram.png

Scenario: Expandable sections work
  Tool: Playwright (playwright skill)
  Preconditions: Dev server running, detail page with expandable sections
  Steps:
    1. Navigate to: http://localhost:3000/learning/{slug}
    2. Find: expandable section trigger button
    3. Click: expandable section trigger
    4. Wait for: expanded content visible (timeout: 3s)
    5. Assert: expanded content contains expected text
    6. Click: expandable section trigger again
    7. Wait for: expanded content hidden (timeout: 3s)
    8. Assert: expanded content is not visible
  Expected Result: Expandable sections toggle correctly
  Evidence: .matrixx/evidence/task-{N}-{slug}-expandable.png
```

**Commit**: YES (one commit per page, or batch)
- Message: `feat(learning): add {SectionName} detail page`
- Files: `frontend/src/pages/learning/{Slug}Page.tsx`, `frontend/src/pages/__tests__/learning/{Slug}Page.test.tsx`
- Pre-commit: `pnpm vitest run frontend/src/pages/__tests__/learning/{Slug}Page.test.tsx`

---

### Task 10: Route Integration (App.tsx)

**What to do**:
- Add lazy import for `LearningPage`: `const LearningPage = lazy(() => import('./pages/LearningPage'))`
- Add lazy imports for 6 detail pages: `const AssetsLearningPage = lazy(() => import('./pages/learning/AssetsPage'))`, etc.
- Add route structure inside `<Routes>`:
  ```tsx
  <Route path="learning" element={<AppShell />}>
    <Route index element={<ProtectedRoute><LearningPage /></ProtectedRoute>} />
    <Route path="assets" element={<ProtectedRoute><AssetsLearningPage /></ProtectedRoute>} />
    <Route path="cult" element={<ProtectedRoute><CultLearningPage /></ProtectedRoute>} />
    <Route path="roles" element={<ProtectedRoute><RolesLearningPage /></ProtectedRoute>} />
    <Route path="strategies" element={<ProtectedRoute><StrategiesLearningPage /></ProtectedRoute>} />
    <Route path="skills" element={<ProtectedRoute><SkillsLearningPage /></ProtectedRoute>} />
    <Route path="configs" element={<ProtectedRoute><ConfigsLearningPage /></ProtectedRoute>} />
  </Route>
  ```
- Verify route structure matches existing patterns (e.g., `/cult` nested routes)

**Must NOT do**:
- No changes to existing routes
- No new route guards
- No backend changes

**Recommended Agent Profile**:
- **Category**: `bullet-time`
  - Reason: Small, focused file edit
- **Skills**: [`frontend-ui-ux`]
  - `frontend-ui-ux`: React Router patterns

**Parallelization**:
- **Can Run In Parallel**: YES
- **Parallel Group**: Wave 3 (with Tasks 11, 12)
- **Blocks**: Task 12
- **Blocked By**: Tasks 3-9

**References**:

**Pattern References**:
- `frontend/src/App.tsx` — Existing route structure, lazy loading pattern, ProtectedRoute usage
- `frontend/src/App.tsx:44-62` — Cult nested route pattern to replicate

**API/Type References**:
- `frontend/src/components/auth/ProtectedRoute.tsx` — Auth guard component
- `frontend/src/components/layout/AppShell.tsx` — Shell wrapper for authenticated routes

**WHY Each Reference Matters**:
- `App.tsx` is the file to edit — must match existing patterns exactly
- The `/cult` nested route pattern is the closest analog to the new `/learning` routes
- `ProtectedRoute` is required for auth — must wrap each route element

**Acceptance Criteria**:

**If TDD (tests enabled):**
- [x] No new test file needed (route integration verified by build + E2E)
- [x] `pnpm build` succeeds with no TypeScript errors

**Agent-Executed QA Scenarios:**

```
Scenario: /learning route loads LearningPage
  Tool: Playwright (playwright skill)
  Preconditions: Dev server running, user authenticated
  Steps:
    1. Navigate to: http://localhost:3000/learning
    2. Wait for: page heading "Learning" visible (timeout: 5s)
    3. Assert: URL is /learning
    4. Assert: 6 cards render
    5. Screenshot: .matrixx/evidence/task-10-learning-route.png
  Expected Result: /learning route loads correctly
  Evidence: .matrixx/evidence/task-10-learning-route.png

Scenario: /learning/assets route loads detail page
  Tool: Playwright (playwright skill)
  Preconditions: Dev server running, user authenticated
  Steps:
    1. Navigate to: http://localhost:3000/learning/assets
    2. Wait for: "Assets" heading visible (timeout: 5s)
    3. Assert: URL is /learning/assets
    4. Assert: breadcrumb shows "Learning > Assets"
    5. Screenshot: .matrixx/evidence/task-10-assets-route.png
  Expected Result: /learning/assets route loads correctly
  Evidence: .matrixx/evidence/task-10-assets-route.png

Scenario: Unauthenticated access redirects to login
  Tool: Playwright (playwright skill)
  Preconditions: Dev server running, user NOT authenticated
  Steps:
    1. Clear localStorage (logout)
    2. Navigate to: http://localhost:3000/learning
    3. Wait for: redirect to /login (timeout: 5s)
    4. Assert: URL is /login
    5. Screenshot: .matrixx/evidence/task-10-auth-redirect.png
  Expected Result: Unauthenticated users redirected to login
  Evidence: .matrixx/evidence/task-10-auth-redirect.png
```

**Commit**: YES
- Message: `feat(learning): add routes for Learning section`
- Files: `frontend/src/App.tsx`
- Pre-commit: `pnpm build`

---

### Task 11: Sidebar Integration

**What to do**:
- Import `GraduationCap` from `lucide-react` in `Sidebar.tsx`
- Add `SidebarNavItem` to the "Overview" group, after Dashboard:
  ```tsx
  <SidebarNavItem to="/learning" label="Learning" icon={GraduationCap} end />
  ```
- Verify the Overview group now has 2 items: Dashboard, Learning

**Must NOT do**:
- No changes to other nav groups
- No new nav groups
- No sidebar restructure

**Recommended Agent Profile**:
- **Category**: `bullet-time`
  - Reason: Single line addition
- **Skills**: [`frontend-ui-ux`]
  - `frontend-ui-ux`: Sidebar patterns

**Parallelization**:
- **Can Run In Parallel**: YES
- **Parallel Group**: Wave 3 (with Tasks 10, 12)
- **Blocks**: Task 12
- **Blocked By**: Tasks 3-9

**References**:

**Pattern References**:
- `frontend/src/components/layout/Sidebar.tsx:37-42` — Overview group to edit
- `frontend/src/components/layout/SidebarNavItem.tsx` — NavItem component API

**WHY Each Reference Matters**:
- `Sidebar.tsx:37-42` is the exact location to add the new nav item
- `SidebarNavItem.tsx` shows the `to`, `label`, `icon`, `end` props

**Acceptance Criteria**:

**If TDD (tests enabled):**
- [x] No new test file needed (sidebar change is trivial)
- [x] `pnpm build` succeeds

**Agent-Executed QA Scenarios:**

```
Scenario: Sidebar shows Learning in Overview group
  Tool: Playwright (playwright skill)
  Preconditions: Dev server running, user authenticated
  Steps:
    1. Navigate to: http://localhost:3000/dashboard
    2. Wait for: sidebar visible (timeout: 5s)
    3. Assert: "Overview" group contains "Dashboard" and "Learning" items
    4. Assert: "Learning" item is second in the group
    5. Click: "Learning" sidebar item
    6. Assert: navigation to /learning
    7. Assert: "Learning" item has aria-current="page"
    8. Screenshot: .matrixx/evidence/task-11-sidebar-learning.png
  Expected Result: Learning appears in sidebar and navigates correctly
  Evidence: .matrixx/evidence/task-11-sidebar-learning.png

Scenario: Learning item highlights when active
  Tool: Playwright (playwright skill)
  Preconditions: Dev server running, user authenticated
  Steps:
    1. Navigate to: http://localhost:3000/learning/assets
    2. Wait for: sidebar visible (timeout: 5s)
    3. Assert: "Learning" sidebar item has aria-current="page" or active class
    4. Screenshot: .matrixx/evidence/task-11-sidebar-active.png
  Expected Result: Learning item highlights on detail pages too
  Evidence: .matrixx/evidence/task-11-sidebar-active.png
```

**Commit**: YES (groups with Task 10)
- Message: `feat(learning): add Learning to sidebar navigation`
- Files: `frontend/src/components/layout/Sidebar.tsx`
- Pre-commit: `pnpm build`

---

### Task 12: Build Verification + Final QA

**What to do**:
- Run `pnpm build` — verify no TypeScript errors, no build failures
- Run `pnpm vitest run` — verify all tests pass
- Run full Playwright E2E verification:
  - All 7 routes load correctly
  - Sidebar navigation works
  - Cards link to detail pages
  - Breadcrumbs work
  - Back links work
  - CTAs link to correct feature pages
  - Animations respect reduced motion
  - axe-core passes on all pages
- Verify bundle size: Learning chunk < 50KB gzipped
- Create evidence screenshots for all pages

**Must NOT do**:
- No code changes (verification only)
- No new features

**Recommended Agent Profile**:
- **Category**: `bullet-time`
  - Reason: Verification task, no code changes
- **Skills**: [`frontend-ui-ux`, `quality-gate`]
  - `frontend-ui-ux`: Final visual verification
  - `quality-gate`: Build, lint, typecheck verification

**Parallelization**:
- **Can Run In Parallel**: NO
- **Parallel Group**: Wave 3 (sequential after Tasks 10, 11)
- **Blocks**: None (final task)
- **Blocked By**: Tasks 10, 11

**References**:

**Pattern References**:
- `frontend/package.json` — Build and test scripts
- `frontend/vitest.config.ts` — Test thresholds

**WHY Each Reference Matters**:
- `package.json` shows the build command and scripts
- `vitest.config.ts` shows coverage thresholds to verify

**Acceptance Criteria**:

**Agent-Executed QA Scenarios:**

```
Scenario: Build succeeds with no errors
  Tool: Bash
  Preconditions: All code changes complete
  Steps:
    1. Run: cd frontend && pnpm build
    2. Assert: exit code 0
    3. Assert: output contains "✓ built in"
    4. Assert: no TypeScript errors in output
    5. Assert: LearningPage chunk generated in dist/assets/
  Expected Result: Build completes successfully
  Evidence: Terminal output captured

Scenario: All tests pass
  Tool: Bash
  Preconditions: All test files created
  Steps:
    1. Run: cd frontend && pnpm vitest run
    2. Assert: exit code 0
    3. Assert: output contains "Tests" with 0 failures
    4. Assert: all learning test files pass
  Expected Result: All tests pass
  Evidence: Terminal output captured

Scenario: All 7 Learning routes render
  Tool: Playwright (playwright skill)
  Preconditions: Dev server running, user authenticated
  Steps:
    1. Navigate to: http://localhost:3000/learning → assert 6 cards
    2. Navigate to: http://localhost:3000/learning/assets → assert Assets heading
    3. Navigate to: http://localhost:3000/learning/cult → assert Cult heading
    4. Navigate to: http://localhost:3000/learning/roles → assert Roles heading
    5. Navigate to: http://localhost:3000/learning/strategies → assert Strategies heading
    6. Navigate to: http://localhost:3000/learning/skills → assert Skills heading
    7. Navigate to: http://localhost:3000/learning/configs → assert Configs heading
    8. Screenshot each page to .matrixx/evidence/task-12-{slug}.png
  Expected Result: All 7 routes render correctly
  Evidence: 7 screenshots in .matrixx/evidence/

Scenario: axe-core passes on all pages
  Tool: Playwright (playwright skill)
  Preconditions: Dev server running, user authenticated
  Steps:
    1. Navigate to: http://localhost:3000/learning
    2. Run: @axe-core/playwright analysis
    3. Assert: violations array is empty
    4. Repeat for each detail page
  Expected Result: Zero axe-core violations on all Learning pages
  Evidence: .matrixx/evidence/task-12-axe-core-results.json
```

**Commit**: NO (verification only)

---

## Commit Strategy

| After Task | Message | Files | Verification |
|------------|---------|-------|--------------|
| 1+2 | `feat(learning): add content data file and test infrastructure` | learning.ts, test helpers, smoke test | vitest run |
| 3 | `feat(learning): add LearningPage with 6 topic cards` | LearningPage.tsx, test | vitest run |
| 4-9 | `feat(learning): add {Section} detail page` | {Slug}Page.tsx, test | vitest run |
| 10+11 | `feat(learning): add routes and sidebar navigation` | App.tsx, Sidebar.tsx | pnpm build |
| 12 | (no commit — verification only) | — | pnpm build + vitest run |

---

## Success Criteria

### Verification Commands
```bash
cd frontend && pnpm build          # Expected: ✓ built in, no errors
cd frontend && pnpm vitest run      # Expected: all tests pass, 0 failures
```

### Final Checklist
- [x] All "Must Have" present
- [x] All "Must NOT Have" absent
- [x] All tests pass
- [x] Build succeeds
- [x] All 7 routes render correctly
- [x] Sidebar shows Learning in Overview group
- [x] Animations respect prefers-reduced-motion
- [x] axe-core passes on all pages
- [x] Content matches CULT_SYSTEM.md numbers
- [x] Reading times are calculated, not hardcoded
