"use client";

import {
  comptrollerRecordsUrl,
  formatAcres,
  formatMailing,
  formatNumber,
  formatRoadLabel,
  formatSale,
  formatUsd,
  isEntityOwner,
  parcelAppraiserUrl,
  sunbizSearchUrl,
} from "@/lib/format";
import { describeFluMatch } from "@/lib/flu";
import { describeRezoningCandidate } from "@/lib/filters";
import { describeOpportunityZone, describeOz2Eligibility } from "@/lib/opportunityZone";
import type { FilterState, FluConfig, ParcelFeature, ZoningConfig } from "@/lib/types";
import { describeZoningMatch } from "@/lib/zoning";

type ParcelDrawerProps = {
  parcel: ParcelFeature | null;
  zoningConfig: ZoningConfig;
  fluConfig: FluConfig;
  filters: FilterState;
  onClose: () => void;
  /** `pane` fills the desktop details rail. `page` is the standalone column / mobile sheet. */
  layout?: "page" | "pane";
};

function Field({ label, value }: { label: string; value: string | null | undefined }) {
  return (
    <div>
      <dt className="text-[11px] uppercase tracking-[0.14em] text-ink-500">{label}</dt>
      <dd className="mt-1 whitespace-pre-line text-sm text-white">{value?.trim() ? value : "Not available"}</dd>
    </div>
  );
}

