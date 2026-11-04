"""All bundled logins against real MongoDB and browser UI; no Kafka or model calls.

Run with AGIS_AUTH_BROWSER=1 and AGIS_TEST_MONGODB_URI pointing to a local MongoDB.
Each test uses a temporary database that is deleted afterwards.
"""

import asyncio
import os
import subprocess
import uuid

import httpx
import pytest
import uvicorn
from core.processes import ProcessTree, child_options
from playwright.async_api import async_playwright, expect

from dev import ROOT, frontend_command

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        os.getenv("AGIS_AUTH_BROWSER") != "1",
        reason="Set AGIS_AUTH_BROWSER=1 with local test MongoDB",
    ),
]

BASE = "http://127.0.0.1:15168"


@pytest.fixture
async def role_browser(monkeypatch):
    from core.config import settings
    from database.branch_accounts import provision_branch_accounts
    from database.indexes import create_indexes
    from database.mongodb import connect_db, disconnect_db, get_client
    from main import create_app

    monkeypatch.setattr(settings, "MONGODB_DB_NAME", "role_browser_" + uuid.uuid4().hex)
    monkeypatch.setattr(settings, "RATE_LIMIT_LOGIN_PER_MINUTE", 1000)
    monkeypatch.setattr(settings, "RATE_LIMIT_API_PER_MINUTE", 10000)
    await connect_db()
    server = None
    server_task = None
    frontend = None
    tree = None
    try:
        await create_indexes()
        await provision_branch_accounts(get_client()[settings.MONGODB_DB_NAME])
        from models.team import Team
        from models.user import User

        for i in range(1, 4):
            mentor = await User.find_one(User.srn == f"MENTOR{i}")
            student = await User.find_one(User.srn == f"STUDENT{i}")
            team = Team(
                team_name=f"Role Test Team {i}", mentor_id=str(mentor.id), members=[student.srn]
            )
            await team.insert()
            await student.set({User.team_id: str(team.id)})
        server = uvicorn.Server(
            uvicorn.Config(
                create_app(), host="127.0.0.1", port=18009, lifespan="off", log_level="error"
            )
        )
        server_task = asyncio.create_task(server.serve())
        frontend = subprocess.Popen(
            frontend_command(port=15168),
            cwd=ROOT / "frontend",
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            env={
                **os.environ,
                "VITE_API_BASE_URL": "/api/v1",
                "VITE_BACKEND_URL": "http://127.0.0.1:18009",
            },
            **child_options(),
        )
        tree = ProcessTree(frontend.pid)
        async with httpx.AsyncClient() as client:
            for _ in range(200):
                try:
                    if server.started and (await client.get(BASE)).status_code == 200:
                        break
                except httpx.HTTPError:
                    pass
                await asyncio.sleep(0.1)
            else:
                raise RuntimeError("Role test servers did not start")
        async with async_playwright() as playwright:
            browser = await playwright.chromium.launch()
            try:
                yield browser
            finally:
                await browser.close()
    finally:
        if tree:
            tree.terminate(force=True)
        if frontend:
            await asyncio.to_thread(frontend.wait, 10)
        if server:
            server.should_exit = True
        if server_task:
            await asyncio.wait_for(server_task, 10)
        await get_client().drop_database(settings.MONGODB_DB_NAME)
        await disconnect_db()


