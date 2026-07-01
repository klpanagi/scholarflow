#!/usr/bin/env python3
"""E2E integration test for the asset processing pipeline.

Verifies against *running* services (backend, DB, MinIO, ES, GROBID, ARQ worker).

Usage:
    # Ensure docker-compose is up and ARQ worker is running
    python tests/scripts/test_asset_pipeline_e2e.py

Prerequisites:
    - docker-compose up -d (postgres, minio, elasticsearch, grobid, redis)
    - ARQ worker running: uv run arq app.tasks.worker_settings.WorkerSettings
    - Backend running: uv run uvicorn app.main:app
"""

import asyncio
import logging
import os
import sys
import time

import httpx

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("e2e")

BASE_URL = os.environ.get("API_BASE_URL", "http://localhost:8000")

# Use a random-ish user per run to avoid conflicts from stale data
import uuid
_RUN_ID = uuid.uuid4().hex[:8]
TEST_EMAIL = f"e2e-{_RUN_ID}@example.com"
TEST_PASSWORD = "TestPass123!"
TEST_NAME = "E2E Bot"

# A known-short arXiv paper (2 pages)
PDF_URL = "https://arxiv.org/pdf/2103.00020"


class E2ETest:
    def __init__(self) -> None:
        self.client = httpx.AsyncClient(base_url=BASE_URL, timeout=45.0, follow_redirects=True)
        self.token: str | None = None
        self.asset_id: str | None = None

    async def __aenter__(self) -> "E2ETest":
        return self

    async def __aexit__(self, *args: object) -> None:
        await self.client.aclose()

    # ── Auth ──────────────────────────────────────────────────────────────

    async def _register(self) -> None:
        resp = await self.client.post(
            "/api/auth/register",
            json={"email": TEST_EMAIL, "password": TEST_PASSWORD, "name": TEST_NAME},
        )
        if resp.status_code == 409:
            logger.info("User already exists, logging in")
            return await self._login()
        resp.raise_for_status()
        logger.info("Registered user %s", TEST_EMAIL)
        await self._login()

    async def _login(self) -> None:
        resp = await self.client.post(
            "/api/auth/login",
            data={"username": TEST_EMAIL, "password": TEST_PASSWORD},
        )
        resp.raise_for_status()
        self.token = resp.json()["access_token"]
        logger.info("Logged in, got JWT")

    # ── Settings ──────────────────────────────────────────────────────────

    async def test_extraction_method_setting(self) -> None:
        # GET default
        resp = await self.client.get(
            "/api/settings/extraction-method",
            headers=self._auth_header,
        )
        resp.raise_for_status()
        default = resp.json()["method"]
        logger.info("Default extraction method: %s", default)
        assert default in ("grobid", "pymupdf", "tika"), f"Unexpected method: {default}"

        # SET to pymupdf
        resp = await self.client.post(
            "/api/settings/extraction-method",
            json={"method": "pymupdf"},
            headers=self._auth_header,
        )
        resp.raise_for_status()
        assert resp.json()["method"] == "pymupdf"

        # Verify persisted
        resp = await self.client.get(
            "/api/settings/extraction-method",
            headers=self._auth_header,
        )
        assert resp.json()["method"] == "pymupdf"

        # Reset to grobid
        resp = await self.client.post(
            "/api/settings/extraction-method",
            json={"method": "grobid"},
            headers=self._auth_header,
        )
        resp.raise_for_status()
        assert resp.json()["method"] == "grobid"
        logger.info("Extraction method setting: OK")

    # ── Upload ────────────────────────────────────────────────────────────

    async def _download_pdf(self) -> bytes:
        logger.info("Downloading test PDF from %s …", PDF_URL)
        async with httpx.AsyncClient(follow_redirects=True, timeout=30.0) as c:
            resp = await c.get(PDF_URL)
        resp.raise_for_status()
        logger.info("Downloaded %d bytes", len(resp.content))
        return resp.content

    async def test_upload(self, pdf_bytes: bytes) -> dict:
        resp = await self.client.post(
            "/api/assets/",
            files={"file": ("paper.pdf", pdf_bytes, "application/pdf")},
            headers={**self._auth_header},  # no Content-Type for multipart
        )
        resp.raise_for_status()
        asset = resp.json()
        self.asset_id = asset["id"]
        logger.info(
            "Uploaded asset id=%s title=%r status=%s",
            asset["id"], asset.get("title"), asset["processing_status"],
        )
        assert asset["processing_status"] == "pending", (
            f"Expected pending, got {asset['processing_status']}"
        )
        return asset

    # ── Poll ──────────────────────────────────────────────────────────────

    async def test_poll_until_completed(self, max_wait: int = 300) -> dict:
        assert self.asset_id
        start = time.monotonic()
        while True:
            elapsed = time.monotonic() - start
            if elapsed > max_wait:
                raise TimeoutError(f"Asset not completed after {max_wait}s")

            resp = await self.client.get(
                f"/api/assets/{self.asset_id}",
                headers=self._auth_header,
            )
            resp.raise_for_status()
            asset = resp.json()
            status = asset["processing_status"]
            logger.info("Poll [%4.0fs] %s", elapsed, status)

            if status == "completed":
                logger.info("Completed in %.0fs", elapsed)
                return asset
            if status == "failed":
                raise RuntimeError(f"Processing failed: {asset}")

            await asyncio.sleep(3)

    # ── Verifications ─────────────────────────────────────────────────────

    async def test_es_search(self) -> list[dict]:
        # Try multiple query terms since we don't know the exact paper title
        queries = ["machine learning", "introduction", "learning", "short", "transferable"]
        for q in queries:
            resp = await self.client.get(
                "/api/assets/search",
                params={"q": q, "limit": 10},
                headers=self._auth_header,
            )
            resp.raise_for_status()
            results = resp.json()
            logger.info("ES search q=%r returned %d results", q, len(results))
            if results:
                for r in results[:2]:
                    snippet = (r.get("title") or r.get("text") or "")[:100]
                    logger.info("  Hit: %s …", snippet)
                return results
        raise AssertionError(f"No ES search results for any query: {queries}")

    async def test_analysis(self, asset: dict) -> None:
        logger.info("Asset title: %r", asset.get("title"))
        logger.info("processing_status: %s", asset.get("processing_status"))
        if asset.get("analysis"):
            logger.info("Analysis keys: %s", list(asset["analysis"].keys()))

        analysis = asset.get("analysis")
        assert analysis, "Paper.analysis is empty"

        # extraction_meta
        meta = analysis.get("extraction_meta")
        assert meta, "No extraction_meta in analysis"
        logger.info(
            "Extraction meta: source=%s sections=%d refs=%d",
            meta.get("source"), len(meta.get("sections", [])), len(meta.get("references", [])),
        )

        # llm_analysis (may be absent if LLM call failed; that's acceptable in some envs)
        llm = analysis.get("llm_analysis")
        if llm:
            logger.info("LLM analysis: keywords=%s", llm.get("keywords", [])[:5])
        else:
            logger.warning("LLM analysis missing (expected if API keys not configured)")

    # ── Cleanup ───────────────────────────────────────────────────────────

    async def cleanup(self) -> None:
        if self.asset_id:
            try:
                resp = await self.client.delete(
                    f"/api/assets/{self.asset_id}",
                    headers=self._auth_header,
                )
                logger.info("Deleted asset %s (HTTP %d)", self.asset_id, resp.status_code)
            except Exception as exc:
                logger.warning("Cleanup failed: %s", exc)

    # ── Helpers ───────────────────────────────────────────────────────────

    @property
    def _auth_header(self) -> dict[str, str]:
        assert self.token
        return {"Authorization": f"Bearer {self.token}"}


async def main() -> None:
    async with E2ETest() as test:
        try:
            logger.info("=" * 60)
            logger.info("E2E Asset Pipeline Test  (run-id: %s)", _RUN_ID)
            logger.info("=" * 60)

            # 1. Auth
            await test._register()

            # 2. Settings
            await test.test_extraction_method_setting()

            # 3. Upload
            pdf = await test._download_pdf()
            asset = await test.test_upload(pdf)

            # 4. Poll (this is the critical part — ARQ worker must process it)
            asset = await test.test_poll_until_completed()

            # 5. ES search
            await test.test_es_search()

            # 6. Analysis
            await test.test_analysis(asset)

            logger.info("=" * 60)
            logger.info("ALL CHECKS PASSED")
            logger.info("=" * 60)

        except Exception as exc:
            logger.exception("E2E test FAILED: %s", exc)
            sys.exit(1)
        finally:
            await test.cleanup()


if __name__ == "__main__":
    asyncio.run(main())
