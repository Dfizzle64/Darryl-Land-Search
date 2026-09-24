import { readFileSync } from "node:fs";
import { describe, expect, it } from "vitest";

const appShell = readFileSync(new URL("../components/AppShell.tsx", import.meta.url), "utf8");
const parcelDrawer = readFileSync(new URL("../components/ParcelDrawer.tsx", import.meta.url), "utf8");
const tractDrawer = readFileSync(new URL("../components/TractDrawer.tsx", import.meta.url), "utf8");

describe("desktop map panels", () => {
  it("keeps the ranked list and the selected parcel in separate rails", () => {
    const ranking = appShell.indexOf("data-ranking-panel");
    const selection = appShell.indexOf("data-selection-panel");
    expect(ranking).toBeGreaterThan(0);
    expect(selection).toBeGreaterThan(ranking);

    const rankingRail = appShell.slice(ranking, selection);
    expect(rankingRail).toContain("SitesPanel");
    expect(rankingRail).toContain("TractPanel");
    expect(rankingRail).not.toContain("ParcelDrawer");
    expect(rankingRail).not.toContain("TractDrawer");
    expect(rankingRail).not.toContain('layout="pane"');

    const selectionRail = appShell.slice(selection, appShell.indexOf('className="lg:hidden"'));
    expect(selectionRail).toContain("<ParcelDrawer");
    expect(selectionRail).toContain("<TractDrawer");
    expect(selectionRail).toContain('layout="pane"');
    expect(appShell).toContain("flex-nowrap");
    expect(appShell).not.toContain("flex-[1.35]");
  });

  it("does not turn the mobile sheet into a second desktop column", () => {
    for (const source of [parcelDrawer, tractDrawer]) {
      expect(source).not.toContain("lg:static");
      expect(source).not.toContain("lg:w-[24rem]");
      expect(source).toContain('pane ? "drawer-scroll h-full overflow-y-auto bg-ink-900 p-5"');
    }
  });
});
