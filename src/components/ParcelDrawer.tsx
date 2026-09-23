"use client";

import {
  comptrollerRecordsUrl,
  formatAcres,
  formatMailing,
  formatNumber,
  formatParcelPlace,
  formatRoadLabel,
  formatSale,
  formatUsd,
  isEntityOwner,
  parcelPublicLinks,
  sunbizSearchUrl,
} from "@/lib/format";
import { describeFluMatch, isNashvilleNextPolicy } from "@/lib/flu";
import { describeRezoningCandidate } from "@/lib/filters";
import { describeOpportunityZone, describeOz2Eligibility } from "@/lib/opportunityZone";
import type { FilterState, FluConfig, ParcelFeature, ParcelProperties, ZoningConfig } from "@/lib/types";
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

function davidsonZoningReason(properties: ParcelProperties): string | null {
  if (properties.countyFips !== "47037") return null;
  const city = properties.jurisdictionCode;
  if (properties.zoningSource === "satellite-zoning-rest-gap") {
    return `${city} keeps its own zoning code. No public zoning FeatureServer was found, so city zoning stays blank. The Metro parcel attribute and *ZZ placeholders are not this city's district.`;
  }
  if (properties.zoningSource === "goodlettsville-unmatched") {
    return "This parcel is inside Goodlettsville, but no ZONECLASS polygon from ZONINGARGISMAP layer 2 intersects it. City zoning stays blank.";
  }
  if (properties.zoningSource === "goodlettsville-zoningargismap-2") {
    const desc = properties.zoningDescription ? ` ${properties.zoningDescription}.` : "";
    return `Goodlettsville ZONECLASS ${properties.zoningCode}.${desc} Inside the satellite, this city layer replaces the Metro parcel attribute.`;
  }
  if (properties.zoningSource === "metro-parcel-attribute") {
    if (properties.parcelZoning && properties.parcelZoning !== properties.zoningCode) {
      return `Metro parcel Zoning attribute with *ZZ satellite placeholders removed (raw attribute ${properties.parcelZoning}). Metro Zoning/Zoning is not required for this value.`;
    }
    return "Metro parcel Zoning attribute, shown outside satellite cities. Metro Zoning/Zoning is rechecked at ingest and is not required.";
  }
  return null;
}

