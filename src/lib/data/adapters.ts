import type { ParcelCollection, ParcelFeature } from "../types";
import { loadParcelCollection } from "./loadFixtures";
import { getMarketFixtureParcel, queryMarketFixtureParcels } from "./marketParcelStore";
import {
  finalizeOrlandoParcelPage,
  getOrlandoFixtureParcel,
  queryOrlandoFixtureParcels,
  queryOrlandoLiveParcels,
  type OrlandoParcelPage,
  type OrlandoParcelQuery,
} from "./orlandoParcelStore";

/**
 * Data-source adapters. The pilot ships on fixtures so `npm run dev` works
 * without keys. Orlando shed parcels are partitioned GeoJSON (+ optional live
 * DOH viewport queries). Swap DATA_SOURCE=ocpa-live for Orange single-parcel
 * lookups against OCPA.
 *
 * Commercial vendors (Regrid, ATTOM, etc.) should implement ParcelProvider
 * rather than replacing the UI. Do not put paid credentials in the repo.
 */
export interface ParcelProvider {
  id: string;
  listParcels(): Promise<ParcelCollection>;
  getParcel(id: string): Promise<ParcelFeature | null>;
  queryOrlandoParcels?(query: OrlandoParcelQuery & { source?: "fixture" | "live" }): Promise<OrlandoParcelPage>;
  queryMarketParcels?(market: string, query: OrlandoParcelQuery): Promise<OrlandoParcelPage>;
}

export class FixtureParcelProvider implements ParcelProvider {
  id = "fixture";

  async listParcels(): Promise<ParcelCollection> {
    // Backward-compatible Orange County pilot sample.
    return loadParcelCollection();
  }

  async getParcel(id: string): Promise<ParcelFeature | null> {
    const [orlando, market] = await Promise.all([getOrlandoFixtureParcel(id), getMarketFixtureParcel(id)]);
    // Polk shares parcel ids with the Orlando DOH extract. The Tampa market tile is the upgrade.
    if (market && (!orlando || market.properties.source !== orlando.properties.source)) return market;
    if (orlando) return orlando;
    if (market) return market;
    const collection = await this.listParcels();
    return collection.features.find((feature) => feature.properties.id === id) ?? null;
  }

  async queryOrlandoParcels(
    query: OrlandoParcelQuery & { source?: "fixture" | "live" },
  ): Promise<OrlandoParcelPage> {
    if (query.source === "live") {
      const collection = await queryOrlandoLiveParcels(query);
      return finalizeOrlandoParcelPage(collection.features, query);
    }
    return queryOrlandoFixtureParcels(query);
  }

  async queryMarketParcels(market: string, query: OrlandoParcelQuery): Promise<OrlandoParcelPage> {
    return queryMarketFixtureParcels(market, query);
  }
}

export class OcpaLiveParcelProvider implements ParcelProvider {
  id = "ocpa-live";

  constructor(
    private readonly endpoint = process.env.OCPA_PARCELS_URL ??
      "https://vgispublic.ocpafl.org/server/rest/services/Webmap/PARCEL/MapServer/4/query",
  ) {}

  async listParcels(): Promise<ParcelCollection> {
    const fixtures = new FixtureParcelProvider();
    return fixtures.listParcels();
  }

  async getParcel(id: string): Promise<ParcelFeature | null> {
    const bareId = id.includes(":") ? id.split(":").slice(1).join(":") : id;
    const params = new URLSearchParams({
      where: `PARCEL='${bareId.replace(/'/g, "''")}'`,
      outFields: [
        "PARCEL",
        "NAME1",
        "NAME2",
        "PROP_NAME",
        "SITUS",
        "ZONING_CODE",
        "SALE_DATE",
        "SALE_ADJ_VALUE",
        "TOTAL_MKT",
        "TOTAL_ASSD",
        "TAXABLE",
        "TAXES",
        "ACREAGE",
        "ADD1",
        "ADD2",
        "CITY",
        "STATE",
        "ZIP",
        "DOR_CODE",
        "CITY_SITUS",
        "ZIP_SITUS",
        "QUAL_CODE",
        "CITY_CODE",
      ].join(","),
      returnGeometry: "true",
      outSR: "4326",
      f: "geojson",
    });
    const response = await fetch(`${this.endpoint}?${params.toString()}`, {
      headers: { Accept: "application/json" },
      next: { revalidate: 60 * 60 },
    });
    if (!response.ok) {
      throw new Error(`OCPA live lookup failed (${response.status})`);
    }
    const body = (await response.json()) as ParcelCollection;
    return body.features[0] ?? null;
  }

  async queryOrlandoParcels(
    query: OrlandoParcelQuery & { source?: "fixture" | "live" },
  ): Promise<OrlandoParcelPage> {
    return new FixtureParcelProvider().queryOrlandoParcels!(query);
  }
}

export class VendorParcelProvider implements ParcelProvider {
  id = "vendor";

  async listParcels(): Promise<ParcelCollection> {
    throw new Error(
      "No commercial parcel vendor is wired. Implement VendorParcelProvider against Regrid/ATTOM/etc. without committing secrets.",
    );
  }

  async getParcel(): Promise<ParcelFeature | null> {
    throw new Error("No commercial parcel vendor is wired.");
  }
}

export function getParcelProvider(): ParcelProvider {
  const source = (process.env.DATA_SOURCE ?? "fixture").toLowerCase();
  if (source === "ocpa-live") return new OcpaLiveParcelProvider();
  if (source === "vendor") return new VendorParcelProvider();
  return new FixtureParcelProvider();
}
