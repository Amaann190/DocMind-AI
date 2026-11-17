import { useEffect, useState } from "react";

export const PANEL_WIDTHS_KEY = "docmind-panel-widths";
export const DEFAULT_PANEL_WIDTHS = { left: 244, right: 274 };

/** Clamp saved panel widths to the ranges the layout supports. */
export function clampPanelWidths(saved) {
  return {
    left: Math.max(220, Math.min(400, Number(saved?.left) || DEFAULT_PANEL_WIDTHS.left)),
    right: Math.max(240, Math.min(440, Number(saved?.right) || DEFAULT_PANEL_WIDTHS.right)),
  };
}

function loadPanelWidths() {
  try {
    return clampPanelWidths(JSON.parse(localStorage.getItem(PANEL_WIDTHS_KEY)));
  } catch {
    return { ...DEFAULT_PANEL_WIDTHS };
  }
}

/** Navigation/sources panel visibility and widths, responsive to the viewport. */
export function useLayout() {
  const [panelWidths, setPanelWidths] = useState(loadPanelWidths);
  const [showSources, setShowSources] = useState(() => window.innerWidth > 980);
  const [showNavigation, setShowNavigation] = useState(true);
  const [mobile, setMobile] = useState(() => window.innerWidth <= 700);
  const [mobileNav, setMobileNav] = useState(false);

  useEffect(() => {
    try {
      localStorage.setItem(PANEL_WIDTHS_KEY, JSON.stringify(panelWidths));
    } catch {
      // Widths are a convenience; ignore unavailable storage.
    }
  }, [panelWidths]);

  useEffect(() => {
    const navigation = window.matchMedia("(max-width: 700px)");
    const sources = window.matchMedia("(max-width: 980px)");
    const updateNavigation = () => {
      setMobile(navigation.matches);
      setMobileNav(false);
    };
    const updateSources = () => setShowSources(!sources.matches);
    navigation.addEventListener("change", updateNavigation);
    sources.addEventListener("change", updateSources);
    return () => {
      navigation.removeEventListener("change", updateNavigation);
      sources.removeEventListener("change", updateSources);
    };
  }, []);

  const navigationVisible = mobile ? mobileNav : showNavigation;
  const toggleNavigation = () =>
    mobile ? setMobileNav(!mobileNav) : setShowNavigation(!showNavigation);

  return {
    panelWidths, setPanelWidths, showSources, setShowSources,
    mobile, setMobileNav, navigationVisible, toggleNavigation,
  };
}
