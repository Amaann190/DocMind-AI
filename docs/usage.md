# Using DocMind

Open the React website at http://127.0.0.1:8765 after following [setup](setup.md).

1. Open **Settings** and choose the provider, endpoint and installed model names.
2. Use **Add source** to upload files, import a public HTTPS page or public GitHub repository.
3. Wait for a source to show **Ready**, then ask a question.
4. Open a citation to read its supporting passage and available page label.

Source imports add to the current collection. Open a source to retry/reindex,
replace it, or remove it. Failed uploads show their error and remain available
for recovery; a failed replacement preserves the previous working source.
The source library lists failed files too, but only usable sources count as ready.

Use **Stop** to keep a partial answer, or **Regenerate** to replace the latest answer.
Copy responses or export the conversation as Word. The configured answer style
changes response presentation, not source support or factual guarantees.

Chats are saved locally and can be searched, renamed, reopened or deleted.
A short topic title is generated after the first successful answer; manual names
are preserved. New empty drafts stay out of history until you send a message.
All chats share the current source collection. Reopening a chat does not restore
its old files, and a backend restart requires adding sources again.

The header theme toggle supports light/dark mode. Close or reopen either side
panel, drag its desktop edge to resize, and use each panel's own scrollbar.
Keyboard focus on a resize edge supports arrows, Home and End.

Changing embedding/provider configuration clears incompatible source indexes.
Reset clears the current workspace and local history for its session owner.
R2R removal/reset also attempts to delete owned remote files; failed cleanup
retains ownership and blocks queries until cleanup succeeds.
