import { describe, expect, it } from "vitest";
import { vintageFieldLabel } from "../lib/format";

describe("Tennessee 2023 parcel field labels", () => {
  it("labels a present sale or value with its published vintage", () => {
    expect(vintageFieldLabel("Last sale", "2023", true)).toBe("Last sale · 2023");
    expect(vintageFieldLabel("Market value", "2023", true)).toBe("Market value · 2023");
    expect(vintageFieldLabel("Assessed value", "2022", true)).toBe("Assessed value · 2022");
  });

  it("leaves the label alone when the field is empty", () => {
    expect(vintageFieldLabel("Last sale", "2023", false)).toBe("Last sale");
    expect(vintageFieldLabel("Market value", null, true)).toBe("Market value");
    expect(vintageFieldLabel("Market value", "  ", true)).toBe("Market value");
  });
});
