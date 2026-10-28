"""Browser authentication journeys against the actual API and isolated test database."""
import asyncio
import os
from pathlib import Path
import signal
import subprocess

import httpx
import pytest
import uvicorn
from playwright.async_api import async_playwright, expect
expect.set_options(timeout=15000)
from tests.backend.integration.test_full_flow import stack  # noqa: F401

pytestmark = [pytest.mark.integration, pytest.mark.skipif(os.getenv("AGIS_INTEGRATION") != "1",
    reason="Start test infrastructure and set AGIS_INTEGRATION=1")]


@pytest.fixture
async def browser_stack(stack):
    server = uvicorn.Server(uvicorn.Config(stack.app, host="127.0.0.1", port=18008, lifespan="off", log_level="error"))
    server_task = asyncio.create_task(server.serve())
    frontend = subprocess.Popen(["npm", "run", "dev", "--", "--port", "15167", "--host", "127.0.0.1"],
        cwd=Path(__file__).resolve().parents[2] / "frontend", stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        env={**os.environ, "VITE_API_BASE_URL": "/api/v1", "VITE_BACKEND_URL": "http://127.0.0.1:18008"}, start_new_session=True)
    try:
        async with httpx.AsyncClient() as client:
            for _ in range(200):
                try:
                    if server.started and (await client.get("http://127.0.0.1:15167")).status_code == 200:
                        break
                except httpx.HTTPError:
                    pass
                await asyncio.sleep(.1)
            else:
                raise RuntimeError("Browser test servers failed to start")
        async with async_playwright() as playwright:
            browser = await playwright.chromium.launch()
            yield stack, browser
            await browser.close()
    finally:
        os.killpg(frontend.pid, signal.SIGTERM)
        await asyncio.to_thread(frontend.wait, 10)
        server.should_exit = True
        await asyncio.wait_for(server_task, 10)


@pytest.mark.parametrize("role,srn,home", [
    ("student", "PES2UG22CS001", "/workspace"),
    ("mentor", "mentor@example.test", "/mentor"),
    ("admin", "ADMIN", "/admin"),
])
async def test_login_refresh_and_logout(browser_stack, role, srn, home):
    stack, browser = browser_stack
    from models.user import User
    from core.security import hash_password
    await User(srn=srn.upper(), name="Browser User", role=role, password_hash=hash_password("test-password-123")).insert()
    context = await browser.new_context()
    page = await context.new_page()
    errors = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    await page.goto("http://127.0.0.1:15167/login")
    assert await page.locator("img[alt='PES University']").first.evaluate("image => image.complete && image.naturalWidth > 0")
    await page.get_by_label("SRN", exact=True).fill(srn)
    await page.get_by_label("Password", exact=True).fill("test-password-123")
    await page.get_by_role("button", name="Sign In", exact=True).click()
    await expect(page).to_have_url("http://127.0.0.1:15167" + home)
    # Force a signature-invalid access token; shared client must rotate from refresh.
    await page.evaluate("localStorage.setItem('agis_access_token', 'expired')")
    result = await page.evaluate("""async () => {
      const {apiRequest} = await import('/src/services/apiClient.ts');
      return apiRequest('/auth/me');
    }""")
    assert result["role"] == role
    await page.reload()
    await expect(page).to_have_url("http://127.0.0.1:15167" + home)
    await page.get_by_role("button", name="Logout", exact=True).first.click()
    await expect(page).to_have_url(__import__('re').compile(r"/(login)?$"))
    assert not errors, errors
    await context.close()


async def test_magic_link_access_and_revocation(browser_stack):
    stack, browser = browser_stack
    from services.workspace_service import workspace_service
    from fastapi import BackgroundTasks
    raw, workspace = await workspace_service.create_magic_link_workspace("Browser workspace", "admin")
    context = await browser.new_context()
    page = await context.new_page()
    await page.goto("http://127.0.0.1:15167/workspace/" + raw)
    await expect(page).to_have_url("http://127.0.0.1:15167/workspace")
    await workspace_service.revoke_workspace(workspace.workspace_id, BackgroundTasks())
    response = await page.evaluate("""async () => fetch('/api/v1/auth/me', {headers: {
      Authorization: 'Bearer ' + localStorage.getItem('agis_access_token')
    }}).then(r => r.status)""")
    assert response == 401
    await context.close()


