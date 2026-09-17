export type IncomeObservation = {
  geoid: string;
  name: string | null;
  medianHouseholdIncome: number | null;
  medianHouseholdIncomeMoe: number | null;
};

export interface IncomeProvider {
  id: string;
  listOrangeCounty(geography: "tract" | "blockGroup"): Promise<IncomeObservation[]>;
}

/**
 * Fixture income is already joined onto parcels. This adapter is the extension
 * point for live ACS. Census Bureau requires CENSUS_API_KEY as of 2026.
 */
export class CensusAcsIncomeProvider implements IncomeProvider {
  id = "census-acs";

  constructor(private readonly apiKey = process.env.CENSUS_API_KEY ?? "") {}

  async listOrangeCounty(geography: "tract" | "blockGroup"): Promise<IncomeObservation[]> {
    if (!this.apiKey) {
      throw new Error("Set CENSUS_API_KEY to query api.census.gov. Fixtures do not need a key.");
    }
    const forClause = geography === "tract" ? "tract:*" : "block group:*";
    const url = new URL("https://api.census.gov/data/2023/acs/acs5");
    url.searchParams.set("get", "NAME,B19013_001E,B19013_001M");
    url.searchParams.set("for", forClause);
    url.searchParams.set("in", "state:12 county:095");
    url.searchParams.set("key", this.apiKey);
    const response = await fetch(url);
    if (!response.ok) {
      throw new Error(`Census ACS request failed (${response.status})`);
    }
    const rows = (await response.json()) as string[][];
    const [header, ...body] = rows;
    const nameIdx = header.indexOf("NAME");
    const estIdx = header.indexOf("B19013_001E");
    const moeIdx = header.indexOf("B19013_001M");
    const stateIdx = header.indexOf("state");
    const countyIdx = header.indexOf("county");
    const tractIdx = header.indexOf("tract");
    const bgIdx = header.indexOf("block group");
    return body.map((row) => {
      const geoid = `${row[stateIdx]}${row[countyIdx]}${row[tractIdx]}${bgIdx >= 0 ? row[bgIdx] : ""}`;
      const estimate = Number(row[estIdx]);
      const moe = Number(row[moeIdx]);
      return {
        geoid,
        name: row[nameIdx] ?? null,
        medianHouseholdIncome: Number.isFinite(estimate) && estimate > 0 ? estimate : null,
        medianHouseholdIncomeMoe: Number.isFinite(moe) ? moe : null,
      };
    });
  }
}
