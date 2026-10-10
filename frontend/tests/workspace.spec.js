import { test, expect } from "@playwright/test";

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
  await page.getByRole("button", { name: "1 Project brief.txt" }).click();
  await expect(page.getByRole("dialog")).toContainText(
    "Launch: November 12, 2026.",
  );
  await page.keyboard.press("Escape");
  await expect(
    page.getByRole("button", { name: "Export", exact: true }),
  ).toBeEnabled();
  await page.screenshot({ path: "../output/react-chat.png", fullPage: true });
});
