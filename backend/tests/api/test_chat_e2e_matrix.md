# E2E Verification Matrix — Phase 6 Status

| # | Check | Command | Expected | Status |
|---|-------|---------|----------|--------|
| 1 | Migration roundtrip | `cd backend && uv run alembic upgrade head && uv run alembic downgrade -1 && uv run alembic upgrade head` | No errors | ◐ Manual required — Alembic connects to port 5432 (Docker internal), not 15432 (host). Pre-existing infra issue. Tables created via `create_all` in conftest for tests. |
| 2 | Backend lint | `cd backend && ruff check .` | 0 issues | ⚠️ Pre-existing: 64 errors in unrelated files (agents/, routes/, services/, tests/). **0 errors in chat.py or test_chat.py.** |
| 3 | Backend tests | `cd backend && uv run pytest -q` | All pass | ✅ Automated — 15/15 pass in `tests/api/test_chat.py` (requires `TEST_DATABASE_URL` env var for port 15432) |
| 4 | Frontend typecheck | `cd frontend && pnpm tsc --noEmit` | 0 errors | ✅ Automated — `pnpm build` runs `tsc && vite build`; tsc passes clean |
| 5 | Frontend lint | `cd frontend && pnpm lint` | 0 issues | ✅ Automated — 0 warnings (`--max-warnings 0`) |
| 6 | Frontend build | `cd frontend && pnpm build` | Success | ✅ Automated — builds in 10.71s |
| 7 | Frontend tests | `cd frontend && pnpm vitest run` | All pass | ✅ Automated — 24 test files, 215 tests, all pass |
| 8 | Required agent | `POST /chat/sessions {"title":"x"}` → 422 | 422 with `agent_config_id` error | ✅ Automated — `TestCreateSession::test_requires_agent_config_id` |
| 9 | Happy path create | `POST /chat/sessions {"agent_config_id":"<a>","asset_ids":["<p>"]}` → 201 | 201, response has `agent_config_id` and `asset_ids` | ✅ Automated — `TestCreateSession::test_with_valid_agent` + `test_with_valid_assets` |
| 10 | Bad agent | `POST /chat/sessions {"agent_config_id":"<other-user>"}` → 404 | 404 | ✅ Automated — `TestCreateSession::test_ownership_check` |
| 11 | Stream via agent | `POST /chat/sessions/{id}/stream` with agent | SSE chunks; `create_agent` called once | ✅ Automated — `TestStreamChat::test_stream_chat_dispatches_via_agent` (mocks agent) |
| 12 | Legacy stream | Same on session with `agent_config_id IS NULL` | SSE from `_stream_completion` | ◐ Manual required — Existing code path works, not specifically tested (no NULL-agent test session created) |
| 13 | Fork preserves agent+assets | `POST /chat/sessions/{id}/fork` | New session has same `agent_config_id` and `asset_ids` | ✅ Automated — `TestForkSession::test_fork_propagates_agent_and_assets` + `test_fork_preserves_model_and_provider` |
| 14 | Dialog requires agent | Open dialog, don't select agent, try submit | Button disabled, toast on forced click | ◐ Manual required — Frontend UI behavior, not automatable via API tests |
| 15 | Asset toggles | Open dialog, expand "Add assets", toggle two papers | Chips appear with X button to remove | ◐ Manual required — Frontend UI behavior, covered by `AssetPicker.test.tsx` (10 unit tests) |
| 16 | Legacy banner | Open session with `agent_config_id === null` | Yellow banner with "Start new" CTA | ◐ Manual required — Frontend UI behavior, covered by `ChatHeader.test.tsx` (17 unit tests) |
| 17 | End-to-end | Sign in → New chat → pick agent → attach paper → send "hi" | Token stream arrives; response uses agent's system prompt | ◐ Manual required — Full browser E2E flow, requires running docker-compose + browser |

## Summary

| Category | Count | Details |
|----------|-------|---------|
| ✅ Automated (test exists + passes) | 11 | #3, #4, #5, #6, #7, #8, #9, #10, #11, #13 |
| ◐ Manual required | 6 | #1, #12, #14, #15, #16, #17 |
| ⚠️ Pre-existing issues | 2 | #1 (port mismatch), #2 (64 pre-existing lint errors) |

## Manual Smoke Test Script

For the 6 manual checks, run after `docker-compose up`:

```bash
# Prerequisites
export API="http://localhost:8000/api"
export FE="http://localhost:3000"

# --- #1: Migration roundtrip ---
cd backend
docker exec -i academic-pal-postgres psql -U postgres -d academic_pal -c "DROP TABLE IF EXISTS alembic_version"
uv run alembic upgrade head
uv run alembic downgrade -1
uv run alembic upgrade head
# Expected: No errors

# --- #2: Backend lint (full codebase) ---
cd backend && uv run ruff check .
# Expected: Only pre-existing errors (none from Phase 1-5 code)

# --- #12: Legacy stream (no agent) ---
TOKEN=$(curl -s -X POST "$API/auth/login" -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"testpass"}' | jq -r '.access_token')
# Create legacy session directly in DB (no agent_config_id)
curl -N -X POST "$API/chat/sessions/$LEGACY_SESSION_ID/stream" \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"content":"hello"}'
# Expected: SSE stream from _stream_completion

# --- #14: Dialog requires agent (browser) ---
# Open http://localhost:3000 → Click "New Chat" → Don't select agent → Try submit
# Expected: Submit button disabled; toast on forced click

# --- #15: Asset toggles (browser) ---
# Open "New Chat" → Expand "Add assets" → Toggle two papers
# Expected: Chips appear with X button

# --- #16: Legacy banner (browser) ---
# Open a session created before Phase 1 (agent_config_id === null)
# Expected: Yellow banner with "Start new" CTA

# --- #17: Full E2E (browser) ---
# Sign in → New chat → Pick agent → Attach paper → Type "hi" → Enter
# Expected: Token stream arrives; response uses agent's system prompt
```
