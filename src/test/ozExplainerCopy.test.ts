import { describe, expect, it } from "vitest";
import { OZ_EXPLAINER_SECTIONS, OZ_EXPLAINER_TAX_NOTE, OZ_EXPLAINER_TITLE } from "../lib/ozExplainerCopy";

describe("OZ 2.0 explainer copy", () => {
  it("keeps the title and section headers", () => {
    expect(OZ_EXPLAINER_TITLE).toBe("How Opportunity Zones 2.0 work");
    expect(OZ_EXPLAINER_SECTIONS.map((section) => section.heading)).toEqual([
      "What makes a tract eligible",
      "How the process works",
      "South Carolina nominations",
      "What the map chips mean",
      "What it means for investors (high level — not tax advice)",
      "Rural vs urban on the eligible list",
      "Disclaimer",
    ]);
  });

  it("does not call map tracts designated or fold MF priority into the explainer", () => {
    const text = JSON.stringify(OZ_EXPLAINER_SECTIONS) + OZ_EXPLAINER_TAX_NOTE;
    expect(text).toContain("Nothing on this map is a certified QOZ");
    expect(text).toContain("Eligible — not designated");
    expect(text).toContain("Governor-nominated / awaiting Treasury");
    expect(text).toContain("Eligible tracts that were not nominated are not shown");
    expect(text).toContain("South Carolina draws the nominated list only");
    expect(text).not.toContain("Other eligible tracts stay");
    expect(text).toContain("September 23, 2026");
    expect(text).toContain("September 22, 2026");
    expect(text).toContain("same GEOIDs");
    expect(text).toContain("not a new list");
    expect(text).toContain("Nomination alone is not a tax benefit");
    expect(text).toContain("Eligible ≠ nominated ≠ certified");
    expect(text).toContain("the state filed that tract with Treasury; still not a certified 2027 QOZ");
    expect(text).toContain(
      "Soft-upgrade only when the state’s official nomination list is public (SC: Commerce Final Recommendations PDF, 112 tracts). Secondary scrapes alone aren’t enough.",
    );
    expect(text).toContain("Designated / QOZ = Treasury certification only — none of our markets yet; target effective Jan 1, 2027.");
    expect(OZ_EXPLAINER_SECTIONS.find((section) => section.heading === "Disclaimer")?.paragraphs?.[0]).toMatch(
      /^Eligible ≠ nominated ≠ certified\./,
    );
    expect(text).toContain("This app does not provide tax advice");
    expect(text.toLowerCase()).not.toContain("mf priority");
    expect(text.toLowerCase()).not.toContain("tier a");
    expect(text).not.toMatch(/these tracts are designated/i);
  });
});