export function ParcelDrawer({
  parcel,
  zoningConfig,
  fluConfig,
  filters,
  onClose,
  layout = "page",
}: ParcelDrawerProps) {
  const pane = layout === "pane";
  if (!parcel) {
    return (
      <aside className={pane ? "h-full overflow-y-auto bg-ink-900/80 p-5" : "hidden w-[24rem] shrink-0 border-l border-white/10 bg-ink-900/80 p-5 lg:block"}>
        <p className="font-display text-2xl text-white">Parcel details</p>
        <p className="mt-2 text-sm leading-relaxed text-ink-300">
          Click a ranked site or a parcel on the map to see acreage, zoning, Future Land Use, Opportunity Zone,
          owner, sale, tax, mailing, and public search links. Emails and phone numbers are not inferred.
        </p>
      </aside>
    );
  }

  const { properties } = parcel;
  const zoning = describeZoningMatch(
    properties.zoningCode,
    properties.zoningDistrict,
    zoningConfig,
    filters.includePlannedDevelopment,
    filters.includeConditionalZoning,
  );
  const flu = describeFluMatch(properties.flu, fluConfig);
  const oz = describeOpportunityZone(properties.opportunityZone);
  const oz2 = describeOz2Eligibility(properties.oz2Eligibility);
  const rezoning = describeRezoningCandidate(parcel, filters, zoningConfig, fluConfig);
  const income = filters.incomeGeography === "tract" ? properties.incomeTract : properties.incomeBlockGroup;
  const mailing = formatMailing(properties.mailingAddress);
  const entity = isEntityOwner(properties.ownerName) || isEntityOwner(properties.ownerName2);
  const fluLine = properties.flu?.code
    ? `${properties.flu.label || properties.flu.code}${properties.flu.jurisdiction ? ` · ${properties.flu.jurisdiction}` : ""}`
    : null;
  const region = properties.state === "North Carolina" ? "NC" : properties.state?.trim() || "FL";
  const placeLine =
    [properties.situsCity, properties.situsZip].filter(Boolean).join(" ") ||
    (properties.countyName ? `${properties.countyName} County, ${region}` : region === "NC" ? "North Carolina" : "Florida");
  const floridaRecords = !properties.state || properties.state === "Florida";
  const appraiser = parcelAppraiserUrl({
    parcelId: properties.parcelId,
    countyFips: properties.countyFips,
    appraiserUrl: properties.appraiserUrl,
  });
  const gaps = properties.dataGaps?.length ? properties.dataGaps : null;

  return (
    <aside className={pane ? "drawer-scroll h-full overflow-y-auto bg-ink-900 p-5" : "drawer-scroll absolute inset-x-0 bottom-0 z-20 max-h-[70vh] overflow-y-auto rounded-t-3xl border border-white/10 bg-ink-900 p-5 shadow-2xl lg:static lg:z-0 lg:max-h-none lg:w-[24rem] lg:shrink-0 lg:rounded-none lg:border-l lg:border-t-0 lg:shadow-none"}>
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-[11px] uppercase tracking-[0.18em] text-clay-400">{properties.parcelId}</p>
          <h2 className="mt-1 font-display text-2xl leading-tight text-white">
            {properties.situsAddress || "Address not available"}
          </h2>
          <p className="text-sm text-ink-300">{placeLine}</p>
        </div>
        <button type="button" onClick={onClose} className="rounded-full border border-white/15 px-3 py-1 text-sm">
          Close
        </button>
      </div>

      <dl className="mt-5 grid grid-cols-2 gap-4">
        <Field label="Owner" value={[properties.ownerName, properties.ownerName2].filter(Boolean).join("\n")} />
        <Field label="Property name" value={properties.propertyName} />
        <Field label="Acreage" value={formatAcres(properties.acreage)} />
        <Field label="Zoning" value={properties.zoningCode} />
        <Field label="Future Land Use" value={fluLine} />
        <Field label="Designated Opportunity Zone" value={oz.inZone == null ? null : oz.inZone ? `Yes · ${properties.opportunityZone?.tractName || properties.opportunityZone?.tractGeoid}` : "No"} />
        <Field
          label="OZ 2.0"
          value={
            oz2.eligible == null
              ? null
              : oz2.eligible
                ? `${oz2.statusChip ?? (oz2.rural === false ? "Eligible, not rural" : "Eligible")} · GEOID ${properties.oz2Eligibility?.tractGeoid ?? "unknown"}`
                : "Not eligible"
          }
        />
        <Field label="Last sale" value={formatSale(properties.lastSale)} />
        <Field label="Qualified sale" value={properties.lastSale.qualified} />
        <Field label="Market value" value={formatUsd(properties.tax.marketValue)} />
        <Field label="Assessed value" value={formatUsd(properties.tax.assessedValue)} />
        <Field label="Taxable value" value={formatUsd(properties.tax.taxableValue)} />
        <Field label="Taxes" value={formatUsd(properties.tax.taxes)} />
      </dl>

      {rezoning.isCandidate ? (
        <div className="mt-3 rounded-2xl border border-clay-400/40 bg-clay-500/10 p-3 text-sm">
          <p className="text-[11px] uppercase tracking-[0.14em] text-clay-400">Rezoning candidate</p>
          <p className="mt-1 font-medium text-white">{rezoning.label}</p>
          <p className="mt-1 text-ink-100">{rezoning.reason}</p>
        </div>
      ) : filters.landUseFilter === "rezoning" ? (
        <div className="mt-3 rounded-2xl border border-white/10 bg-ink-800/80 p-3 text-sm">
          <p className="text-[11px] uppercase tracking-[0.14em] text-ink-500">Rezoning</p>
          <p className="mt-1 text-ink-100">{rezoning.reason}</p>
        </div>
      ) : null}

      <div className="mt-5 rounded-2xl border border-white/10 bg-ink-800/80 p-3 text-sm">
        <p className="text-[11px] uppercase tracking-[0.14em] text-ink-500">Zoning</p>
        <p className="mt-1 text-ink-100">{zoning.reason}</p>
      </div>
      <div className="mt-3 rounded-2xl border border-white/10 bg-ink-800/80 p-3 text-sm">
        <p className="text-[11px] uppercase tracking-[0.14em] text-ink-500">Future Land Use</p>
        <p className="mt-1 text-ink-100">{flu.reason}</p>
      </div>
      <div className="mt-3 rounded-2xl border border-white/10 bg-ink-800/80 p-3 text-sm">
        <p className="text-[11px] uppercase tracking-[0.14em] text-ink-500">Designated Opportunity Zone</p>
        <p className="mt-1 text-ink-100">{oz.detail}</p>
      </div>
      <div className="mt-3 rounded-2xl border border-moss-400/30 bg-ink-800/80 p-3 text-sm">
        <p className="text-[11px] uppercase tracking-[0.14em] text-moss-400">OZ 2.0 nomination</p>
        <p className="mt-1 font-medium text-white">{oz2.statusChip ?? oz2.label}</p>
        <p className="mt-1 text-ink-100">{oz2.detail}</p>
      </div>

      <div className="mt-4 space-y-3">
        <Field label="Owner mailing address" value={mailing} />
        <Field
          label={filters.incomeGeography === "tract" ? "Tract median household income" : "Block group median household income"}
          value={income?.medianHouseholdIncome != null ? `${formatUsd(income.medianHouseholdIncome)}\n${income.name}` : income?.name}
        />
        <Field
          label="Nearest FDOT AADT"
          value={
            properties.nearestRoad?.aadt != null
              ? `${formatNumber(properties.nearestRoad.aadt)} vehicles/day (${properties.nearestRoad.year ?? "year n/a"})\n${formatRoadLabel(properties.nearestRoad)}\n${properties.nearestRoad.distanceMeters != null ? `${formatNumber(properties.nearestRoad.distanceMeters)} m from centroid` : ""}`
              : null
          }
        />
      </div>

      <div className="mt-5 space-y-2 text-sm">
        <p className="text-[11px] uppercase tracking-[0.14em] text-ink-500">Public contact paths</p>
        <a className="block text-moss-400 underline-offset-2 hover:underline" href={appraiser.href} target="_blank" rel="noreferrer">
          {appraiser.label}
        </a>
        {entity && properties.ownerName && floridaRecords ? (
          <a className="block text-moss-400 underline-offset-2 hover:underline" href={sunbizSearchUrl(properties.ownerName)} target="_blank" rel="noreferrer">
            Search Florida Sunbiz for LLC / corporate principals
          </a>
        ) : floridaRecords ? (
          <p className="text-ink-300">Owner does not look like an LLC/corp in the assessor name field. Sunbiz search is skipped.</p>
        ) : (
          <p className="text-ink-300">Phone numbers and email addresses are not collected from the public parcel roll.</p>
        )}
        {properties.countyFips === "12095" || !properties.countyFips ? (
          <a className="block text-moss-400 underline-offset-2 hover:underline" href={comptrollerRecordsUrl()} target="_blank" rel="noreferrer">
            Orange County Comptroller official records
          </a>
        ) : null}
        {gaps ? (
          <p className="text-xs text-ink-500">Data gaps for this county extract: {gaps.join("; ")}</p>
        ) : null}
        <p className="text-xs text-ink-500">
          Contact paths are mailing address plus official search links only. This app does not scrape or invent emails or
          phone numbers.
        </p>
      </div>
    </aside>
  );
}
