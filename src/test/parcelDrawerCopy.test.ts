import { describe, expect, it } from "vitest";
import { formatSale, missingPublicParcelValue } from "../lib/format";
import { describeOpportunityZone, describeOz2Eligibility } from "../lib/opportunityZone";

describe("parcel drawer gaps", () => {
  it("does not call a missing FDOR field 'not in this county'", () => {
    expect(missingPublicParcelValue("zoning", "12069")).not.toMatch(/not in this county/i);
    expect(missingPublicParcelValue("zoning", "12069")).toMatch(/not on this county's public parcel row/i);
    expect(missingPublicParcelValue("zoning", "12095")).toMatch(/OCPA/);
    expect(missingPublicParcelValue("propertyName")).toMatch(/no property name/i);
    expect(missingPublicParcelValue("situs")).toMatch(/no street address/i);
    expect(missingPublicParcelValue("sale")).toMatch(/no sale date or price/i);
    expect(missingPublicParcelValue("designatedOz")).toMatch(/not a yes or no/i);
    expect(missingPublicParcelValue("designatedOz")).toMatch(/not a 2027 designation/i);
    expect(missingPublicParcelValue("designatedOz")).not.toMatch(/^yes\b/i);
  });

  it("leaves a blank sale empty instead of the words Not available", () => {
    expect(formatSale({ date: null, price: null })).toBeNull();
    expect(formatSale({ date: "2020-01-01", price: 10 })).toMatch(/01\/01\/2020/);
  });

  it("keeps Lake tract 12069031317 as eligible and not designated", () => {
    const oz2 = describeOz2Eligibility({
      eligible: true,
      rural: true,
      tractGeoid: "12069031317",
      tractName: "Census Tract 313.17",
      designation: "eligible-for-nomination",
      source: "rev-proc-2026-14",
    });
    expect(oz2.eligible).toBe(true);
    expect(oz2.statusChip).toMatch(/not designated/i);
    expect(oz2.detail).toContain("12069031317");
    expect(oz2.detail).toMatch(/has not been nominated or certified/i);

    const designated = describeOpportunityZone(null);
    expect(designated.inZone).toBeNull();
    expect(designated.detail).toMatch(/has not been joined/i);
    expect(designated.detail).not.toMatch(/designated qoz$/i);
  });
});
