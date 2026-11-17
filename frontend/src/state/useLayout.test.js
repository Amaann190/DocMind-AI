import { describe, expect, it } from "vitest";
import { clampPanelWidths, DEFAULT_PANEL_WIDTHS } from "./useLayout.js";

describe("clampPanelWidths", () => {
  it("falls back to defaults for missing or invalid values", () => {
    expect(clampPanelWidths(null)).toEqual(DEFAULT_PANEL_WIDTHS);
    expect(clampPanelWidths({ left: "wide", right: NaN })).toEqual(DEFAULT_PANEL_WIDTHS);
  });
  it("clamps widths into the supported range", () => {
    expect(clampPanelWidths({ left: 10, right: 9999 })).toEqual({ left: 220, right: 440 });
    expect(clampPanelWidths({ left: 300, right: 300 })).toEqual({ left: 300, right: 300 });
  });
});