function Field({ label, value, empty }: { label: string; value: string | null | undefined; empty?: string }) {
  return (
    <div>
      <dt className="text-[11px] uppercase tracking-[0.14em] text-ink-500">{label}</dt>
      <dd className="mt-1 whitespace-pre-line text-sm text-white">{value?.trim() ? value : empty ?? "Not available"}</dd>
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
  const florida = !properties.state || properties.state === "Florida";
  const orangeCounty = properties.countyFips === "12095" || properties.countyName === "Orange";
  const incomeEmpty = !florida
    ? "No ACS join outside Florida"
    : filters.incomeGeography === "blockGroup"
      ? orangeCounty
        ? "No block-group income for this location"
        : "Block-group income is joined for Orange County only"
      : income?.geoid
        ? "ACS did not publish a median for this tract"
        : "No ACS tract join for this location";
  const aadtEmpty = florida
    ? "No FDOT count segment within 15 km"
    : "FDOT AADT is Florida only";
  const davidson = properties.countyFips === "47037";
  const satelliteCity =
    davidson && !!properties.jurisdictionCode && properties.jurisdictionCode !== "Metro Nashville";
  const zoningEmpty = satelliteCity
    ? properties.zoningSource === "goodlettsville-unmatched"
      ? "No Goodlettsville ZONECLASS intersects this parcel"
      : `No public zoning layer for ${properties.jurisdictionCode}`
    : properties.countyFips === "12095"
      ? "Not on the OCPA parcel"
      : "Not in this county's public parcel extract";
  const mailing = formatMailing(properties.mailingAddress);
  const entity = isEntityOwner(properties.ownerName) || isEntityOwner(properties.ownerName2);
  const nashvillePolicy = isNashvilleNextPolicy(properties.flu) || (davidson && !satelliteCity);
  const fluLine = properties.flu?.code
    ? nashvillePolicy
      ? properties.flu.label || properties.flu.code
      : `${properties.flu.label || properties.flu.code}${properties.flu.jurisdiction ? ` · ${properties.flu.jurisdiction}` : ""}`
    : null;
  const fluReason = satelliteCity
    ? `${properties.jurisdictionCode} has no public future-land-use layer. NashvilleNext CCM is Metro guidance and is not this city's comprehensive plan, so future land use stays blank.`
    : davidson && !properties.flu?.code
      ? "No NashvilleNext community character polygon intersects this parcel. CCM is policy guidance, not an entitlement. A missing join is not a Future Land Use designation."
      : flu.reason;
  const zoningReason = davidsonZoningReason(properties) ?? zoning.reason;
  const placeLine = formatParcelPlace(properties);
  const publicLinks = parcelPublicLinks({
    parcelId: properties.parcelId,
    countyFips: properties.countyFips,
    appraiserUrl: properties.appraiserUrl,
  });
  const altIds = [
    properties.stanpar && properties.stanpar !== properties.parcelId ? `STANPAR ${properties.stanpar}` : null,
    properties.parId ? `ParID ${properties.parId}` : null,
  ]
    .filter(Boolean)
    .join(" · ");
  const acreageValue =
    properties.deededAcreage != null && properties.deededAcreage !== properties.acreage
      ? `${formatAcres(properties.acreage)}\nDeeded ${formatAcres(properties.deededAcreage)}`
      : formatAcres(properties.acreage);
  const appraisalSplit = properties.tax.landAppraised != null || properties.tax.improvementAppraised != null;
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
        <Field label="Acreage" value={acreageValue} />
        {davidson ? <Field label="Jurisdiction" value={properties.jurisdictionCode} /> : null}
        <Field label="Zoning" value={properties.zoningCode} empty={zoningEmpty} />
        <Field
          label={nashvillePolicy ? "Community character policy" : "Future Land Use"}
          value={fluLine}
          empty={
            satelliteCity
              ? "No public city comprehensive plan"
              : nashvillePolicy
                ? "No NashvilleNext policy intersects this parcel"
                : "Not joined for this county"
          }
        />
        {altIds ? <Field label="Alternate parcel ids" value={altIds} /> : null}
        {properties.zoningDescription ? <Field label="Zoning description" value={properties.zoningDescription} /> : null}
        {properties.parcelZoning && properties.parcelZoning !== properties.zoningCode ? (
          <Field label="Metro parcel zoning attribute" value={properties.parcelZoning} />
        ) : null}
        {properties.landUse ? <Field label="Land use" value={properties.landUse} /> : null}
        {properties.zoningOverlays?.length ? (
          <Field label="Zoning overlays (not base zone)" value={properties.zoningOverlays.join("\n")} />
        ) : null}
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
        <Field label={appraisalSplit ? "Total appraised" : "Market value"} value={formatUsd(properties.tax.marketValue)} />
        <Field label={appraisalSplit ? "Total assessed" : "Assessed value"} value={formatUsd(properties.tax.assessedValue)} />
        {appraisalSplit ? (
          <>
            <Field label="Land appraised" value={formatUsd(properties.tax.landAppraised)} />
            <Field label="Improvement appraised" value={formatUsd(properties.tax.improvementAppraised)} />
            <Field label="Land assessed" value={formatUsd(properties.tax.landAssessed)} />
            <Field label="Improvement assessed" value={formatUsd(properties.tax.improvementAssessed)} />
          </>
        ) : null}
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
        <p className="mt-1 text-ink-100">{zoningReason}</p>
      </div>
      <div className="mt-3 rounded-2xl border border-white/10 bg-ink-800/80 p-3 text-sm">
        <p className="text-[11px] uppercase tracking-[0.14em] text-ink-500">
          {nashvillePolicy ? "Community character policy" : "Future Land Use"}
        </p>
        <p className="mt-1 text-ink-100">{fluReason}</p>
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
          value={
            income?.medianHouseholdIncome != null
              ? `${formatUsd(income.medianHouseholdIncome)}\n${income.name ?? ""}`
              : income?.name && income.medianHouseholdIncome == null
                ? null
                : income?.name
          }
          empty={incomeEmpty}
        />
        <Field
          label="Nearest FDOT AADT"
          value={
            properties.nearestRoad?.aadt != null
              ? `${formatNumber(properties.nearestRoad.aadt)} vehicles/day (${properties.nearestRoad.year ?? "year n/a"})\n${formatRoadLabel(properties.nearestRoad)}\n${properties.nearestRoad.distanceMeters != null ? `${formatNumber(properties.nearestRoad.distanceMeters)} m from centroid` : ""}`
              : null
          }
          empty={aadtEmpty}
        />
      </div>

      <div className="mt-5 space-y-2 text-sm">
        <p className="text-[11px] uppercase tracking-[0.14em] text-ink-500">Public contact paths</p>
        {publicLinks.map((link) => (
          <a key={link.href} className="block text-moss-400 underline-offset-2 hover:underline" href={link.href} target="_blank" rel="noreferrer">
            {link.label}
          </a>
        ))}
        {entity && properties.ownerName && florida ? (
          <a className="block text-moss-400 underline-offset-2 hover:underline" href={sunbizSearchUrl(properties.ownerName)} target="_blank" rel="noreferrer">
            Search Florida Sunbiz for LLC / corporate principals
          </a>
        ) : entity && properties.ownerName ? (
          <p className="text-ink-300">Owner looks like a company or trust. This county extract does not link a business-entity registry.</p>
        ) : (
          <p className="text-ink-300">Owner does not look like an LLC/corp in the assessor name field. Sunbiz search is skipped.</p>
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
