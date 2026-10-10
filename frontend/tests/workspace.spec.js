import { test, expect } from "@playwright/test";

test("panels close and reopen while workspace stays reachable in short windows", async ({
  page,
}) => {
  await page.setViewportSize({ width: 1280, height: 480 });
  await page.goto("/");
  const navigation = page.getByRole("complementary", {
    name: "Workspace navigation",
  });
  const sources = page.getByRole("complementary", {
    name: "Sources",
    exact: true,
  });
  const profile = page.getByRole("button", { name: /My workspace/ });
  await expect(profile).toBeInViewport();
  const box = await profile.boundingBox();
  expect(box.y + box.height).toBeLessThanOrEqual(480);
  await profile.click();
  await expect(
    page.getByRole("heading", { name: "A workspace that fits." }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Chat", exact: true }).click();
  expect(
    await page
      .locator(".sidebar-scroll")
      .evaluate((el) => el.scrollHeight > el.clientHeight),
  ).toBeTruthy();
  await page.locator(".sidebar-scroll").hover();
  await page.mouse.wheel(0, 700);
  await expect
    .poll(() => page.locator(".sidebar-scroll").evaluate((el) => el.scrollTop))
    .toBeGreaterThan(0);
  await expect(profile).toBeInViewport();
  await page
    .getByRole("button", { name: "Hide navigation", exact: true })
    .click();
  await expect(navigation).toBeHidden();
  await expect
    .poll(() =>
      page.locator("main").evaluate((el) => el.getBoundingClientRect().x),
    )
    .toBe(0);
  await page.getByRole("button", { name: "Toggle navigation" }).click();
  await expect(navigation).toBeVisible();
  await page.getByRole("button", { name: "Close source panel" }).click();
  await expect(sources).toBeHidden();
  await page.getByRole("button", { name: "Show source panel" }).click();
  await expect(sources).toBeVisible();
  expect(
    await sources.evaluate((el) => el.scrollHeight > el.clientHeight),
  ).toBeTruthy();
  await sources.hover();
  await page.mouse.wheel(0, 700);
  await expect
    .poll(() => sources.evaluate((el) => el.scrollTop))
    .toBeGreaterThan(0);
  await expect(
    page.getByRole("button", { name: "Close source panel" }),
  ).toBeInViewport();
  await expect(
    page.getByRole("textbox", { name: "Ask DocMind" }),
  ).toBeInViewport();
  await page.screenshot({
    path: "../output/react-panels-short.png",
    animations: "disabled",
  });

  await page.setViewportSize({ width: 390, height: 500 });
  await page.getByRole("button", { name: "Toggle navigation" }).click();
  await expect(profile).toBeInViewport();
  await profile.click();
  await expect(
    page.getByRole("heading", { name: "A workspace that fits." }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Toggle navigation" }).click();
  await page.getByRole("button", { name: "Chat", exact: true }).click();
  await page.getByRole("button", { name: "Show source panel" }).click();
  await expect(sources).toBeVisible();
  await page.getByRole("button", { name: "Close source panel" }).click();
  await expect(sources).toBeHidden();
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBeTruthy();
});

test("workspace, settings persistence, source modal and responsive layout", async ({
  page,
}) => {
  const errors = [];
  page.on("pageerror", (error) => errors.push(error.message));
  await page.goto("/");
  await expect(
    page.getByRole("heading", {
      name: "A clearer view of everything you know.",
    }),
  ).toBeVisible();
  await page.screenshot({
    path: "../output/react-desktop.png",
    fullPage: true,
  });
  await page.getByRole("button", { name: "Add your first source" }).click();
  await expect(page.getByRole("dialog")).toBeVisible();
  await page.getByRole("button", { name: "Website", exact: true }).click();
  await expect(
    page.getByPlaceholder("https://example.com/article"),
  ).toBeVisible();
  await page.getByRole("button", { name: "GitHub", exact: true }).click();
  await expect(page.getByPlaceholder("owner/repository")).toBeVisible();
  await page.keyboard.press("Escape");
  await page.getByRole("button", { name: "Settings", exact: true }).click();
  await page.getByRole("button", { name: "Detailed", exact: true }).click();
  await page.getByRole("button", { name: "Save preferences" }).click();
  await expect
    .poll(() =>
      page.evaluate(
        () =>
          JSON.parse(localStorage.getItem("docmind-react-preferences") || "{}")
            .style,
      ),
    )
    .toBe("Detailed");
  await page.reload();
  await page.getByRole("button", { name: "Settings", exact: true }).click();
  await expect(
    page.getByRole("button", { name: "Detailed", exact: true }),
  ).toHaveClass("chosen");
  await page.screenshot({
    path: "../output/react-settings.png",
    fullPage: true,
  });
  await page.getByRole("button", { name: "Chat", exact: true }).click();
  await page.setViewportSize({ width: 390, height: 844 });
  await expect(
    page.getByRole("navigation", { name: "Main navigation" }),
  ).toBeHidden();
  await expect(
    page.getByRole("textbox", { name: "Ask DocMind" }),
  ).toBeVisible();
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth,
    ),
  ).toBeTruthy();
  await page.screenshot({
    path: "../output/react-mobile.png",
    fullPage: true,
    animations: "disabled",
  });
  await page.getByRole("button", { name: "Toggle navigation" }).click();
  await expect(
    page.getByRole("navigation", { name: "Main navigation" }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Settings", exact: true }).click();
  await expect(
    page.getByRole("heading", { name: "A workspace that fits." }),
  ).toBeVisible();
  expect(errors).toEqual([]);
});

test("live upload, grounded answer, export and source removal", async ({
  page,
}) => {
  test.skip(
    !process.env.DOCMIND_LIVE,
    "Set DOCMIND_LIVE=1 with local Ollama models installed.",
  );
  test.setTimeout(300000);
  await page.goto("/");
  await page.getByRole("button", { name: "Add your first source" }).click();
  await page
    .getByRole("dialog")
    .locator("input[type=file]")
    .setInputFiles({
      name: "demo-brief.txt",
      mimeType: "text/plain",
      buffer: Buffer.from(
        "Aurora project brief. The approved budget is $24,000. The launch date is November 12, 2026. Maya Chen leads the design team.",
      ),
    });
  await page.getByRole("button", { name: "Add to workspace" }).click();
  await expect(
    page.getByRole("heading", { name: "Your knowledge is ready." }),
  ).toBeVisible({ timeout: 120000 });
  await page
    .getByRole("textbox", { name: "Ask DocMind" })
    .fill("What is the approved project budget?");
  await page.getByRole("button", { name: "Send message" }).click();
  await expect(
    page.getByRole("button", { name: "Export", exact: true }),
  ).toBeEnabled({ timeout: 180000 });
  await expect(page.locator(".message.assistant")).toContainText("24,000");
  await expect(page.locator(".citation-list button").first()).toBeVisible();
  await page.screenshot({
    path: "../output/react-live-answer.png",
    fullPage: true,
  });
  const download = page.waitForEvent("download");
  await page.getByRole("button", { name: "Export", exact: true }).click();
  expect((await download).suggestedFilename()).toBe(
    "DocMind-conversation.docx",
  );
  await page
    .getByRole("button", { name: "Add source", exact: true })
    .first()
    .click();
  await page
    .getByRole("dialog")
    .locator("input[type=file]")
    .setInputFiles({
      name: "second.txt",
      mimeType: "text/plain",
      buffer: Buffer.from("The second project is named Meridian."),
    });
  await page.getByRole("button", { name: "Add to workspace" }).click();
  const sourceList = page.locator(".source-list");
  await expect(sourceList.getByRole("button")).toHaveCount(2, {
    timeout: 60000,
  });
  await sourceList.getByRole("button", { name: /second.txt/ }).click();
  await page
    .getByRole("button", { name: "Reindex source", exact: true })
    .click();
  await expect(page.getByRole("button", { name: "Replace file" })).toBeEnabled({
    timeout: 60000,
  });
  await page.getByLabel("Replacement file").setInputFiles({
    name: "updated.txt",
    mimeType: "text/plain",
    buffer: Buffer.from("The updated project is named Solstice."),
  });
  await expect(
    page.getByRole("dialog").getByRole("heading", { name: "updated.txt" }),
  ).toBeVisible({ timeout: 60000 });
  await page
    .getByRole("button", { name: "Remove source", exact: true })
    .click();
  await page.getByRole("button", { name: "Confirm removal" }).click();
  await expect(sourceList.getByRole("button")).toHaveCount(1, {
    timeout: 60000,
  });
  await expect(sourceList).toContainText("demo-brief.txt");
  await page.getByRole("button", { name: "Remove all sources" }).click();
  await page.getByRole("button", { name: "Confirm removal" }).click();
  await expect(
    page.getByRole("heading", { name: "A home for your knowledge" }),
  ).toBeVisible();
  const state = await page.request.get("/api/state").then((r) => r.json());
  expect(state.has_index).toBe(false);
});

test("streamed answer, source preview and export controls", async ({
  page,
}) => {
  await page.emulateMedia({ colorScheme: "dark" });
  // The real API is covered separately; this test checks streamed UI rendering deterministically.
  await page.route("**/api/chat", async (route) => {
    const message = {
      role: "assistant",
      content: "The launch is November 12, 2026 [1].",
      sources: [
        {
          number: 1,
          name: "Project brief.txt",
          text: "Launch: November 12, 2026.",
          page: "7",
        },
      ],
    };
    await page.route("**/api/state", (route) =>
      route.fulfill({
        json: {
          ...initial,
          messages: [{ role: "user", content: "When is the launch?" }, message],
        },
      }),
    );
    await route.fulfill({
      contentType: "application/x-ndjson",
      body:
        JSON.stringify({ type: "token", text: message.content }) +
        "\n" +
        JSON.stringify({ type: "done", message }) +
        "\n",
    });
  });
  let initial;
  await page.goto("/");
  await expect(
    page.getByRole("textbox", { name: "Ask DocMind" }),
  ).toBeVisible();
  initial = await page.request.get("/api/state").then((r) => r.json());
  await page
    .getByRole("textbox", { name: "Ask DocMind" })
    .fill("When is the launch?");
  await page.getByRole("button", { name: "Send message" }).click();
  await expect(
    page.getByText("The launch is November 12, 2026 [1].", { exact: true }),
  ).toBeVisible();
  await page.getByRole("button", { name: /1 Project brief.txt/ }).click();
  await expect(page.getByRole("dialog")).toContainText(
    "Launch: November 12, 2026.",
  );
  await expect(page.getByRole("dialog").locator("mark")).toHaveText(
    "Launch: November 12, 2026.",
  );
  await expect(page.getByRole("dialog")).toContainText("Page 7");
  await page.screenshot({ path: "../output/react-dark-citation.png" });
  await page.keyboard.press("Escape");
  await expect(
    page.getByRole("button", { name: "Export", exact: true }),
  ).toBeEnabled();
  await page.screenshot({ path: "../output/react-chat.png", fullPage: true });
});

test("dark theme follows the system initially, persists a choice and covers every screen", async ({
  page,
}) => {
  const errors = [];
  page.on("pageerror", (error) => errors.push(error.message));
  await page.emulateMedia({ colorScheme: "dark" });
  await page.goto("/");
  const root = page.locator("html");
  await expect(root).toHaveAttribute("data-theme", "dark");
  await expect(page.locator(".composer")).toHaveCSS(
    "background-color",
    "rgb(32, 40, 34)",
  );
  await page
    .getByRole("textbox", { name: "Ask DocMind" })
    .fill("Keep this draft");
  await page.getByRole("button", { name: "Switch to light mode" }).click();
  await expect(root).toHaveAttribute("data-theme", "light");
  await expect(page.getByRole("textbox", { name: "Ask DocMind" })).toHaveValue(
    "Keep this draft",
  );
  await page.reload();
  await expect(root).toHaveAttribute("data-theme", "light");
  const toggle = page.getByRole("button", { name: "Switch to dark mode" });
  await toggle.focus();
  await page.keyboard.press("Enter");
  await expect(root).toHaveAttribute("data-theme", "dark");
  await page.reload();
  await expect(root).toHaveAttribute("data-theme", "dark");
  await expect(
    page.getByRole("textbox", { name: "Ask DocMind" }),
  ).toBeVisible();
  await page.screenshot({ path: "../output/react-dark-desktop.png" });
  await page.getByRole("button", { name: "Settings", exact: true }).click();
  await expect(page.locator(".settings-section").first()).toHaveCSS(
    "background-color",
    "rgb(32, 40, 34)",
  );
  await expect(page.locator(".field input").first()).toHaveCSS(
    "color",
    "rgb(232, 236, 227)",
  );
  await page.screenshot({ path: "../output/react-dark-settings.png" });
  await page.getByRole("button", { name: /Source library/ }).click();
  await expect(
    page.getByRole("heading", { name: "Source library." }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Add source", exact: true }).click();
  await expect(page.getByRole("dialog")).toHaveCSS(
    "background-color",
    "rgb(32, 40, 34)",
  );
  await page.screenshot({ path: "../output/react-dark-import.png" });
  await page.keyboard.press("Escape");
  await page.getByRole("button", { name: "Chat", exact: true }).click();
  await page.setViewportSize({ width: 390, height: 844 });
  await expect(
    page.getByRole("button", { name: "Switch to light mode" }),
  ).toBeInViewport();
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBeTruthy();
  await page.screenshot({ path: "../output/react-dark-mobile.png" });
  expect(errors).toEqual([]);
});

test("theme switching still works when browser storage is unavailable", async ({
  page,
}) => {
  await page.addInitScript(() => {
    Storage.prototype.getItem = () => {
      throw new DOMException("Storage blocked", "SecurityError");
    };
    Storage.prototype.setItem = () => {
      throw new DOMException("Storage blocked", "SecurityError");
    };
  });
  await page.emulateMedia({ colorScheme: "dark" });
  await page.goto("/");
  await expect(page.locator("html")).toHaveAttribute("data-theme", "dark");
  await page.getByRole("button", { name: "Switch to light mode" }).click();
  await expect(page.locator("html")).toHaveAttribute("data-theme", "light");
  await expect(
    page.getByRole("textbox", { name: "Ask DocMind" }),
  ).toBeVisible();
});

test("saved conversations rename, search, reopen and delete; panel widths persist", async ({
  page,
}) => {
  await page.goto("/");
  await page
    .getByRole("button", { name: "Rename New conversation", exact: true })
    .click();
  await page.getByLabel("Conversation name").fill("Research notes");
  await page.getByRole("button", { name: "Save name", exact: true }).click();
  await expect(page.getByRole("dialog")).toBeHidden();
  await page
    .getByRole("button", { name: /New conversation/ })
    .first()
    .click();
  await expect(page.locator(".conversation-row")).toHaveCount(2);
  await page
    .getByRole("textbox", { name: "Search conversations" })
    .fill("Research");
  await expect(page.locator(".conversation-row")).toHaveCount(1);
  await page
    .getByRole("button", { name: "Research notes", exact: true })
    .click();
  await expect(
    page.getByRole("button", { name: "Research notes", exact: true }),
  ).toHaveAttribute("aria-current", "page");
  await page.reload();
  await expect(
    page.getByRole("button", { name: "Research notes", exact: true }),
  ).toHaveAttribute("aria-current", "page");
  const left = page.getByRole("separator", { name: "Resize navigation panel" });
  const right = page.getByRole("separator", { name: "Resize sources panel" });
  await left.focus();
  await page.keyboard.press("ArrowRight");
  await expect(left).toHaveAttribute("aria-valuenow", "254");
  const handle = await right.boundingBox();
  await page.mouse.move(handle.x + 3, handle.y + 150);
  await page.mouse.down();
  await page.mouse.move(handle.x - 47, handle.y + 150);
  await page.mouse.up();
  await expect(right).toHaveAttribute("aria-valuenow", "324");
  await page.reload();
  await expect(left).toHaveAttribute("aria-valuenow", "254");
  await expect(right).toHaveAttribute("aria-valuenow", "324");
  await page
    .getByRole("button", { name: "Delete Research notes", exact: true })
    .click();
  await page.getByRole("button", { name: "Confirm deletion" }).click();
  await expect(
    page.getByRole("button", { name: "Research notes", exact: true }),
  ).toHaveCount(0);
});

test("stop and regenerate controls preserve a single conversation turn", async ({
  page,
}) => {
  await page.goto("/");
  await expect(
    page.getByRole("textbox", { name: "Ask DocMind" }),
  ).toBeVisible();
  const initial = await page.request.get("/api/state").then((r) => r.json());
  let finish;
  const stopped = new Promise((resolve) => {
    finish = resolve;
  });
  let count = 0;
  await page.route("**/api/chat", async (route) => {
    const request = route.request().postDataJSON();
    if (count++ === 0) await stopped;
    else expect(request.regenerate).toBe(true);
    const message = {
      role: "assistant",
      content: count === 1 ? "Partial answer" : "Regenerated answer",
      stopped: count === 1,
      sources: [],
    };
    await page.route("**/api/state", (r) =>
      r.fulfill({
        json: {
          ...initial,
          messages: [{ role: "user", content: "Explain this" }, message],
        },
      }),
    );
    await route.fulfill({
      contentType: "application/x-ndjson",
      body: JSON.stringify({ type: "done", message }) + "\n",
    });
  });
  await page.route("**/api/chat/stop", async (route) => {
    await route.fulfill({ json: { stopping: true } });
    finish();
  });
  await page.getByRole("textbox", { name: "Ask DocMind" }).fill("Explain this");
  await page.getByRole("button", { name: "Send message" }).click();
  await page.getByRole("button", { name: "Stop generating" }).click();
  await expect(page.getByText("Stopped · Partial answer saved")).toBeVisible();
  await page.getByRole("button", { name: "Regenerate answer" }).click();
  await expect(
    page.getByText("Regenerated answer", { exact: true }),
  ).toBeVisible();
  await expect(page.locator("article.message.user")).toHaveCount(1);
});
