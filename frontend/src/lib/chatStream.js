/**
 * Chat answers stream from POST /api/chat as newline-delimited JSON events:
 *   {type: "token", text}           a piece of the answer
 *   {type: "done" | "error", message} the final assistant message
 *   {type: "warning", text}         a non-fatal problem to show the user
 */

/** Messages shown immediately when a question is sent, before any token arrives. */
export function optimisticMessages(messages, text, regenerate) {
  return [
    ...(regenerate ? messages.slice(0, -2) : messages),
    { role: "user", content: text },
    { role: "assistant", content: "", sources: [] },
  ];
}

/** Apply one stream event to the message list; returns a new list. */
export function applyChatEvent(messages, event) {
  if (!messages.length || !event || event.type === "warning") return messages;
  const next = [...messages];
  const last = next.length - 1;
  if (event.type === "token") {
    next[last] = { ...next[last], content: next[last].content + event.text };
  } else if (event.message) {
    next[last] = event.message;
  }
  return next;
}

/** Split buffered text into complete lines; returns [lines, remainder]. */
export function splitLines(buffer) {
  const lines = buffer.split("\n");
  const rest = lines.pop();
  return [lines.filter((line) => line.trim()), rest];
}

/** Read an NDJSON response body and call onEvent for each parsed event. */
export async function readEvents(body, onEvent) {
  const reader = body.getReader();
  const decoder = new TextDecoder();
  let pending = "";
  for (;;) {
    const { done, value } = await reader.read();
    if (done) break;
    pending += decoder.decode(value, { stream: true });
    const [lines, rest] = splitLines(pending);
    pending = rest;
    lines.forEach((line) => onEvent(JSON.parse(line)));
  }
  pending += decoder.decode();
  if (pending.trim()) onEvent(JSON.parse(pending));
}
