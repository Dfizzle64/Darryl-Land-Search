import { afterEach, describe, expect, it, vi } from "vitest";
import { GET, maxDuration } from "../app/api/geocode/route";
import {
  addressVariants,
  esriMatchPoint,
  geocodeAddress,
  NOMINATIM_USER_AGENT,
  nominatimMatchPoint,
} from "../lib/geocode";
import { ADDRESS_NOT_FOUND, LOOKUP_UNAVAILABLE } from "../lib/jumpTo";

const FAST = { census: 40, esri: 40, nominatim: 40, county: 40 };

afterEach(() => {
  vi.unstubAllGlobals();
});

function json(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

function censusHit(lng = -84.39, lat = 33.75): Response {
  return json({ result: { addressMatches: [{ coordinates: { x: lng, y: lat } }] } });
}

function censusMiss(): Response {
  return json({ result: { addressMatches: [] } });
}

function esriHit(score: number, lng = -84.05, lat = 34.11, country: string | null = "USA"): Response {
  return json({
    candidates: [
      {
        score,
        location: { x: lng, y: lat },
        attributes: { Score: score, Country: country, Addr_type: "StreetAddress" },
      },
    ],
  });
}

function nominatimHit(lon = "-81.61", lat = "28.05"): Response {
  return json([{ lat, lon, address: { country_code: "us" } }]);
}

function requestUrl(input: RequestInfo | URL): URL {
  if (input instanceof URL) return input;
  if (typeof input === "string") return new URL(input);
  return new URL(input.url);
}

function hang(init?: RequestInit): Promise<Response> {
  return new Promise((_, reject) => {
    const abort = () => {
      const error = new Error("The operation was aborted.");
      error.name = "AbortError";
      reject(error);
    };
    if (init?.signal?.aborted) {
      abort();
      return;
    }
    init?.signal?.addEventListener("abort", abort, { once: true });
  });
}

describe("address variants", () => {
  it("strips a unit, expands route abbreviations, and drops the ZIP", () => {
    expect(addressVariants("500 GA Hwy 20 Apt 4, Buford, GA 30518")).toEqual([
      "500 GA Hwy 20 Apt 4, Buford, GA 30518",
      "500 GA Hwy 20, Buford, GA 30518",
      "500 GA Highway 20, Buford, GA 30518",
      "500 GA Highway 20, Buford, GA",
    ]);
    expect(addressVariants("150 4th Ave N, Suite #200, Nashville, TN 37219")).toContain(
      "150 4th Ave N, Nashville, TN 37219",
    );
    expect(addressVariants("100 Peachtree St NW #2500, Atlanta, GA 30303")).toContain(
      "100 Peachtree St NW, Atlanta, GA 30303",
    );
  });

  it("expands SR, US, and County Rd without inventing a state-name highway", () => {
    expect(addressVariants("1000 SR 16, Starke, FL 32091")).toContain("1000 State Road 16, Starke, FL 32091");
    expect(addressVariants("800 US 19, Tarpon Springs, FL 34689")).toContain(
      "800 US Highway 19, Tarpon Springs, FL 34689",
    );
    expect(addressVariants("250 Co. Rd. 220, Middleburg, FL 32068")).toContain(
      "250 County Road 220, Middleburg, FL 32068",
    );
    expect(addressVariants("100 CR 42, Locust Grove, GA 30248")).toContain("100 County Road 42, Locust Grove, GA 30248");
    const orlando = addressVariants("400 S Orange Ave, Orlando, FL 32801");
    expect(orlando).toEqual(["400 S Orange Ave, Orlando, FL 32801", "400 S Orange Ave, Orlando, FL"]);
    expect(orlando.join(" ")).not.toMatch(/Florida Highway|North Carolina Highway/);
  });

  it("keeps at most four distinct Census queries", () => {
    const variants = addressVariants("150 Nexton Pkwy Apt B, Summerville, SC 29486");
    expect(variants.length).toBeLessThanOrEqual(4);
    expect(variants).toContain("150 Nexton Parkway, Summerville, SC 29486");
    expect(new Set(variants.map((variant) => variant.toLowerCase())).size).toBe(variants.length);
  });
});

describe("provider parsers", () => {
  it("keeps a high-scoring US Esri candidate and skips the rest", () => {
    expect(esriMatchPoint({ candidates: [{ score: 90, location: { x: -84.1, y: 33.7 }, attributes: { Country: "USA" } }] })).toEqual({
      lng: -84.1,
      lat: 33.7,
    });
    expect(
      esriMatchPoint({
        candidates: [
          { score: 99, location: { x: -79.38, y: 43.65 }, attributes: { Country: "CAN" } },
          { score: 95, location: { x: -84.39, y: 33.75 }, attributes: { Country: "US" } },
        ],
      }),
    ).toEqual({ lng: -84.39, lat: 33.75 });
    expect(esriMatchPoint({ candidates: [{ score: 89.99, location: { x: -84.1, y: 33.7 }, attributes: { Country: "USA" } }] })).toBeNull();
    expect(esriMatchPoint({ candidates: [{ score: 99, location: { x: 2.35, y: 48.85 }, attributes: {} }] })).toBeNull();
    expect(esriMatchPoint({ candidates: [] })).toBeNull();
  });

  it("reads a US Nominatim hit and ignores other countries", () => {
    expect(nominatimMatchPoint([{ lat: "33.75", lon: "-84.39", address: { country_code: "us" } }])).toEqual({
      lng: -84.39,
      lat: 33.75,
    });
    expect(nominatimMatchPoint([{ lat: "43.65", lon: "-79.38", address: { country_code: "ca" } }])).toBeNull();
    expect(nominatimMatchPoint([])).toBeNull();
  });
});

describe("geocode fallback order", () => {
  it("returns the Census match and does not call the fallbacks", async () => {
    const fetchImpl = vi.fn(async (input: RequestInfo | URL) => {
      expect(requestUrl(input).hostname).toBe("geocoding.geo.census.gov");
      expect(requestUrl(input).searchParams.get("benchmark")).toBe("Public_AR_Current");
      return censusHit(-81.38, 28.54);
    });
    const result = await geocodeAddress("400 S Orange Ave, Orlando, FL 32801", { fetch: fetchImpl, timeouts: FAST });
    expect(result).toEqual({ ok: true, lng: -81.38, lat: 28.54, provider: "census" });
    expect(fetchImpl).toHaveBeenCalledOnce();
  });

  it("retries a Census variant after the unit is removed", async () => {
    const seen: string[] = [];
    const fetchImpl = vi.fn(async (input: RequestInfo | URL) => {
      const address = requestUrl(input).searchParams.get("address") ?? "";
      seen.push(address);
      if (address.includes("Apt")) return censusMiss();
      return censusHit();
    });
    const result = await geocodeAddress("233 Peachtree St NE Apt 18, Atlanta, GA 30303", {
      fetch: fetchImpl,
      timeouts: FAST,
    });
    expect(result).toMatchObject({ ok: true, provider: "census" });
    expect(seen[0]).toContain("Apt");
    expect(seen[1]).toBe("233 Peachtree St NE, Atlanta, GA 30303");
    expect(fetchImpl.mock.calls.every(([input]) => requestUrl(input as RequestInfo).hostname.includes("census"))).toBe(true);
  });

  it("asks Census again with the route expanded and without the ZIP", async () => {
    const seen: string[] = [];
    const fetchImpl = vi.fn(async (input: RequestInfo | URL) => {
      const address = requestUrl(input).searchParams.get("address") ?? "";
      seen.push(address);
      if (address === "1000 State Road 16, Starke, FL") return censusHit(-82.1, 29.95);
      return censusMiss();
    });
    const result = await geocodeAddress("1000 S.R. 16, Starke, FL 32091", { fetch: fetchImpl, timeouts: FAST });
    expect(result).toEqual({ ok: true, lng: -82.1, lat: 29.95, provider: "census" });
    expect(seen).toContain("1000 State Road 16, Starke, FL 32091");
    expect(seen).toContain("1000 State Road 16, Starke, FL");
  });

  it("retries Census once after a 503, then uses that match", async () => {
    let calls = 0;
    const fetchImpl = vi.fn(async () => {
      calls += 1;
      if (calls === 1) return json({ error: "busy" }, 503);
      return censusHit(-86.8, 33.52);
    });
    const result = await geocodeAddress("200 Dexter Ave, Montgomery, AL 36104", { fetch: fetchImpl, timeouts: FAST });
    expect(result).toEqual({ ok: true, lng: -86.8, lat: 33.52, provider: "census" });
    expect(calls).toBe(2);
  });

  it("retries a timed-out Census call once and then falls through to Esri", async () => {
    const hosts: string[] = [];
    const fetchImpl = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = requestUrl(input);
      hosts.push(url.hostname);
      if (url.hostname.includes("census")) return hang(init);
      expect(url.searchParams.get("forStorage")).toBe("false");
      expect(url.searchParams.get("countryCode")).toBe("USA");
      return esriHit(100, -82.1, 29.95);
    });
    const result = await geocodeAddress("1000 SR 16, Starke, FL 32091", { fetch: fetchImpl, timeouts: FAST });
    expect(result).toEqual({ ok: true, lng: -82.1, lat: 29.95, provider: "esri" });
    expect(hosts.filter((host) => host.includes("census"))).toHaveLength(2);
    expect(hosts.at(-1)).toBe("geocode.arcgis.com");
  });

  it("skips a low Esri score and a non-US candidate, then uses Nominatim", async () => {
    const fetchImpl = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = requestUrl(input);
      if (url.hostname.includes("census")) return censusMiss();
      if (url.hostname.includes("arcgis")) {
        return json({
          candidates: [
            { score: 88, location: { x: -84, y: 33 }, attributes: { Country: "USA" } },
            { score: 99, location: { x: -79.38, y: 43.65 }, attributes: { Country: "CAN" } },
          ],
        });
      }
      const headers = init?.headers as Record<string, string>;
      expect(headers["User-Agent"]).toBe(NOMINATIM_USER_AGENT);
      expect(url.searchParams.get("countrycodes")).toBe("us");
      return nominatimHit("-83.76", "32.83");
    });
    const result = await geocodeAddress("223 Great Waters Lane, Macon, GA 31220", { fetch: fetchImpl, timeouts: FAST });
    expect(result).toEqual({ ok: true, lng: -83.76, lat: 32.83, provider: "nominatim" });
  });

  it("stops extra Census spellings once the Census time budget is spent", async () => {
    let ticks = 0;
    const seen: string[] = [];
    const fetchImpl = vi.fn(async (input: RequestInfo | URL) => {
      const url = requestUrl(input);
      if (url.hostname.includes("census")) {
        seen.push(url.searchParams.get("address") ?? "");
        return censusMiss();
      }
      if (url.hostname.includes("arcgis")) return esriHit(96);
      return json([]);
    });
    const result = await geocodeAddress("500 GA Hwy 20 Apt 4, Buford, GA 30518", {
      fetch: fetchImpl,
      timeouts: FAST,
      now: () => {
        ticks += 1;
        return ticks > 2 ? 8_000 : 0;
      },
    });
    expect(seen).toEqual(["500 GA Hwy 20 Apt 4, Buford, GA 30518"]);
    expect(result).toMatchObject({ ok: true, provider: "esri" });
  });

  it("rejects a rewritten Census hit on a different street and uses Esri", async () => {
    const fetchImpl = vi.fn(async (input: RequestInfo | URL) => {
      const url = requestUrl(input);
      if (url.hostname.includes("census")) {
        const address = url.searchParams.get("address") ?? "";
        if (address.endsWith(", SC")) {
          return json({
            result: {
              addressMatches: [
                {
                  matchedAddress: "150 NEWTON RD, SUMMERVILLE, SC, 29483",
                  coordinates: { x: -80.258, y: 33.0 },
                },
              ],
            },
          });
        }
        return censusMiss();
      }
      if (url.hostname.includes("arcgis")) return esriHit(96.61, -80.129, 33.08);
      return json([]);
    });
    const result = await geocodeAddress("150 Nexton Pkwy, Summerville, SC 29486", { fetch: fetchImpl, timeouts: FAST });
    expect(result).toEqual({ ok: true, lng: -80.129, lat: 33.08, provider: "esri" });
  });

  it("keeps a rewritten Census hit when the street name still agrees", async () => {
    const fetchImpl = vi.fn(async (input: RequestInfo | URL) => {
      const url = requestUrl(input);
      if (!url.hostname.includes("census")) return json({ candidates: [] });
      const address = url.searchParams.get("address") ?? "";
      if (address.includes("Apt")) return censusMiss();
      return json({
        result: {
          addressMatches: [
            { matchedAddress: "233 PEACHTREE ST NE, ATLANTA, GA, 30303", coordinates: { x: -84.39, y: 33.76 } },
          ],
        },
      });
    });
    const result = await geocodeAddress("233 Peachtree St NE Apt 18, Atlanta, GA 30303", {
      fetch: fetchImpl,
      timeouts: FAST,
    });
    expect(result).toEqual({ ok: true, lng: -84.39, lat: 33.76, provider: "census" });
  });

  it("says the address was not found only after every provider misses", async () => {
    const fetchImpl = vi.fn(async (input: RequestInfo | URL) => {
      const host = requestUrl(input).hostname;
      if (host.includes("census")) return censusMiss();
      if (host.includes("arcgis")) return json({ candidates: [] });
      return json([]);
    });
    const result = await geocodeAddress("14500 Whitcomb Way, Winter Garden, FL 34787", {
      fetch: fetchImpl,
      timeouts: FAST,
      parcelRead: () => "",
    });
    expect(result).toEqual({ ok: false, status: 404, error: ADDRESS_NOT_FOUND });
  });

  it("says the lookup is unavailable when every provider errors", async () => {
    const fetchImpl = vi.fn(async (input: RequestInfo | URL) => {
      const host = requestUrl(input).hostname;
      if (host.includes("census")) return json({ error: "down" }, 502);
      if (host.includes("arcgis")) return json({ error: { code: 500, message: "down" } });
      return json({ error: "blocked" }, 429);
    });
    const result = await geocodeAddress("223 Great Waters Lane, Macon, GA 31220", { fetch: fetchImpl, timeouts: FAST });
    expect(result).toEqual({ ok: false, status: 503, error: LOOKUP_UNAVAILABLE });
    expect(fetchImpl.mock.calls.filter(([input]) => requestUrl(input as RequestInfo).hostname.includes("census"))).toHaveLength(2);
  });

  it("says the lookup is unavailable when fallbacks error after Census misses", async () => {
    const fetchImpl = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const host = requestUrl(input).hostname;
      if (host.includes("census")) return censusMiss();
      return hang(init);
    });
    const result = await geocodeAddress("400 S Orange Ave, Orlando, FL", { fetch: fetchImpl, timeouts: FAST });
    expect(result).toEqual({ ok: false, status: 503, error: LOOKUP_UNAVAILABLE });
  });

  it("does not retry a non-transient Census rejection", async () => {
    let censusCalls = 0;
    const fetchImpl = vi.fn(async (input: RequestInfo | URL) => {
      const host = requestUrl(input).hostname;
      if (host.includes("census")) {
        censusCalls += 1;
        return json({ error: "bad" }, 400);
      }
      if (host.includes("arcgis")) return esriHit(97, -84.39, 33.76);
      return json([]);
    });
    const result = await geocodeAddress("1 CNN Center, Atlanta, GA 30303", { fetch: fetchImpl, timeouts: FAST });
    expect(result).toMatchObject({ ok: true, provider: "esri" });
    expect(censusCalls).toBe(addressVariants("1 CNN Center, Atlanta, GA 30303").length);
  });

  it("offers a same-state street candidate under the auto threshold and skips postal and unrelated streets", async () => {
    const fetchImpl = vi.fn(async (input: RequestInfo | URL) => {
      const host = requestUrl(input).hostname;
      if (host.includes("census")) return censusMiss();
      if (host === "geocode.arcgis.com") {
        return json({
          candidates: [
            {
              address: "100 Harvest Point Blvd, Spring Hill, Tennessee, 37174",
              score: 87.03,
              location: { x: -86.97546, y: 35.73736 },
              attributes: { Addr_type: "PointAddress", Country: "USA", Region: "Tennessee" },
            },
            {
              address: "37174, Spring Hill, Tennessee",
              score: 84,
              location: { x: -86.93, y: 35.75 },
              attributes: { Addr_type: "Postal", Country: "USA", Region: "Tennessee" },
            },
            {
              address: "Parks Ln, Spring Hill, Tennessee",
              score: 79.26,
              location: { x: -86.91, y: 35.72 },
              attributes: { Addr_type: "StreetName", Country: "USA", Region: "Tennessee" },
            },
          ],
        });
      }
      if (host.includes("nominatim")) return json([]);
      if (host === "tnmap.tn.gov") {
        return json({
          candidates: [
            {
              address: "100 HARVEST POINT BLVD, SPRING HILL, TN, 37174",
              score: 88.17,
              location: { x: -86.975465, y: 35.737368 },
              attributes: { Score: 88.17 },
            },
          ],
        });
      }
      return json({ features: [] });
    });
    const result = await geocodeAddress("100 Harvest Park Dr, Spring Hill, TN 37174", {
      fetch: fetchImpl,
      timeouts: FAST,
      parcelRead: () => "",
    });
    expect(result).toMatchObject({ ok: false, status: 404, error: ADDRESS_NOT_FOUND });
    expect(result.ok ? [] : result.suggestions).toEqual([
      {
        label: "100 HARVEST POINT BLVD, SPRING HILL, TN, 37174",
        lng: -86.975465,
        lat: 35.737368,
        score: 88.17,
        provider: "county",
      },
    ]);
  });

  it("does not suggest a ZIP centroid or a street that does not share the name", async () => {
    const fetchImpl = vi.fn(async (input: RequestInfo | URL) => {
      const host = requestUrl(input).hostname;
      if (host.includes("census")) return censusMiss();
      if (host === "geocode.arcgis.com") {
        return json({
          candidates: [
            {
              address: "28079, Indian Trail, North Carolina",
              score: 84.83,
              location: { x: -80.67, y: 35.07 },
              attributes: { Addr_type: "Postal", Country: "USA", Region: "North Carolina" },
            },
            {
              address: "200 Indian Trail Rd, Indian Trail, North Carolina, 28079",
              score: 78.24,
              location: { x: -80.67, y: 35.08 },
              attributes: { Addr_type: "PointAddress", Country: "USA", Region: "North Carolina" },
            },
          ],
        });
      }
      if (host.includes("nominatim")) return json([]);
      if (host === "atlas.unioncountync.gov") {
        return json({
          features: [
            {
              attributes: { NUM: "911", NAME: "BAILEY", TYPE: "CT", DISPLAY: "911 BAILEY CT" },
              geometry: { x: -80.8, y: 35.1 },
            },
          ],
        });
      }
      return json({ features: [] });
    });
    const result = await geocodeAddress("200 Bailey Rd, Indian Trail, NC 28079", {
      fetch: fetchImpl,
      timeouts: FAST,
      parcelRead: () => "",
    });
    expect(result).toEqual({ ok: false, status: 404, error: ADDRESS_NOT_FOUND });
  });

  it("jumps to one parcel situs match and suggests when several remain", async () => {
    const one = await geocodeAddress("315 N Bumby Avenue, Orlando, FL 32803", {
      fetch: vi.fn(async (input: RequestInfo | URL) => {
        const host = requestUrl(input).hostname;
        if (host.includes("census")) return censusMiss();
        if (host === "geocode.arcgis.com") return json({ candidates: [] });
        return json([]);
      }),
      timeouts: FAST,
      parcelRead: () => "315\tN BUMBY AVE\tORLANDO\t32803\t-81.35100\t28.55100\n",
    });
    expect(one).toEqual({ ok: true, lng: -81.351, lat: 28.551, provider: "parcels" });

    const many = await geocodeAddress("100 Main Street, FL", {
      fetch: vi.fn(async (input: RequestInfo | URL) => {
        const host = requestUrl(input).hostname;
        if (host.includes("census")) return censusMiss();
        if (host === "geocode.arcgis.com") return json({ candidates: [] });
        return json([]);
      }),
      timeouts: FAST,
      parcelRead: () =>
        ["100\tMAIN ST\tORLANDO\t32801\t-81.30000\t28.50000", "100\tMAIN ST\tAPOPKA\t32703\t-81.50000\t28.60000"].join("\n"),
    });
    expect(many.ok ? [] : many.suggestions?.map((item) => item.provider)).toEqual(["parcels", "parcels"]);
  });

  it("keeps a county outage from turning a clean miss into an unavailable lookup", async () => {
    const fetchImpl = vi.fn(async (input: RequestInfo | URL) => {
      const host = requestUrl(input).hostname;
      if (host.includes("census")) return censusMiss();
      if (host === "geocode.arcgis.com") return json({ candidates: [] });
      if (host.includes("nominatim")) return json([]);
      return json({ error: "down" }, 429);
    });
    const result = await geocodeAddress("100 Harvest Park Dr, Spring Hill, TN 37174", {
      fetch: fetchImpl,
      timeouts: FAST,
      parcelRead: () => "",
    });
    expect(result).toEqual({ ok: false, status: 404, error: ADDRESS_NOT_FOUND });
  });
});

