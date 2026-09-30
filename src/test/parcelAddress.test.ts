import { describe, expect, it } from "vitest";
import { countyPlaces, countyRequests } from "../lib/countyAddress";
import { canonicalStreet, findParcelHits, formatParcelLabel, parseAddressQuery } from "../lib/parcelAddress";
import { parcelHits } from "../lib/parcelIndex";
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { JumpToBar } from "../components/JumpToBar";

describe("parcel address index", () => {
  it("canonicalizes either house-number position and the street suffix", () => {
    expect(canonicalStreet("3874 Campbellsville Pike")).toEqual({ number: "3874", street: "CAMPBELLSVILLE PIKE" });
    expect(canonicalStreet("CAMPBELLSVILLE PIKE 3874")).toEqual({ number: "3874", street: "CAMPBELLSVILLE PIKE" });
    expect(canonicalStreet("100 Harvest Park Drive")).toEqual({ number: "100", street: "HARVEST PARK DR" });
  });

  it("filters situs rows by city and ZIP and drops a blank city when the query names one", () => {
    const text = [
      "100\tHARVEST POINT BLVD\tSPRING HILL\t37174\t-86.97546\t35.73736",
      "100\tHARVEST POINT BLVD\tCOLUMBIA\t38401\t-87.00000\t35.60000",
      "100\tHARVEST POINT BLVD\t\t37174\t-86.90000\t35.70000",
      "200\tHARVEST POINT BLVD\tSPRING HILL\t37174\t-86.80000\t35.70000",
    ].join("\n");
    const hits = findParcelHits(text, "100 Harvest Point Boulevard, Spring Hill, TN 37174");
    expect(hits).toHaveLength(1);
    expect(hits[0]).toMatchObject({ city: "SPRING HILL", zip: "37174", state: "TN" });
    expect(formatParcelLabel(hits[0])).toBe("100 HARVEST POINT BLVD, SPRING HILL, TN 37174");
    expect(parseAddressQuery("100 Harvest Point Boulevard, Spring Hill, Tennessee 37174").state).toBe("TN");
  });

  it("reads the built Orlando situs index", () => {
    const hits = parcelHits("315 N Bumby Ave, Orlando, FL 32803");
    expect(hits[0]).toMatchObject({ label: "315 N BUMBY AVE", city: "ORLANDO", zip: "32803", state: "FL" });
    expect(parcelHits("14500 Whitcomb Way, Winter Garden, FL 34787")).toEqual([]);
  });
});

describe("county address points", () => {
  it("queries Orange, Union, and Tennessee only, and only an exact street", () => {
    expect(countyRequests("100 Harvest Park Dr, Spring Hill, TN 37174").map((item) => item.service)).toEqual(["tennessee"]);
    expect(countyRequests("14500 Whitcomb Way, Winter Garden, FL 34787").map((item) => item.service)).toEqual(["orange"]);
    const unionWhere = new URL(countyRequests("200 Bailey Rd, Indian Trail, NC 28079")[0]?.url ?? "http://invalid").searchParams.get("where");
    expect(unionWhere).toContain("NUM='200'");
    expect(unionWhere).toContain("NAME='BAILEY'");
    expect(unionWhere).toContain("TYPE='RD'");
    expect(countyRequests("4100 Gardenia Dr, Indian Land, SC 29707")).toEqual([]);

    const wrong = countyPlaces(
      "orange",
      {
        features: [
          {
            attributes: {
              FULL_ADDRESS_NUMBER: "14500",
              COMPLETE_STREETNAME: "Whittridge Dr",
              COMPLETE_ADDRESS: "14500 Whittridge Dr",
              LATITUDE: 28.47,
              LONGITUDE: -81.6,
            },
          },
        ],
      },
      "14500 Whitcomb Way, Winter Garden, FL 34787",
    );
    expect(wrong).toEqual({ hit: null, suggestions: [] });

    const court = countyPlaces(
      "union",
      {
        features: [
          {
            attributes: { NUM: "911", NAME: "BAILEY", TYPE: "CT", DISPLAY: "911 BAILEY CT" },
            geometry: { x: -80.8, y: 35.1 },
          },
        ],
      },
      "200 Bailey Rd, Indian Trail, NC 28079",
    );
    expect(court).toEqual({ hit: null, suggestions: [] });
  });
});

describe("JumpToBar suggestions", () => {
  it("renders did-you-mean choices and hides the not-found message", () => {
    const html = renderToStaticMarkup(
      createElement(JumpToBar, {
        busy: false,
        note: null,
        error: "Couldn't find that address.",
        suggestions: [
          {
            label: "100 Harvest Point Blvd, Spring Hill, TN 37174",
            lng: -86.97,
            lat: 35.73,
            score: 87,
            provider: "esri",
          },
        ],
        onJump: () => undefined,
        onSuggestion: () => undefined,
      }),
    );
    expect(html).toContain("Did you mean");
    expect(html).toContain("100 Harvest Point Blvd, Spring Hill, TN 37174");
    expect(html).toContain('type="button"');
    expect(html).not.toContain("Couldn't find that address.");
  });
});