async def test_complete_student_journey_with_real_kafka_worker(browser_stack):
    import re
    import uuid
    from aiokafka import AIOKafkaConsumer
    from unittest.mock import AsyncMock
    from tests.backend.integration.test_full_flow import INTAKE
    from core.config import settings
    from core.security import hash_password
    from models.user import User
    from workers.combined_agent_worker import CombinedAgentWorker
    stack, browser = browser_stack
    await User(srn="PES2UG22CS001", name="Journey User", role="student", password_hash=hash_password("test-password-123")).insert()
    worker = CombinedAgentWorker()
    worker.http_client = httpx.AsyncClient(transport=httpx.ASGITransport(app=stack.app), base_url="http://test",
        headers={"X-Worker-Secret": settings.WORKER_INTERNAL_SECRET})
    async def fake_agent(flow, inputs):
        return {"final_decision": {"status": "GO", "justification": "Validated evidence"}} if flow == "dfv" else {"report": "# Interview guide\n\nAsk about the last time the problem occurred."}
    worker._run_agent = AsyncMock(side_effect=fake_agent)
    consumers, tasks = [], []
    context = await browser.new_context()
    context.set_default_timeout(15000)
    page = await context.new_page()
    errors = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    try:
        for flow in ["dfv", "discovery"]:
            consumer = AIOKafkaConsumer("userSession." + flow, bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
                group_id="browser-" + uuid.uuid4().hex, auto_offset_reset="latest", enable_auto_commit=False)
            await consumer.start()
            for _ in range(50):
                await consumer.getmany(timeout_ms=100)
                if consumer.assignment(): break
            consumers.append(consumer)
            tasks.append(asyncio.create_task(worker._consume(consumer, getattr(worker, "_handle_" + flow))))
        await page.goto("http://127.0.0.1:15167/login")
        await page.get_by_label("SRN", exact=True).fill("PES2UG22CS001")
        await page.get_by_label("Password", exact=True).fill("test-password-123")
        await page.get_by_role("button", name="Sign In", exact=True).click()
        await expect(page).to_have_url("http://127.0.0.1:15167/workspace")
        await page.goto("http://127.0.0.1:15167/workspace/tipsc")
        for label, field in [("Problem Statement", "problem_statement"), ("Customer Segment", "customer_segment"),
            ("Consequence", "consequence"), ("Assumptions", "assumptions"), ("Proposed Solution", "proposed_solution"),
            ("Geography", "target_geography"), ("Sector", "industry_sector")]:
            value = INTAKE[field]
            await page.get_by_label(re.compile("^" + label)).fill("\n".join(value) if isinstance(value, list) else value)
        await page.get_by_role("button", name="Submit for TIPSC Evaluation").click()
        await expect(page.get_by_text("Ready for DFV", exact=True)).to_be_visible()
        # A full reload must restore server progress before stage guards run.
        await page.goto("http://127.0.0.1:15167/workspace/dfv")
        await expect(page.get_by_role("button", name="Run DFV Analysis", exact=True)).to_be_visible()
        for textarea in await page.locator("textarea").all():
            await textarea.fill("Evidence from twenty customers supports the market and implementation plan. " * 3)
        await page.get_by_role("button", name="Run DFV Analysis", exact=True).click()
        await expect(page.get_by_text("DFV Results", exact=True)).to_be_visible()
        await page.goto("http://127.0.0.1:15167/workspace/discovery")
        await expect(page.locator("textarea").first).to_be_visible()
        for textarea in await page.locator("textarea").all():
            await textarea.fill("Students seeking affordable mentors; interviews will explore existing alternatives.")
        await page.get_by_role("button", name="Review My Thinking").click()
        await page.get_by_role("button", name="Trigger Discovery Planner").click()
        await expect(page.get_by_role("heading", name="Interview guide", exact=True)).to_be_visible()
        assert worker._run_agent.await_count == 2
        assert not errors, errors
    finally:
        for task in tasks: task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
        for consumer in consumers: await consumer.stop()
        await worker.http_client.aclose()
        await context.close()
