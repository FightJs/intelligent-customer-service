# LLM Balance Error Degradation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task with verification checkpoints.

**Goal:** Prevent an upstream LLM 402 insufficient-balance response from turning session creation into a 500, and show a clear actionable error when chat cannot run.

**Architecture:** Keep the session and database flow independent from the optional greeting generation. Catch only Anthropic `APIStatusError` responses with status 402, return a fixed greeting for session creation, and translate the same condition at the API boundary into HTTP 503 with a user-safe detail. The frontend API client will preserve server error details so ChatPanel can display the recharge message.

**Tech Stack:** FastAPI, Anthropic Python SDK, pytest/TestClient, React/TypeScript, Vitest.

---

### Task 1: Add regression tests for 402 behavior

**Files:**
- Modify: `backend/tests/test_api.py`
- Modify: `frontend/tests/client.test.ts`

- [x] Add tests that make `initial_greeting` and `run_agent` raise a constructed Anthropic `APIStatusError` with HTTP 402.
- [x] Assert session creation remains HTTP 200 with a fallback greeting.
- [x] Assert chat returns HTTP 503 with the explicit balance message.
- [x] Assert frontend `chat()` exposes the server `detail` instead of only `chat: 503`.
- [x] Run the focused tests and confirm they fail against the current implementation.

### Task 2: Implement the minimal backend degradation

**Files:**
- Modify: `backend/agent/gather.py`
- Modify: `backend/api/app.py`

- [x] Catch only `APIStatusError` with status 402 in `initial_greeting`, log a warning without credentials, and return the existing fixed greeting.
- [x] Catch the same status in `/api/chat` and raise HTTP 503 with `LLM 服务余额不足，请联系管理员充值后重试。`.
- [x] Leave unrelated LLM failures visible as server errors so they are not mislabeled.

### Task 3: Surface backend error details in the frontend

**Files:**
- Modify: `frontend/src/api/client.ts`
- Modify: `frontend/src/components/ChatPanel/ChatPanel.tsx`

- [x] Add a small response-error helper that reads FastAPI `detail` and falls back to the status text.
- [x] Use it in session and chat requests.
- [x] Render the balance-specific message naturally in the existing AI message area.

### Task 4: Verify all affected behavior

- [x] Run backend focused tests, then the full backend suite.
- [x] Run frontend tests and `npm run build`.
- [x] Review the final diff for secrets, unrelated changes, and missing test coverage.
