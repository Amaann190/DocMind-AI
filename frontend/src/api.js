export const storageKey = "docmind-react-preferences";
export async function api(path, options = {}) {
  const headers = { "X-DocMind-Client": "react", ...options.headers };
  if (options.body && !(options.body instanceof FormData))
    headers["Content-Type"] = "application/json";
  const response = await fetch("/api" + path, { ...options, headers });
  if (!response.ok) {
    let detail;
    try {
      detail = (await response.json()).detail;
    } catch {
      detail = response.statusText;
    }
    throw new Error(
      typeof detail === "string"
        ? detail
        : "Check your settings and try again.",
    );
  }
  return response.json();
}
export function storePreferences(settings) {
  const { api_key, r2r_key, ...safe } = settings;
  try {
    localStorage.setItem(storageKey, JSON.stringify(safe));
  } catch {
    /* Session still works without browser storage. */
  }
}
