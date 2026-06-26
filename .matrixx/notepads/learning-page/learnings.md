# Learning Page — Learnings

## Wave 1, Task 2 — Test infrastructure

- Created `frontend/src/__test-utils__/learning-test-helpers.tsx` with:
  - `renderWithProviders(ui, options?)` — wraps with ThemeProvider, QueryClientProvider (fresh `QueryClient`, `retry: false`), and MemoryRouter (default `initialEntries: ['/']`)
  - `createQueryClient()` — returns a fresh `QueryClient` with `retry: false`
  - `createMockUser()` — returns `{ id: 'test-user-id', email: 'test@example.com' }`
  - `vi.mock('framer-motion', ...)` stubs `motion.div`, `motion.path`, `motion.circle`, `motion.g` as plain DOM nodes
  - `vi.mock('@/stores/auth', ...)` returns a default logged-in user (`useAuthStore`)
  - localStorage polyfill (jsdom in Node ≥22 doesn't provide it natively; ThemeProvider needs it)

- Created `frontend/src/pages/__tests__/learning/smoke.test.tsx` with:
  - `it.skip('smoke — LearningPage (pending Wave 2 Task 3)', ...)` — placeholder; real test activates when `LearningPage.tsx` is created
  - `describe('test infrastructure', ...)` with 2 passing tests:
    1. Renders trivial `<div>test</div>` through `renderWithProviders` and asserts text
    2. Verifies `createQueryClient()` returns fresh instances (reference inequality)

- Key discovery: jsdom in newer Node.js (≥22) warns `localStorage is not available because --localstorage-file was not provided`. The `ThemeProvider` component reads `localStorage` during mount (`getInitialTheme`), so without a polyfill the test crashes. The polyfill is placed in the helper at module level, before providers are rendered.

- Pattern used for `vi.mock` matches `SettingsPage.test.tsx` style (top-level `vi.mock` calls before exports).

## Wave 1, Task 1 — Content data file + tests

**Files created:**
- `frontend/src/content/learning.ts` (848 lines, ~53 KB) — typed data + Zod schema + helpers, no JSX
- `frontend/src/content/__tests__/learning.test.ts` (17 tests) — pure-data tests, no React/vi.mock

**Test results:** 17/17 pass (`pnpm vitest run src/content/__tests__/learning.test.ts` → 1.01s, all green). `pnpm tsc --noEmit` → exit 0.

**Content design notes:**

- Total prose: ~5,453 words across 6 sections. Per-section actual word counts (drives `WORD_COUNTS`): `assets=820, cult=700, roles=1214, strategies=1107, skills=811, configs=801`. All match the spec's required minutes (5/4/7/6/5/5) via `ceil(words/200)`.
- Each section has 6-8 content blocks of varied types (text + list + diagram + callout). Per-section block counts: assets=8, cult=7, roles=9, strategies=8, skills=8, configs=8.
- Diagram IDs are URL-safe lowercase slugs (`asset-pipeline`, `cult-architecture`, `role-graph`, `strategy-flow`, `skill-loading`, `config-flow`). The diagram component (Wave 2) will dispatch on these IDs.
- Content draws from authoritative backend sources:
  - 10 skill names match `scholarflow_skills.py` `_SKILL_SEEDS` exactly
  - 9 role descriptions match `factory.py` `AGENT_REGISTRY` keys
  - 4 strategies (direct/critique/reflection/evaluator_optimizer) match `models/__init__.py` `Strategy` enum
  - 14 configs = 7 seed (`_AGENT_SEEDS`) + 7 default (`_DEFAULT_AGENT_CONFIGS` in `agents.py`)

**Schema design notes:**

- `learningSectionSchema` uses `z.object` + `z.enum` for difficulty/icon, `z.string().regex(/^[a-z0-9-]+$/)` for id/slug, `z.number().int().positive()` for readingMinutes, `z.array(contentBlockSchema).min(3).max(10)` for sections.
- `contentBlockSchema` is `z.discriminatedUnion('type', [text, diagram, list, callout])`. Diagram IDs also use the URL-safe regex.
- `learningSections` is `as const satisfies ReadonlyArray<LearningSection>` so the literal types are preserved (`icon: 'FileText'`, not `string`).
- The catalog passes its own schema (verified by test 6: `learningSectionSchema.parse(learningSections[0])` does not throw).

**Helper signatures:**

- `computeReadingMinutes(slug, textWords)` — `Math.max(1, Math.ceil(textWords / 200))`. Throws on negative or non-finite input. The `slug` arg is only used in the error message; it is the catalogue that decides which words go in.
- `countWords(text)` — `text.trim().split(/\s+/).length` (returns 0 for empty/whitespace). Exposed for future tooling to recompute `WORD_COUNTS` automatically.
- `getSectionBySlug(slug)` — `learningSections.find((s) => s.slug === slug)`. Returns `undefined` for unknown slugs.
- `LEARNING_SECTION_SLUGS` and `LEARNING_SECTION_IDS` — readonly arrays for navigation/sitemap use.

**Test gotchas (Wave 2 onwards should know):**

- Spec required `import { ... } from '@/content/learning'` (alias), not relative `../learning`. The `@` alias resolves via `vitest.config.ts` → `path.resolve(__dirname, './src')` and `tsconfig.json` → `paths: { "@/*": ["./src/*"] }`.
- Spec required `.parse()` + `.toThrow()` for negative schema cases (not `.safeParse()`). The `.parse()` API throws `ZodError` synchronously.
- The Word-Count-driven minutes design (test #11 in original 14-test list → "matches the readingMinutes recorded for every section") was verified by computing `computeReadingMinutes(slug, WORD_COUNTS[slug])` and asserting equality with `s.readingMinutes`. This guards against accidental drift between the const and the catalog.
- The schema's `sections: z.array(...).min(3).max(10)` is exercised in the test for `sections.length >= 3`; the upper bound is not in the spec but prevents runaway data files.
- The catalog uses `as const` so the literal types of `icon: 'FileText'`, `difficulty: 'Beginner'` etc. are preserved end-to-end. Downstream pages should infer from the catalog, not from the Zod schema, to keep the literal types.

**Open items for Wave 2 (Task 3+):**

- Need a `Diagram` component that dispatches on `diagramId` and renders the six diagrams. The diagram IDs are stable contracts — do not rename casually.
- The `LucideIconName` literal type and `LUCIDE_ICON_NAMES` const tuple let downstream pages render `<DynamicIcon name={s.icon} />` without importing every icon. Consider a thin `DynamicIcon` wrapper that resolves the string to the lucide-react component.
- The `LUCIDE_ICON_NAMES` set in the spec is 8 names (the 6 used + 2 spares: `GraduationCap`, `BookOpen`). The 2 spares are reserved for future sections; do not rename them.
- The `Cult` section description is the only one that contains a quoted string ("The Cult") — Wave 2 detail pages should preserve the quotation marks in the heading.

## Wave 2, Task 3 — Learning index page

**File created:** `frontend/src/pages/LearningPage.tsx`

**Architecture:**
- Dynamic icon resolution via `ICONS: Record<LucideIconName, LucideIcon>` map — imports all 8 Lucide icons from `LUCIDE_ICON_NAMES`, resolves at render time via `const Icon = ICONS[section.icon]`
- `difficultyVariant()` helper maps `Difficulty` to `Badge` variant: `Beginner → secondary`, `Intermediate → default`, `Advanced → destructive`
- PageHeader has no `icon` prop — the GraduationCap icon is rendered as an adjacent decorative badge in a flex container alongside PageHeader
- Root wrapper uses `animate-in fade-in duration-500` (matching DashboardPage pattern)

**Grid layout:**
- `grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6` — responsive 1→2→3 columns
- Each card wrapped in `Link to={"/learning/" + section.slug}` with `group block h-full`
- Card has `hover:border-primary/30 transition-all duration-300 hover:shadow-lg hover:shadow-primary/5`
- "Read more →" text uses `group-hover:translate-x-0.5` for subtle hover micro-interaction

**Animation:**
- `useReducedMotion()` + `withReducedMotion()` for accessibility
- `staggerContainer` (with `staggerChildren: 0.06`, `delayChildren: 0.05`) on the grid motion.div
- `cardVariants` on each card motion.div (fade-in, y-offset, scale entrance)

**Test update:**
- Un-skipped the smoke test — now imports `LearningPage` and `learningSections`, renders via `renderWithProviders`, iterates all 6 sections asserting `screen.getByText(section.title)` is in document
- All 3 tests pass (1 smoke + 2 infrastructure)

**Gotcha:** PageHeader component does not accept an `icon` prop despite task spec mentioning it. Handle the icon externally.

## Wave 2, Task 7 — Strategies detail page

**Files created:**
- `frontend/src/pages/learning/StrategiesPage.tsx` — default export `StrategiesPage`
- `frontend/src/pages/__tests__/learning/StrategiesPage.test.tsx` — 8 tests, all pass

**Architecture:**
- Mirrors AssetsPage pattern: `PageMotion` wrapper, `ContentBlockRenderer` switch, `CALLOUT_STYLES` config, `LIST_ICON_MAP`
- 9 content blocks rendered in order (text ×6, list ×1, diagram ×1, callout ×1)
- 4-list-item grid: `grid-cols-1 md:grid-cols-2`
- CTA footer: "View Workflows" → `/workflows`, "← Back to Learning" → `/learning`

**Diagram (StrategyFlowDiagram):**
- Hand-authored SVG `viewBox="0 0 800 460"` with 4 parallel vertical lanes
- Lane centers: x = 130 (direct), 290 (critique), 450 (reflection), 610 (evaluator_optimizer)
- Gold-filled circles (`#D4A017`), navy strokes (`#1B2A4A`, `#334155`)
- Lane 4 has a curved bidirectional loop arrow: cubic bezier `C 80 ... 80 ...`
- `prefersReducedMotion` branches: lane 4 loop arrow renders as plain `<path>` (no animation) when motion reduced
- Lane labels at y=35 with `style={{ textTransform: 'uppercase', letterSpacing: '1px' }}`
- Cost labels at `lane.x + 65` on right side: "1x", "2x", "2.5x", "8x"

**Icon resolution:**
- `Swords` for PageHeader icon (exists in lucide-react v0.294.0)
- List icons: `Zap`, `MessageSquare` (fallback for missing `MessageSquareWarning`), `RefreshCw` (fallback for missing `Reflection`), `IterationCw`
- All CALLOUT_STYLES variants have explicit `icon` property to avoid TS `as const` union narrowing

**Test patterns:**
- 8 tests covering: title (heading role), Advanced badge, breadcrumb, 4 strategy names, diagram `role="img"`, callout, View Workflows link, Back to Learning link
- Strategy names found via `getAllByText` (they appear in both card h4 and SVG lane labels)
- Breadcrumb scoped via `within(nav)` to avoid heading/title clashes

**Files created:**
- `frontend/src/pages/learning/AssetsPage.tsx` — default export `AssetsPage`
- `frontend/src/pages/__tests__/learning/AssetsPage.test.tsx` — 10 tests

**Architecture:**
- `PageMotion` wrapper (from `@/components/shared/PageMotion`) handles entrance/exit animations and `prefers-reduced-motion`
- Section data: `learningSections.find(s => s.slug === 'assets')!`
- Block renderer dispatches on `block.type` via `ContentBlockRenderer` switch component
- No `file-search` icon in `LUCIDE_ICON_NAMES` — built a secondary `LIST_ICON_MAP` for list item icons (`Upload`, `Database`, `FileSearch`, `Scissors`, `Search`)
- `FileSearch` exists in lucide-react v0.294.0 (`file-search.js` in dist)

**Diagram (AssetPipelineDiagram):**
- Hand-authored SVG with `viewBox="0 0 400 580"`, vertical 5-stage pipeline
- Uses only stubbed motion primitives: `motion.circle`, `motion.path`, `motion.g` (no `motion.rect` — test mock doesn't include it)
- Arrow paths use `pathLength` animation with 1.5s duration
- Rect-shaped nodes wrap `<rect>` in `motion.g` for fade-in instead of `motion.rect`
- Gold (#d4a574) arrows, slate (#64748b) nodes

**Callout renderer:**
- Variant config with `border`, `bg`, `icon`, `iconColor` per variant (blue/info, green/tip, amber/warning)
- Colored left border via `border-l-*` utilities

**Test gotchas (unique to this page):**
- "Assets" appears in both PageHeader h1 and breadcrumb — use `getByRole('heading')` for the title test, `getAllByText` for breadcrumb
- "Upload", "Object storage", "Text extraction" appear in both the diagram SVG and the list — use `getAllByText` with `.length >= 1`
- "Beginner" appears in both the page header badge area — use `getAllByText`

## Wave 2, Task 8 — Configs detail page

**Files created:**
- `frontend/src/pages/learning/ConfigsPage.tsx` — default export `ConfigsPage`
- `frontend/src/pages/__tests__/learning/ConfigsPage.test.tsx` — 8 tests, all pass

**Architecture:**
- Mirrors AssetsPage pattern: `PageMotion` wrapper, `CALLOUT_STYLES` config, `LIST_ICON_MAP`
- 7 content blocks rendered in order (text ×4, list ×1, diagram ×1, callout ×1)
- 14-item list grid: `grid-cols-1 sm:grid-cols-2`
- CTA footer: "Manage Configurations" → `/cult/configs`, "← Back to Learning" → `/learning`
- `Settings2` icon for page header, `AlertTriangle` for warning callout

**Diagram (ConfigFlowDiagram):**
- Hand-authored SVG `viewBox="0 0 500 600"`, vertical 5-stage pipeline
- 5 stages: config_id (gold/#d4a574) → DB lookup (navy/#475569) → Skill concat (navy/#475569 with 3 side skill boxes) → Agent class (navy/#475569) → Runnable instance (emerald/#10b981)
- 3 skill boxes on left side feeding into Skill concat: eu-horizon, academic-writing, project-mgmt
- Uses `motion.g` for node fade-in, `motion.path` for animated arrow drawing (pathLength)
- `HorizontalArrow` component for skill → concat connections
- No `motion.rect` — rects wrapped in `motion.g` for compatibility with test mock

**List icons needed:**
- `FileText`, `ClipboardCheck`, `KanbanSquare`, `FileSignature`, `Swords`, `Search`, `PenLine`, `Sparkles`, `Microscope`

**Test gotchas (unique to this page):**
- "Agent Configurations" appears in THREE places: breadcrumb span, PageHeader h1 — use `getAllByText` for all queries
- Callout title uses Unicode RIGHT SINGLE QUOTATION MARK (U+2019) in "Don't" — use a function matcher with `content.includes()` instead of exact match
- `Learning` link and `← Back to Learning` link both point to `/learning` — distinguish by text content

## Wave 2, Task 9 — Roles detail page

**Files created:**
- `frontend/src/pages/learning/RolesPage.tsx` — default export `RolesPage`
- `frontend/src/pages/__tests__/learning/RolesPage.test.tsx` — 8 tests, all pass

**Architecture:**
- Mirrors AssetsPage/CultPage pattern: `PageMotion` wrapper, `ContentBlockRenderer` switch, `CALLOUT_STYLES` config, `LIST_ICON_MAP`
- 11 content blocks rendered in order (text ×8, list ×1, diagram ×1, callout ×1)
- 9-item role list grid: `grid-cols-1 sm:grid-cols-2 lg:grid-cols-3`
- CTA footer: "Browse Agents" → `/cult/agents`, "← Back to Learning" → `/learning`
- `Users` icon for page header, `Info` for callout

**Diagram (RoleGraphDiagram):**
- Hand-authored SVG `viewBox="0 0 500 500"`, circular graph layout
- Center: Manager node (gold/#d4a574 circle, r=60) with pulse animation via `pulseVariants`
- 8 outer role nodes (navy/#334155 circles, r=48) at radius 170px:
  - Roles arranged at 45° intervals: researcher (top), writer (top-right), reviewer (right), deep_reviewer (bottom-right), recommender (bottom), revision (bottom-left), debater (left), review_writer (top-left)
- Gold animated connecting lines (stroke-dasharray pathLength) from each outer node to center
- Tiny SVG icon shapes inside each node: Search (magnifying glass), PenLine (diagonal), ClipboardCheck (rect+check), Microscope (circle+lens), Sparkles (star), RefreshCw (circular arrow), Swords (crossed lines), FileSignature (wave curve)
- All motion primitives wrapped in reduced-motion checks

**Icon resolution:**
- `LIST_ICON_MAP` must include ALL 9 Lucide icons: `Search`, `PenLine`, `ClipboardCheck`, `Microscope`, `Sparkles`, `RefreshCw`, `KanbanSquare`, `Swords`, `FileSignature`
- `KanbanSquare` was initially missing from the map — the data file has it for the `manager` role, causing React crash in tests
- `CALLOUT_STYLES` must include all 3 variants (info/tip/warning) to satisfy `CalloutBlock.variant` type union, even though only `info` is used in this section

**New test mock requirement:**
- The shared `framer-motion` mock in `learning-test-helpers.tsx` needed `motion.p` added (it only had `div`, `path`, `circle`, `g`) — all text blocks use `motion.p` via `ContentBlockRenderer`

**Test gotchas:**
- "Agent Roles" appears in BOTH breadcrumb span AND PageHeader h1 — use `getAllByText` not `getByText`
- All 9 role names appear in both list grid cards AND SVG diagram text — use `getAllByText` with `length >= 1`
- Breadcrumb check for "Agent Roles" must use `getAllByText`
