#!/usr/bin/env python3
"""E2E integration test for the chat streaming pipeline.

Verifies: auth → agent config lookup → session creation → SSE streaming →
message history.

Usage:
    python tests/scripts/test_chat_e2e.py

Prerequisites:
    - docker-compose up (postgres, backend, redis)
    - Backend running: uv run uvicorn app.main:app
"""

import asyncio
import json
import logging
import os
import sys
import uuid as _uuid

import httpx

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("e2e-chat")

BASE_URL = os.environ.get("API_BASE_URL", "http://localhost:8000")

_RUN_ID = _uuid.uuid4().hex[:8]
TEST_EMAIL = f"chat-e2e-{_RUN_ID}@example.com"
TEST_PASSWORD = "ChatTest123!"
TEST_NAME = "Chat E2E Bot"


class ChatE2ETest:
    def __init__(self) -> None:
        self.client = httpx.AsyncClient(base_url=BASE_URL, timeout=45.0, follow_redirects=True)
        self.token: str | None = None
        self.agent_config_id: str | None = None
        self.session_id: str | None = None

    async def __aenter__(self) -> "ChatE2ETest":
        return self

    async def __aexit__(self, *args: object) -> None:
        await self.client.aclose()

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

    async def test_get_agent(self) -> None:
        # Try the "Default Chat" seed first (applied globally on first configs fetch)
        resp = await self.client.get(
            "/api/agents/configs",
            headers=self._auth_header,
        )
        resp.raise_for_status()
        configs = resp.json()
        logger.info("Found %d agent configs", len(configs))
        for c in configs:
            if c["name"] == "Default Chat" and c["provider"] == "opencode":
                self.agent_config_id = c["id"]
                logger.info("Using Default Chat: id=%s model=%s", c["id"], c["model"])
                return
        # Fallback: create one with opencode provider (for fresh DBs where seed wasn't applied)
        logger.info("Default Chat not found, creating test agent")
        resp = await self.client.post(
            "/api/agents/configs",
            json={
                "name": f"E2E Chat Agent {_RUN_ID}",
                "role": "chat",
                "provider": "opencode",
                "model": "deepseek-v4-flash",
                "strategy": "direct",
                "tools": [],
                "system_prompt": "You are a helpful assistant. Answer concisely.",
            },
            headers=self._auth_header,
        )
        resp.raise_for_status()
        config = resp.json()
        self.agent_config_id = config["id"]
        logger.info("Created agent: id=%s model=%s", config["id"], config["model"])

    async def test_create_session(self) -> None:
        assert self.agent_config_id
        resp = await self.client.post(
            "/api/chat/sessions",
            json={
                "agent_config_id": self.agent_config_id,
                "title": f"E2E Chat Test {_RUN_ID}",
            },
            headers=self._auth_header,
        )
        resp.raise_for_status()
        session = resp.json()
        self.session_id = session["id"]
        logger.info("Created session id=%s title=%r", self.session_id, session.get("title"))

    async def test_send_message(self, content: str) -> str:
        assert self.session_id and self.token
        url = f"{BASE_URL}/api/chat/sessions/{self.session_id}/stream"
        full_response = ""
        token_count = 0
        saw_thinking = False

        logger.info("Sending: %s …", content[:60])
        async with httpx.AsyncClient(timeout=120.0, follow_redirects=True) as sc:
            async with sc.stream(
                "POST",
                url,
                json={"content": content},
                headers={"Authorization": f"Bearer {self.token}"},
            ) as resp:
                resp.raise_for_status()
                async for line in resp.aiter_lines():
                    if not line.startswith("data: "):
                        continue
                    payload = line.removeprefix("data: ")
                    try:
                        event = json.loads(payload)
                    except json.JSONDecodeError:
                        continue

                    t = event.get("type")
                    if t == "thinking":
                        saw_thinking = True
                    elif t == "token":
                        full_response += event.get("content", "")
                        token_count += 1
                    elif t == "done":
                        logger.info("  [done] %d tokens", token_count)
                        break
                    elif t == "error":
                        raise RuntimeError(f"Stream error: {event.get('content')}")

        assert saw_thinking, "No 'thinking' event received"
        assert token_count > 0, f"No tokens received"
        return full_response

    async def test_get_messages(self) -> list[dict]:
        assert self.session_id
        resp = await self.client.get(
            f"/api/chat/sessions/{self.session_id}/messages",
            headers=self._auth_header,
        )
        resp.raise_for_status()
        messages = resp.json()
        logger.info("Conversation: %d messages", len(messages))
        for m in messages:
            p = (m.get("content", "")[:70] or "(empty)").replace("\n", " ")
            logger.info("  [%s] %s", m["role"], p)
        return messages

    async def cleanup(self) -> None:
        if self.session_id:
            try:
                resp = await self.client.delete(
                    f"/api/chat/sessions/{self.session_id}",
                    headers=self._auth_header,
                )
                logger.info("Deleted session (HTTP %d)", resp.status_code)
            except Exception as exc:
                logger.warning("Cleanup: %s", exc)

    @property
    def _auth_header(self) -> dict[str, str]:
        assert self.token
        return {"Authorization": f"Bearer {self.token}"}


async def main() -> None:
    async with ChatE2ETest() as test:
        try:
            logger.info("=" * 60)
            logger.info("Chat E2E Test  (run-id: %s)", _RUN_ID)
            logger.info("=" * 60)

            await test._register()
            await test.test_get_agent()
            await test.test_create_session()

            await test.test_send_message("What is 2+2? Answer briefly.")
            await test.test_send_message("What is the capital of France?")
            await test.test_send_message("Name three colors of the rainbow.")

            messages = await test.test_get_messages()
            assert len(messages) >= 6, f"Expected >=6, got {len(messages)}"
            for i, m in enumerate(messages):
                expected = "user" if i % 2 == 0 else "assistant"
                assert m["role"] == expected, f"Msg {i}: expected {expected}, got {m['role']}"

            logger.info("=" * 60)
            logger.info("ALL CHECKS PASSED")
            logger.info("=" * 60)

        except Exception:
            logger.exception("E2E chat test FAILED")
            sys.exit(1)
        finally:
            await test.cleanup()


if __name__ == "__main__":
    asyncio.run(main())
