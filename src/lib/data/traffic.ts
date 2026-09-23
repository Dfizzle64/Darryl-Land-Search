export interface TrafficProvider {
  id: string;
  listOrangeCountyAadt(): Promise<GeoJSON.FeatureCollection>;
}

/**
 * Live FDOT AADT is public and keyless. The seed script uses this endpoint;
 * the running app reads the fixture overlay so the map stays fast offline.
 */
export class FdotAadtProvider implements TrafficProvider {
  id = "fdot-aadt";

  constructor(
    private readonly endpoint = process.env.FDOT_AADT_URL ??
      "https://services1.arcgis.com/O1JpcwDW8sjYuddV/arcgis/rest/services/Annual_Average_Daily_Traffic_Historical_TDA/FeatureServer/0/query",
  ) {}

  async listOrangeCountyAadt(): Promise<GeoJSON.FeatureCollection> {
    const params = new URLSearchParams({
      where: "YEAR_=2025 AND COUNTY='Orange' AND AADT>0",
      outFields: "AADT,ROADWAY,DESC_FRM,DESC_TO,YEAR_",
      returnGeometry: "true",
      outSR: "4326",
      f: "geojson",
      resultRecordCount: "2000",
    });
    const response = await fetch(`${this.endpoint}?${params.toString()}`);
    if (!response.ok) {
      throw new Error(`FDOT AADT request failed (${response.status})`);
    }
    return (await response.json()) as GeoJSON.FeatureCollection;
  }
}
