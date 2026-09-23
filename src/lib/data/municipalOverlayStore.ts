import { readFile } from "node:fs/promises";
import path from "node:path";
import {
  cityIndexFromFixture,
  EMPTY_MUNICIPAL_INDEX,
  overlayCityUsable,
  type MunicipalCityIndex,
  type MunicipalOverlayIndex,
} from "../municipalOverlays";

const DATA_DIR = path.join(process.cwd(), "data");

type RegistryCity = {
  id: string;
  status?: string;
  fixture?: string;
};

type Registry = {
  cities?: RegistryCity[];
  rejected?: Array<{ url?: string }>;
};

let pending: Promise<MunicipalOverlayIndex> | null = null;

async function readIndex(): Promise<MunicipalOverlayIndex> {
  const registry = JSON.parse(await readFile(path.join(DATA_DIR, "municipal-overlays.json"), "utf8")) as Registry;
  const cities: MunicipalCityIndex[] = [];
  for (const city of registry.cities ?? []) {
    if (city.status !== "active" || !city.fixture) continue;
    const fixture = JSON.parse(await readFile(path.join(process.cwd(), city.fixture), "utf8")) as Parameters<
      typeof cityIndexFromFixture
    >[0];
    const index = cityIndexFromFixture(fixture);
    if (!overlayCityUsable(index)) continue;
    cities.push(index);
  }
  return { cities };
}

export function loadMunicipalOverlayIndex(): Promise<MunicipalOverlayIndex> {
  if (!pending) {
    pending = readIndex().catch((error) => {
      pending = null;
      console.error("Municipal overlay fixtures are unavailable", error);
      return EMPTY_MUNICIPAL_INDEX;
    });
  }
  return pending;
}
