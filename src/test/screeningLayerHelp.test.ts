import { describe, expect, it } from "vitest";
import { screeningLayerNotes } from "../lib/screeningLayerHelp";

const charlotte = {
  market: "Charlotte",
  county: null,
  state: null,
  states: ["North Carolina", "South Carolina"],
};

describe("screening layer notes follow the selected market", () => {
  it("keeps Charlotte on North Carolina and Mecklenburg sources", () => {
    const notes = screeningLayerNotes(charlotte);
    const blob = Object.values(notes).join(" ");
    expect(blob).not.toMatch(/Orange County|OCPS|Know Your Schools|Florida/);
    expect(notes.schools).toMatch(/CMS/);
    expect(notes.schools).toMatch(/NCDPI/);
    expect(notes.water).toMatch(/Charlotte Water/);
    expect(notes.water).not.toMatch(/Orange/);
    expect(notes.designatedOz).toBe("Not available for this market yet.");
    expect(notes.flood).toMatch(/FEMA/);
    expect(notes.flood).not.toMatch(/Orange|Charlotte/);
  });

  it("drops Mecklenburg copy when a South Carolina county in the Charlotte shed is selected", () => {
    const notes = screeningLayerNotes({
      ...charlotte,
      county: "York",
      state: "South Carolina",
    });
    const blob = Object.values(notes).join(" ");
    expect(blob).not.toMatch(/Orange County|OCPS|Know Your Schools|CMS|NCDPI|Mecklenburg/);
    expect(notes.schools).toMatch(/South Carolina/);
    expect(notes.water).toBe("Not available for this county yet.");
  });

  it("uses Florida notes on Orlando and hides Charlotte sources", () => {
    const notes = screeningLayerNotes({
      market: "Orlando",
      county: null,
      state: null,
      states: ["Florida"],
    });
    const blob = Object.values(notes).join(" ");
    expect(blob).not.toMatch(/CMS|Mecklenburg|NCDPI|Charlotte Water/);
    expect(notes.schools).toMatch(/OCPS/);
    expect(notes.schools).toMatch(/Know Your Schools/);
    expect(notes.water).toMatch(/Orange County/);
    expect(notes.designatedOz).toMatch(/Orange County/);
    expect(notes.designatedOz).not.toMatch(/2027 designation$/);
  });

  it("says water and schools are unavailable where this app has no layer", () => {
    const atlanta = screeningLayerNotes({
      market: "Atlanta",
      county: null,
      state: null,
      states: ["Georgia"],
    });
    expect(atlanta.water).toBe("Not available for this market yet.");
    expect(atlanta.sewer).toBe("Not available for this market yet.");
    expect(atlanta.schools).toMatch(/Georgia school report card/);
    expect(atlanta.schools).not.toMatch(/Orange|OCPS|CMS|Charlotte/);
    expect(atlanta.power).toMatch(/HIFLD/);
    expect(atlanta.power).not.toMatch(/Mecklenburg|Orange County/);

    const arkansas = screeningLayerNotes({
      market: "Memphis",
      county: "Crittenden",
      state: "Arkansas",
      states: ["Tennessee", "Arkansas", "Mississippi"],
    });
    expect(arkansas.schools).toBe("Not available for this county yet.");
    expect(Object.values(arkansas).join(" ")).not.toMatch(/Orange County|OCPS|Know Your Schools/);
  });
});
