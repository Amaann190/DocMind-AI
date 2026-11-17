import { useEffect, useState } from "react";

export const THEME_KEY = "docmind-theme";

/** Light/dark theme, applied to <html> and remembered when storage allows. */
export function useTheme() {
  const [theme, setTheme] = useState(
    () => document.documentElement.dataset.theme || "light",
  );
  useEffect(() => {
    document.documentElement.dataset.theme = theme;
    document.documentElement.style.colorScheme = theme;
    const meta = document.querySelector('meta[name="theme-color"]');
    if (meta) meta.content = theme === "dark" ? "#171c19" : "#f7f6f2";
  }, [theme]);
  function toggleTheme() {
    const next = theme === "dark" ? "light" : "dark";
    setTheme(next);
    try {
      localStorage.setItem(THEME_KEY, next);
    } catch {
      // Storage can be unavailable (private mode); the theme still applies.
    }
  }
  return { theme, setTheme, toggleTheme };
}
