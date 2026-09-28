import { readFileSync } from "node:fs";
import { describe, expect, it } from "vitest";

describe("company logo", () => {
  it("uses a trimmed Catalyst mark with the company name as alt text", () => {
    const logo = readFileSync(new URL("../components/CompanyLogo.tsx", import.meta.url), "utf8");
    expect(logo).toContain('alt="Catalyst Development Partners"');
    expect(logo).toContain('src="/catalyst-logo.webp"');
    expect(logo).toContain("h-11");
    expect(logo).toContain("md:h-12");

    const shell = readFileSync(new URL("../components/AppShell.tsx", import.meta.url), "utf8");
    const header = shell.slice(shell.indexOf("<header"), shell.indexOf("</header>"));
    expect(header.indexOf("<CompanyLogo")).toBeGreaterThan(-1);
    expect(header.indexOf("<CompanyLogo")).toBeLessThan(header.indexOf("<h1"));

    const map = readFileSync(new URL("../components/SiteMap.tsx", import.meta.url), "utf8");
    expect(map).not.toContain("CompanyLogo");
    expect(map).not.toContain("bottom-[6.75rem]");
    const cluster = map.indexOf("data-map-zoom-readout");
    const clusterClass = map.slice(map.lastIndexOf("className=", cluster), cluster);
    expect(clusterClass).toContain("bottom-4");
    expect(map).toContain("absolute bottom-4 left-3");

    const file = readFileSync(new URL("../../public/catalyst-logo.webp", import.meta.url));
    expect(file.subarray(0, 4).toString()).toBe("RIFF");
    expect(file.subarray(8, 12).toString()).toBe("WEBP");
    expect(file.length).toBeGreaterThan(1_000);
    expect(file.length).toBeLessThan(40_000);
    const bits = file.readUInt32LE(21);
    const width = (bits & 0x3fff) + 1;
    const height = ((bits >> 14) & 0x3fff) + 1;
    expect(width).toBe(110);
    expect(height).toBe(112);
  });
});