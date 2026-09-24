/**
 * Buncombe County (37021) field rules shared with scripts/seed_buncombe_parcels.py.
 * SalePrice on the county Property layer is often stamp-like or inconsistent with
 * the excise stamp. Untrusted prices stay null. Deed dates are separate.
 */

/** North Carolina excise tax: $2 per $1,000 of consideration. */
export const NC_EXCISE_RATE = 0.002;

export const BUNCOMBE_MUNICIPALITIES: Record<string, string> = {
  CAS: "Asheville",
  CBF: "Biltmore Forest",
  CBM: "Black Mountain",
  CMT: "Montreat",
  CWO: "Woodfin",
  CWV: "Weaverville",
};

export const BUNCOMBE_PROPCARD = "https://prc-buncombe.spatialest.com/#/property/";

export function buncombePropCardUrl(pin: string, raw?: string | null): string {
  const expected = `${BUNCOMBE_PROPCARD}${pin}`;
  const text = raw?.trim();
  if (text && text.startsWith(BUNCOMBE_PROPCARD) && text.includes(pin)) return text;
  return expected;
}

export function castBuncombeMoney(value: unknown): number | null {
  if (value == null) return null;
  const text = String(value).trim().replace(/[$,]/g, "");
  if (!text) return null;
  const parsed = Number(text);
  if (!Number.isFinite(parsed)) return null;
  return parsed;
}

export function parseBuncombeDeedDate(value: unknown): string | null {
  const text = value == null ? "" : String(value).trim();
  if (!/^\d{8}$/.test(text)) return null;
  const year = Number(text.slice(0, 4));
  const month = Number(text.slice(4, 6));
  const day = Number(text.slice(6, 8));
  if (year < 1900 || year > 2100 || month < 1 || month > 12 || day < 1 || day > 31) return null;
  return `${text.slice(0, 4)}-${text.slice(4, 6)}-${text.slice(6, 8)}`;
}

export function composeBuncombeSitus(parts: {
  houseNumber?: string | null;
  numberSuffix?: string | null;
  streetPrefix?: string | null;
  streetName?: string | null;
  streetType?: string | null;
  postDirection?: string | null;
}): string | null {
  const piece = (value: string | null | undefined) => {
    const text = value?.trim();
    return text || null;
  };
  const number = piece(parts.houseNumber);
  const suffix = piece(parts.numberSuffix);
  let house: string | null = null;
  if (number && suffix) {
    house = suffix.length === 1 ? `${number}${suffix}` : `${number} ${suffix}`;
  } else {
    house = number;
  }
  const street = [piece(parts.streetPrefix), piece(parts.streetName), piece(parts.streetType), piece(parts.postDirection)]
    .filter((item): item is string => Boolean(item))
    .join(" ");
  const line = [house, street].filter(Boolean).join(" ");
  return line || null;
}

export type BuncombeSaleInput = {
  salePrice: number | null;
  stamps: number | null;
  landValue: number | null;
  marketValue: number | null;
};

/**
 * Keep SalePrice only when it agrees with the excise stamp or, with no stamp,
 * looks like a real consideration against land and total market value.
 */
export function trustedBuncombeSalePrice(input: BuncombeSaleInput): number | null {
  const price = input.salePrice;
  if (price == null || !Number.isFinite(price) || price <= 0) return null;
  const stamps = input.stamps != null && Number.isFinite(input.stamps) ? input.stamps : 0;
  const land = input.landValue != null && Number.isFinite(input.landValue) && input.landValue > 0 ? input.landValue : 0;
  const market =
    input.marketValue != null && Number.isFinite(input.marketValue) && input.marketValue > 0 ? input.marketValue : 0;
  if (stamps > 0) {
    const implied = stamps / NC_EXCISE_RATE;
    const ratio = price / implied;
    if (ratio >= 0.75 && ratio <= 1.25) return price;
    return null;
  }
  if (price < 25000) return null;
  const anchorLow = land > 0 ? land : market;
  const anchorHigh = market > 0 ? market : land;
  if (anchorLow <= 0 && anchorHigh <= 0) return price;
  if (price < 0.2 * anchorLow || price > 4 * anchorHigh) return null;
  return price;
}
