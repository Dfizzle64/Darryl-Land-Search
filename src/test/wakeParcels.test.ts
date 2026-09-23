import { describe, expect, it } from "vitest";
import { parcelAppraiserUrl } from "../lib/format";
import { wakeJurisdictionLabel, wakeZoningLabel } from "../lib/wakeParcels";

describe("Wake County parcel labels", () => {
  it("names planning jurisdictions without inventing a zoning designation", () => {
    expect(wakeJurisdictionLabel("RA")).toBe("Raleigh");
    expect(wakeJurisdictionLabel("wc")).toBe("Wake County");
    expect(wakeJurisdictionLabel("ZZ")).toBeNull();
    expect(wakeZoningLabel("CX-3", "RA")).toBe("Raleigh · CX-3");
    expect(wakeZoningLabel("R-40", "WC")).toBe("Wake County · R-40");
    expect(wakeZoningLabel(null, "RO")).toBeNull();
  });

  it("links the Wake real estate account by REID and does not fall through to Orange County", () => {
    const account = parcelAppraiserUrl({
      parcelId: "0695320153",
      countyFips: "37183",
      appraiserUrl: "https://services.wakegov.com/realestate/Account.asp?id=0022383",
    });
    expect(account.href).toBe("https://services.wakegov.com/realestate/Account.asp?id=0022383");
    expect(account.label).toBe("Open Wake County real estate account");
    expect(account.href).not.toContain("ocpa");

    const search = parcelAppraiserUrl({ parcelId: "0695320153", countyFips: "37183" });
    expect(search.href).toBe("https://services.wakegov.com/realestate/");
    expect(search.label).toBe("Open Wake County real estate search");
  });
});