async def test_all_nine_logins_role_interfaces_and_boundaries(role_browser):
    for role, prefix, home in [
        ("admin", "aerodactyl", "/admin"),
        ("mentor", "mosasaur", "/mentor"),
        ("student", "stegosaur", "/workspace"),
    ]:
        for i in range(1, 4):
            context = await role_browser.new_context()
            page = await context.new_page()
            errors = []
            page.on("pageerror", lambda error, target=errors: target.append(str(error)))
            try:
                await page.goto(BASE + "/login")
                await page.get_by_label("SRN", exact=True).fill(
                    f"{role}{i}" if i != 2 else f"{role}{i}".upper()
                )
                await page.get_by_label("Password", exact=True).fill(f"{prefix}{i}")
                await page.get_by_role("button", name="Sign In", exact=True).click()
                await expect(page).to_have_url(BASE + home)
                if role == "admin":
                    await expect(
                        page.get_by_role("heading", name="Admin Control Center", exact=True)
                    ).to_be_visible()
                    await expect(
                        page.get_by_role("cell", name="Role Test Team 1", exact=True)
                    ).to_be_visible()
                elif role == "mentor":
                    await expect(
                        page.get_by_text("Team Progress Monitor", exact=True)
                    ).to_be_visible()
                    await expect(
                        page.get_by_role("cell", name=f"Student {i} STUDENT{i}", exact=True)
                    ).to_be_visible()
                    for other in {1, 2, 3} - {i}:
                        await expect(
                            page.get_by_role(
                                "cell", name=f"Student {other} STUDENT{other}", exact=True
                            )
                        ).to_have_count(0)
                else:
                    await expect(
                        page.get_by_role("heading", name="Welcome, Student")
                    ).to_be_visible()
                    await expect(
                        page.get_by_role("heading", name="TIPSC Evaluation", exact=True)
                    ).to_be_visible()
                if i == 1:
                    screenshots = ROOT / ".local" / "role-ui-check"
                    screenshots.mkdir(parents=True, exist_ok=True)
                    await page.screenshot(
                        path=str(screenshots / f"{role}.png"), full_page=True, animations="disabled"
                    )
                if role == "mentor":
                    await expect(page.get_by_text("Not Started", exact=True)).to_be_visible()
                if role == "student":
                    await expect(
                        page.get_by_role("button", name="Archive Session", exact=True)
                    ).to_be_disabled()
                # Tokens, restored identity and actual API permissions must agree with the interface.
                profile = await page.evaluate("""async () => {
                    const {apiRequest} = await import('/src/services/apiClient.ts');
                    return apiRequest('/auth/me');
                }""")
                assert profile["role"] == role
                await page.reload()
                await expect(page).to_have_url(BASE + home)
                for blocked in {
                    "admin": ["/mentor", "/workspace", "/quickstart"],
                    "mentor": ["/admin", "/workspace", "/quickstart"],
                    "student": ["/admin", "/mentor"],
                }[role]:
                    await page.goto(BASE + blocked)
                    await expect(page).to_have_url(BASE + home)
                endpoint = "/admin/metrics" if role != "admin" else "/mentor/teams"
                denied = await page.evaluate(
                    """async (endpoint) => fetch('/api/v1' + endpoint, {headers: {
                    Authorization: 'Bearer ' + localStorage.getItem('agis_access_token')
                }}).then(response => response.status)""",
                    endpoint,
                )
                assert denied == 403
                await page.goto(BASE)
                if role in ("admin", "mentor"):
                    await expect(
                        page.get_by_role("link", name=role.title() + " Dashboard", exact=True).first
                    ).to_have_attribute("href", home)
                    await expect(page.locator("#quickstart")).to_have_count(0)
                    await expect(
                        page.get_by_role("link", name="Quickstart", exact=True)
                    ).to_have_count(0)
                else:
                    await page.get_by_role("link", name="Quickstart", exact=True).click()
                    await expect(page).to_have_url(BASE + "/quickstart")
                    await expect(
                        page.get_by_role("heading", name="Quickstart Evaluation", exact=True)
                    ).to_be_visible()
                await page.goto(BASE + home)
                await page.get_by_role("button", name="Logout", exact=True).first.click()
                await expect(page).to_have_url(BASE + "/login")
                assert not await page.evaluate("localStorage.getItem('agis_access_token')")
                assert not errors, errors
                print(
                    f"{role}{i}: login, role UI, reload, route/API restrictions, navigation and logout passed"
                )
            finally:
                await context.close()