describe("geocode route", () => {
  it("keeps lat/long parsing on the server and does not call a geocoder", async () => {
    const fetchImpl = vi.fn();
    vi.stubGlobal("fetch", fetchImpl);
    const response = await GET(new Request("http://localhost/api/geocode?q=26.1224%2C+-80.1373"));
    expect(response.status).toBe(200);
    expect(await response.json()).toEqual({ lat: 26.1224, lng: -80.1373, kind: "coordinates" });
    expect(fetchImpl).not.toHaveBeenCalled();
    expect(maxDuration).toBe(20);
  });

  it("rejects coordinates that are not a location", async () => {
    const response = await GET(new Request("http://localhost/api/geocode?q=200%2C+400"));
    expect(response.status).toBe(400);
    expect(await response.json()).toEqual({ error: "Those coordinates are not valid." });
  });

  it("returns the provider that matched", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => censusHit(-84.39, 33.75)),
    );
    const response = await GET(
      new Request(`http://localhost/api/geocode?q=${encodeURIComponent("233 Peachtree St NE, Atlanta, GA 30303")}`),
    );
    expect(response.status).toBe(200);
    expect(response.headers.get("Cache-Control")).toBe("no-store");
    expect(await response.json()).toEqual({ lng: -84.39, lat: 33.75, kind: "address", provider: "census" });
  });

  it("returns the unavailable message when the geocoders fail", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => json({ error: "down" }, 503)),
    );
    const response = await GET(
      new Request(`http://localhost/api/geocode?q=${encodeURIComponent("223 Great Waters Lane, Macon, GA")}`),
    );
    expect(response.status).toBe(503);
    expect(await response.json()).toEqual({ error: LOOKUP_UNAVAILABLE });
  });

  it("returns did-you-mean choices instead of the not-found error", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async (input: RequestInfo | URL) => {
        const host = requestUrl(input).hostname;
        if (host.includes("census")) return censusMiss();
        if (host === "geocode.arcgis.com") {
          return json({
            candidates: [
              {
                address: "Gardenia Ln, Fort Mill, South Carolina, 29707",
                score: 89.76,
                location: { x: -80.84224, y: 34.98276 },
                attributes: { Addr_type: "StreetName", Country: "USA", Region: "South Carolina" },
              },
            ],
          });
        }
        return json([]);
      }),
    );
    const response = await GET(
      new Request(`http://localhost/api/geocode?q=${encodeURIComponent("4100 Gardenia Dr, Indian Land, SC 29707")}`),
    );
    expect(response.status).toBe(200);
    expect(await response.json()).toEqual({
      kind: "suggestions",
      suggestions: [
        {
          label: "Gardenia Ln, Fort Mill, South Carolina, 29707",
          lng: -80.84224,
          lat: 34.98276,
          score: 89.76,
          provider: "esri",
        },
      ],
    });
  });
});
