import { describe, expect, it } from "vitest";
import { parcelAppraiserUrl, statePostal } from "../lib/format";

describe("parcel appraiser links", () => {
  it("opens Mecklenburg parcels in POLARIS with the pid deep link", () => {
    const linked = parcelAppraiserUrl({
      parcelId: "4661960387",
      countyFips: "37119",
      appraiserUrl: "https://polaris3g.mecklenburgcountync.gov/pid/01113108",
    });
    expect(linked.href).toBe("https://polaris3g.mecklenburgcountync.gov/pid/01113108");
    expect(linked.label).toBe("Open in Mecklenburg POLARIS");
  });

  it("keeps a POLARIS home link when a Mecklenburg pid is missing", () => {
    const linked = parcelAppraiserUrl({
      parcelId: "4661960387",
      countyFips: "37119",
      appraiserUrl: null,
    });
    expect(linked.href).toBe("https://polaris3g.mecklenburgcountync.gov/");
    expect(linked.label).toBe("Open in Mecklenburg POLARIS");
  });

  it("maps county state names to postal abbreviations", () => {
    expect(statePostal("North Carolina")).toBe("NC");
    expect(statePostal("Florida")).toBe("FL");
    expect(statePostal(null)).toBeNull();
  });
});