async def test_empty_session_lookup_is_successful_and_not_duplicated(role_browser):
    context = await role_browser.new_context()
    page = await context.new_page()
    lookups = []
    page.on(
        "response",
        lambda response: lookups.append(response) if "/sessions/user/" in response.url else None,
    )
    try:
        await page.goto(BASE + "/login")
        await page.get_by_label("SRN", exact=True).fill("student1")
        await page.get_by_label("Password", exact=True).fill("stegosaur1")
        await page.get_by_role("button", name="Sign In", exact=True).click()
        await expect(page).to_have_url(BASE + "/workspace")
        await page.wait_for_load_state("networkidle")
        assert len(lookups) == 1
        assert lookups[0].status == 200
        assert (await lookups[0].json())["data"] is None
        lookups.clear()
        await page.reload()
        await expect(page.get_by_role("heading", name="Welcome, Student")).to_be_visible()
        await page.wait_for_load_state("networkidle")
        assert len(lookups) == 1
        assert lookups[0].status == 200
    finally:
        await context.close()


async def test_admin_theme_across_tabs_and_dialogs(role_browser):
    context = await role_browser.new_context(viewport={"width": 1440, "height": 1000})
    page = await context.new_page()
    screenshots = ROOT / ".local" / "admin-theme-check"
    screenshots.mkdir(parents=True, exist_ok=True)
    try:
        await page.goto(BASE + "/login")
        await page.get_by_label("SRN", exact=True).fill("admin1")
        await page.get_by_label("Password", exact=True).fill("aerodactyl1")
        await page.get_by_role("button", name="Sign In", exact=True).click()
        await expect(page.get_by_role("cell", name="Role Test Team 1", exact=True)).to_be_visible()
        for theme in ["light", "dark"]:
            if theme == "dark":
                await page.get_by_role("button", name="Switch to dark mode", exact=True).click()
                await expect(page.locator("html")).to_have_class("dark")
            for tab in ["Teams", "Advisors", "API Endpoints"]:
                await page.get_by_role("button", name=tab, exact=True).click()
                await expect(page.get_by_role("button", name=tab, exact=True)).to_have_attribute(
                    "aria-pressed", "true"
                )
                await page.wait_for_function("""() => {
                    const selected = document.querySelector('button[aria-pressed="true"]');
                    const heading = document.querySelector('h1');
                    return selected && heading && getComputedStyle(selected).color === getComputedStyle(heading).color;
                }""")
                await page.screenshot(
                    path=str(screenshots / f"{theme}-{tab.replace(' ', '-')}.png"), full_page=True
                )
                if theme == "dark":
                    for locator in (
                        [page.get_by_role("banner"), page.locator("table tbody tr").first]
                        if tab != "API Endpoints"
                        else [page.get_by_role("banner")]
                    ):
                        assert await locator.evaluate(
                            "element => getComputedStyle(element).backgroundColor"
                        ) not in ["rgb(255, 255, 255)", "rgb(248, 250, 252)"]
                if tab == "Teams":
                    buttons = ["Add Team"]
                elif tab == "Advisors":
                    buttons = ["Add Faculty Mentor", "Add External Reviewer"]
                else:
                    buttons = []
                for button in buttons:
                    await page.get_by_role("button", name=button, exact=True).click()
                    dialog = page.get_by_role("dialog")
                    await expect(dialog).to_be_visible()
                    if theme == "dark":
                        assert (
                            await dialog.evaluate(
                                "element => getComputedStyle(element).backgroundColor"
                            )
                            == "rgb(0, 0, 0)"
                        )
                    await page.screenshot(
                        path=str(screenshots / f"{theme}-{button.replace(' ', '-')}.png"),
                        full_page=True,
                        animations="disabled",
                    )
                    await page.keyboard.press("Escape")
                    await expect(dialog).to_have_count(0)
        await page.reload()
        await expect(page.locator("html")).to_have_class("dark")
        await expect(
            page.get_by_role("heading", name="Admin Control Center", exact=True)
        ).to_be_visible()
        await page.get_by_role("button", name="Switch to light mode", exact=True).click()
        await expect(page.locator("html")).not_to_have_class("dark")
    finally:
        await context.close()
