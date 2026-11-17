import { describe, expect, it } from "vitest";
import { applyChatEvent, optimisticMessages, readEvents, splitLines } from "./chatStream.js";

const user = { role: "user", content: "Q" };
const answer = { role: "assistant", content: "A", sources: [] };

describe("optimisticMessages", () => {
  it("appends the question and an empty answer", () => {
    expect(optimisticMessages([], "Hi", false)).toEqual([
      { role: "user", content: "Hi" },
      { role: "assistant", content: "", sources: [] },
    ]);
  });
  it("replaces the last turn when regenerating", () => {
    const result = optimisticMessages([user, answer], "Q", true);
    expect(result).toHaveLength(2);
    expect(result[1].content).toBe("");
  });
});

describe("applyChatEvent", () => {
  const start = [user, { role: "assistant", content: "", sources: [] }];
  it("appends tokens to the last message without mutating input", () => {
    const once = applyChatEvent(start, { type: "token", text: "Hel" });
    const twice = applyChatEvent(once, { type: "token", text: "lo" });
    expect(twice[1].content).toBe("Hello");
    expect(start[1].content).toBe("");
  });
  it("replaces the last message with the final message", () => {
    const final = { role: "assistant", content: "Done", sources: [{ number: 1 }] };
    expect(applyChatEvent(start, { type: "done", message: final })[1]).toBe(final);
  });
  it("ignores warnings and empty lists", () => {
    expect(applyChatEvent(start, { type: "warning", text: "x" })).toBe(start);
    expect(applyChatEvent([], { type: "token", text: "x" })).toEqual([]);
  });
});

describe("stream parsing", () => {
  it("keeps an incomplete trailing line buffered", () => {
    expect(splitLines('{"a":1}\n\n{"b"')).toEqual([['{"a":1}'], '{"b"']);
  });
  it("parses events split across chunks", async () => {
    const encoder = new TextEncoder();
    const chunks = ['{"type":"tok', 'en","text":"Hi"}\n{"type":"done",', '"message":{"content":"Hi"}}'];
    const body = new ReadableStream({
      start(controller) {
        chunks.forEach((c) => controller.enqueue(encoder.encode(c)));
        controller.close();
      },
    });
    const events = [];
    await readEvents(body, (event) => events.push(event));
    expect(events).toEqual([
      { type: "token", text: "Hi" },
      { type: "done", message: { content: "Hi" } },
    ]);
  });
});
