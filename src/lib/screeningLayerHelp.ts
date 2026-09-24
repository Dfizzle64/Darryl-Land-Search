import { STATE_REPORT_CARDS } from "./screening";

export type ScreeningHelpScope = {
  market: string;
  county: string | null;
  state: string | null;
  /** States in the selected market. Ignored when a county state is selected. */
  states: string[];
};

export type ScreeningLayerNotes = {
  flood: string;
  wetlands: string;
  schools: string;
  water: string;
  sewer: string;
  power: string;
  eligibleTracts: string;
  designatedOz: string;
};

const NOT_FOR_MARKET = "Not available for this market yet.";
const NOT_FOR_COUNTY = "Not available for this county yet.";

const SCHOOL_STATES = new Set(["Florida", "Georgia", "North Carolina", "South Carolina", "Tennessee", "Alabama"]);

const FLOOD =
  "FEMA NFHL effective flood zones at the centroid. A static BFE is shown only when NFHL publishes one. This layer has no Community Rating System class.";
const WETLANDS = "National Wetlands Inventory. Polygons draw at closer zoom.";
const ELIGIBLE =
  "Brown tracts are rural-eligible. Blue tracts are urban eligible. Eligible is not a designated 2027 QOZ. SC MF priority is a separate shortlist, not a designation.";
const POWER_GENERIC = "HIFLD electric retail territories. Not a connection or a will-serve. Gas has no public polygon.";
const POWER_ORANGE = "Orange County open-data electric service areas. Not a connection or a will-serve. Gas has no public polygon.";
const POWER_MECK =
  "HIFLD retail territories. In Mecklenburg those include Duke Energy Carolinas and EnergyUnited EMC and can overlap a municipal retailer. Not a connection or a will-serve. Gas has no public polygon.";

function statesInView(scope: ScreeningHelpScope): string[] {
  if (scope.state) return [scope.state];
  return [...new Set(scope.states)];
}

function countySelected(scope: ScreeningHelpScope): boolean {
  return Boolean(scope.county && scope.state);
}

function unavailable(scope: ScreeningHelpScope): string {
  return countySelected(scope) ? NOT_FOR_COUNTY : NOT_FOR_MARKET;
}

function orangeInView(scope: ScreeningHelpScope): boolean {
  if (countySelected(scope)) return scope.county === "Orange" && scope.state === "Florida";
  return scope.market === "Orlando";
}

function meckInView(scope: ScreeningHelpScope): boolean {
  if (countySelected(scope)) return scope.county === "Mecklenburg" && scope.state === "North Carolina";
  if (scope.state === "South Carolina") return false;
  return scope.market === "Charlotte" && (scope.state == null || scope.state === "North Carolina");
}

function waterNote(scope: ScreeningHelpScope, kind: "water" | "sewer"): string {
  const service = kind === "water" ? "water" : "wastewater";
  const layer = kind === "water" ? "Water" : "Sewer";
  if (orangeInView(scope)) {
    if (countySelected(scope)) {
      return `Orange County public ${service} service areas. Not a connection or a will-serve.`;
    }
    return `${layer} polygons are loaded for Orange County only. Other counties in this market are not covered yet. Not a connection or a will-serve.`;
  }
  if (meckInView(scope)) {
    const city =
      kind === "water"
        ? "Charlotte Water publishes no service-area polygon. Inside the city the municipal boundary is a jurisdiction proxy, and unincorporated Mecklenburg stays unverified."
        : "Charlotte publishes no sewer service-area polygon. Inside the city the municipal boundary is a jurisdiction proxy, and unincorporated Mecklenburg stays unverified.";
    if (!countySelected(scope) && scope.state == null) {
      return `${city} Other counties in this market are not covered yet.`;
    }
    return city;
  }
  return unavailable(scope);
}

function powerNote(scope: ScreeningHelpScope): string {
  if (orangeInView(scope)) {
    if (!countySelected(scope)) {
      return "Orange County uses its open-data electric service areas. Other counties in this market use HIFLD retail territories. Neither is a connection or a will-serve. Gas has no public polygon.";
    }
    return POWER_ORANGE;
  }
  if (meckInView(scope) && (countySelected(scope) || scope.state === "North Carolina" || scope.state == null)) {
    return POWER_MECK;
  }
  return POWER_GENERIC;
}

