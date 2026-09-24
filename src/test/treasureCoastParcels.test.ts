import { describe, expect, it } from "vitest";
import { parcelAppraiserUrl } from "../lib/format";
import {
  fluEmptyMessage,
  treasureCoastAppraiserLabel,
  zoningEmptyMessage,
  zoningLine,
} from "../lib/treasureCoast";

describe("Treasure Coast parcel labels", () => {
  it("names each county appraiser and does not send Okeechobee to Ocoee", () => {
    expect(treasureCoastAppraiserLabel("12093")).toMatch(/Okeechobee/);
    expect(treasureCoastAppraiserLabel("12093")).not.toMatch(/Ocoee/);
    expect(parcelAppraiserUrl({ parcelId: "1", countyFips: "12061" }).label).toMatch(/Indian River/);
    expect(parcelAppraiserUrl({ parcelId: "1", countyFips: "12061", appraiserUrl: "https://www.ircpa.org/x" }).href).toBe(
      "https://www.ircpa.org/x",
    );
    expect(parcelAppraiserUrl({ parcelId: "1", countyFips: "12009" }).href).toContain("bcpao.us");
    expect(parcelAppraiserUrl({ parcelId: "1", countyFips: "12085" }).label).toMatch(/Martin/);
  });

  it("shows the municipality on the zoning line and does not call eligible tracts designated", () => {
    expect(zoningLine({ countyFips: "12061", zoningCode: "RS-1", jurisdictionCode: "Sebastian" })).toBe(
      "RS-1 · Sebastian",
    );
    expect(zoningLine({ countyFips: "12095", zoningCode: "ORL-R-3", jurisdictionCode: "ORL" })).toBe("ORL-R-3");
    expect(zoningEmptyMessage("12061", "Fellsmere")).toMatch(/Fellsmere/);
    expect(zoningEmptyMessage("12061", "Fellsmere")).toMatch(/not copied/);
    expect(zoningEmptyMessage("12009", "Melbourne")).not.toMatch(/Australia/);
    expect(zoningEmptyMessage("12093", "Okeechobee County")).toMatch(/not City of Ocoee/);
    expect(fluEmptyMessage("12085", "Unincorporated")).toMatch(/not designated/);
  });
});