function schoolNote(scope: ScreeningHelpScope): string {
  const states = statesInView(scope);
  if (orangeInView(scope) && countySelected(scope)) {
    return "OCPS attendance zones, with 2025-26 Know Your Schools letters where a grade is published. No grade is invented.";
  }
  if (meckInView(scope) && countySelected(scope)) {
    return "CMS attendance zones, with 2025-26 NCDPI grades for Charlotte-Mecklenburg Schools. No grade is invented.";
  }
  if (scope.market === "Orlando" && !countySelected(scope)) {
    return "Orange County draws OCPS attendance zones. Elsewhere in this market, letters are the 2025-26 Know Your Schools report card. No grade is invented.";
  }
  if (scope.market === "Charlotte" && !countySelected(scope) && (scope.state == null || scope.state === "North Carolina")) {
    return "Mecklenburg draws CMS attendance zones with 2025-26 NCDPI grades. Other counties in this market use NCES locations and the state report card. No grade is invented.";
  }
  if (states.length === 1) {
    const state = states[0];
    if (!SCHOOL_STATES.has(state)) return unavailable(scope);
    if (state === "Florida") {
      return "2025-26 Know Your Schools letters where a grade is published. No attendance-zone layer for this market. No grade is invented.";
    }
    if (state === "North Carolina") {
      return "NCES locations. Grades in this extract are the 2024-25 North Carolina DPI researcher file where a school is listed. No grade is invented.";
    }
    const card = STATE_REPORT_CARDS[state === "Georgia" ? "GA" : state === "South Carolina" ? "SC" : state === "Tennessee" ? "TN" : "AL"];
    return `NCES locations and a link to the ${card.label}. No grade is invented.`;
  }
  const missing = states.filter((state) => !SCHOOL_STATES.has(state));
  const loaded = states.filter((state) => SCHOOL_STATES.has(state));
  if (!loaded.length) return unavailable(scope);
  if (!missing.length) {
    return "NCES locations and a link to the state report card. No grade is invented.";
  }
  const loadedLabel = loaded.length === 1 ? `${loaded[0]} uses` : `${loaded.join(" and ")} use`;
  const missingLabel = missing.length === 1 ? missing[0] : missing.join(" and ");
  return `${loadedLabel} NCES locations and the state report card. ${missingLabel} school dots are not loaded yet. No grade is invented.`;
}

function designatedNote(scope: ScreeningHelpScope): string {
  if (scope.market === "Orlando" && (!countySelected(scope) || (scope.county === "Orange" && scope.state === "Florida"))) {
    return "Current HUD/Treasury Qualified Opportunity Zone layer for Orange County. This is not a 2027 designation.";
  }
  return unavailable(scope);
}

export function screeningLayerNotes(scope: ScreeningHelpScope): ScreeningLayerNotes {
  return {
    flood: FLOOD,
    wetlands: WETLANDS,
    schools: schoolNote(scope),
    water: waterNote(scope, "water"),
    sewer: waterNote(scope, "sewer"),
    power: powerNote(scope),
    eligibleTracts: ELIGIBLE,
    designatedOz: designatedNote(scope),
  };
}

export function screeningLegendLine(
  kind: "water" | "sewer" | "power" | "schools",
  scope: ScreeningHelpScope,
): string {
  const notes = screeningLayerNotes(scope);
  if (kind === "water") {
    if (orangeInView(scope)) return "Water service area (Orange County)";
    if (meckInView(scope)) return "Water (no Charlotte service polygon)";
    return "Water (not in this view)";
  }
  if (kind === "sewer") {
    if (orangeInView(scope)) return "Sewer service area (Orange County)";
    if (meckInView(scope)) return "Sewer (no Charlotte service polygon)";
    return "Sewer (not in this view)";
  }
  if (kind === "power") {
    if (orangeInView(scope) && (countySelected(scope) || scope.market === "Orlando")) return "Electric service area";
    return "Electric retail territory";
  }
  if (notes.schools.startsWith("Not available")) return "Schools (not in this view)";
  if (meckInView(scope)) return "Schools · CMS zones in Mecklenburg";
  if (orangeInView(scope)) return "Schools · OCPS zones in Orange County";
  return "Schools · locations, no invented grade";
}
