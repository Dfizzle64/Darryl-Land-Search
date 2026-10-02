"use client";

import { useEffect, useRef, useState } from "react";
import {
  comptrollerRecordsUrl,
  entitySearchLink,
  formatAcres,
  formatMailing,
  aadtEmptyMessage,
  aadtFieldLabel,
  formatNumber,
  formatParcelPlace,
  formatRoadLabel,
  formatSale,
  formatUsd,
  vintageFieldLabel,
  incomeEmptyMessage,
  isEntityOwner,
  isFloridaParcel,
  lakeAltKey,
  parcelIdLabel,
  showAadtField,
  missingPublicParcelValue,
  parcelAppraiserUrl,
} from "@/lib/format";
import { mailingGap, type ScreeningPoint } from "@/lib/screening";
import { ScreeningDetails } from "./ScreeningDetails";
import { describeFluMatch } from "@/lib/flu";
import { describeRezoningCandidate } from "@/lib/filters";
import { describeOpportunityZone, describeOz2Eligibility, oz2ParcelFieldValue } from "@/lib/opportunityZone";
import type { FilterState, FluConfig, ParcelFeature, TractClassView, ZoningConfig } from "@/lib/types";
import { googleMapsUrl, OZ2_NOT_JOINED, SitePdfError, type TractGeometryRecord } from "@/lib/sitePdf";
import { useSheetExpanded } from "./useSheetExpanded";
import type { TractRentFields } from "@/lib/tractRent";
import { fluEmptyForPolk, zoningEmptyForPolk } from "@/lib/polkMunicipal";
import { fluEmptyForSeminole, zoningEmptyForSeminole } from "@/lib/seminoleMunicipal";
import { fluEmptyForMartinIrc, zoningEmptyForMartinIrc } from "@/lib/martinIrcMunicipal";
import { fluEmptyForPanhandle, zoningEmptyForPanhandle } from "@/lib/panhandleMunicipal";
import { fluEmptyForCharlotte, zoningEmptyForCharlotte } from "@/lib/charlotteMunicipal";
import { fluEmptyForManateeSarasota, zoningEmptyForManateeSarasota } from "@/lib/manateeSarasotaMunicipal";
import { brevardFluReason, formatJoinedZoning } from "@/lib/brevardMunicipal";
import { fluEmptyForMunicipal, zoningEmptyForCounty } from "@/lib/volusiaFlaglerMunicipal";
import { jurisdictionGisViewers } from "@/lib/jurisdictionLinks";
import { fluEmptyForSouthFlorida, saleEmptyForSouthFlorida, zoningEmptyForSouthFlorida } from "@/lib/southFlorida";
import { describeZoningMatch } from "@/lib/zoning";

type ParcelDrawerProps = {
  parcel: ParcelFeature | null;
  zoningConfig: ZoningConfig;
  fluConfig: FluConfig;
  filters: FilterState;
  screeningPoint?: ScreeningPoint | null;
  screeningStatus?: "idle" | "loading" | "error";
  /** Tract polygon for this parcel's 2020 GEOID, when the app has one. */
  pdfTract?: TractGeometryRecord | null;
  /** Rent-layer values for that GEOID. Missing series stay dashes in the PDF. */
  pdfRent?: Partial<TractRentFields> | null;
  /** Eligible-tract overlay. Off keeps the tract tint off the PDF map. */
  showTracts?: boolean;
  tractClass?: TractClassView;
  onClose: () => void;
  /** `pane` fills the desktop details rail. `page` is the standalone column / mobile sheet. */
  layout?: "page" | "pane";
};

/** City-prefixed districts are `{place}:{code}` with no space. Orange districts stay the raw code. */
function formatZoningWithCity(code: string | null, district: string | null): string | null {
  if (!code) return null;
  const suffix = `:${code}`;
  if (district?.endsWith(suffix)) {
    const place = district.slice(0, -suffix.length);
    if (place && !place.includes(":")) return `${code} · ${place}`;
  }
  return code;
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
  screeningPoint = null,
  screeningStatus = "idle",
  pdfTract = null,
  pdfRent = null,
  showTracts = true,
  tractClass = "both",
  onClose,
  layout = "page",
}: ParcelDrawerProps) {
  const pane = layout === "pane";
  const { expanded, handleProps } = useSheetExpanded(parcel?.properties.id ?? null);
  const [exporting, setExporting] = useState(false);
  const [exportError, setExportError] = useState<string | null>(null);
  const exportToken = useRef(0);
  const parcelKey = parcel?.properties.id ?? null;
  useEffect(() => {
    setExportError(null);
  }, [parcelKey]);
  if (!parcel) {
    return (
      <aside className={pane ? "h-full overflow-y-auto bg-ink-900/80 p-5" : "hidden"}>
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
  const florida = isFloridaParcel(properties.state);
  const orangeCounty = properties.countyFips === "12095" || properties.countyName === "Orange";
  const incomeEmpty = incomeEmptyMessage(filters.incomeGeography, income, orangeCounty);
  const aadtKnown = properties.nearestRoad?.aadt != null;
  const aadtEmpty = aadtEmptyMessage(properties.state);
  const dekalb = properties.countyFips === "13089";
  const zoningEmpty = zoningEmptyForSouthFlorida(
    properties.countyFips,
    zoningEmptyForPanhandle(
    properties.countyFips,
    zoningEmptyForCharlotte(
      properties.countyFips,
      zoningEmptyForManateeSarasota(
        properties.countyFips,
        properties.countyFips === "12009"
          ? "No city zoning layer covers this parcel."
          : zoningEmptyForMartinIrc(
              properties.countyFips,
              zoningEmptyForSeminole(
                properties.countyFips,
                zoningEmptyForPolk(
                  properties.countyFips,
                  zoningEmptyForCounty(properties.countyFips, missingPublicParcelValue("zoning", properties.countyFips)),
                ),
              ),
            ),
      ),
    ),
    ),
  );
  const zoningLine =
    properties.countyFips === "12009"
      ? formatJoinedZoning(properties.zoningCode, properties.municipal)
      : properties.zoningCode
        ? properties.municipal?.zoningLabel && properties.municipal.zoningLabel !== properties.zoningCode
          ? `${properties.zoningCode} — ${properties.municipal.zoningLabel}`
          : formatZoningWithCity(properties.zoningCode, properties.zoningDistrict)
        : null;
  const mailing = formatMailing(properties.mailingAddress) ?? mailingGap(properties.mailingAddress);
  const entityName = isEntityOwner(properties.ownerName)
    ? properties.ownerName
    : isEntityOwner(properties.ownerName2)
      ? properties.ownerName2
      : null;
  const entityLink = entityName ? entitySearchLink(properties.state, entityName, properties.countyFips) : null;
  const fluLine = properties.flu?.code
    ? `${properties.flu.label || properties.flu.code}${properties.flu.jurisdiction ? ` · ${properties.flu.jurisdiction}` : ""}${
        properties.countyFips === "12009" && properties.municipal?.unofficial
          ? ` · unofficial ${properties.municipal.vintage || "vintage"}`
          : ""
      }`
    : null;
  const placeLine = formatParcelPlace(properties);
  const appraiser = parcelAppraiserUrl({
    parcelId: properties.parcelId,
    countyFips: properties.countyFips,
    appraiserUrl: properties.appraiserUrl,
  });
  const gisViewers = jurisdictionGisViewers({
    countyFips: properties.countyFips,
    gisViewerUrl: properties.gisViewerUrl,
    gisViewerUrlAlt: properties.gisViewerUrlAlt,
  });
  const gaps = properties.dataGaps?.length ? properties.dataGaps : null;

  const [lon, lat] = properties.centroid;
  const mapsHref = Number.isFinite(lat) && Number.isFinite(lon) ? googleMapsUrl(lat, lon) : null;
  const ozPeek =
    oz.inZone == null ? "Designated QOZ unknown" : oz.inZone ? "Designated QOZ" : "Not a designated QOZ";
  const oz2Peek = oz2.statusChip ?? oz2.label;

  return (
    <aside
      data-detail-sheet={pane ? "pane" : expanded ? "expanded" : "peek"}
      className={pane ? "drawer-scroll h-full overflow-y-auto bg-ink-900 p-5" : `drawer-scroll sheet-page absolute inset-x-0 bottom-0 z-20 max-h-[70vh] overflow-y-auto rounded-t-3xl border border-white/10 bg-ink-900 p-5 shadow-2xl${expanded ? " sheet-expanded" : ""}`}
    >
      {pane ? null : (
        <button
          type="button"
          className="sheet-handle mx-auto mb-2 h-11 w-full items-center justify-center"
          aria-expanded={expanded}
          aria-label={expanded ? "Show less" : "Expand details"}
          {...handleProps}
        >
          <span className="flex flex-col items-center gap-1 text-[11px] uppercase tracking-[0.14em] text-ink-300">
            <span className="h-1.5 w-10 rounded-full bg-white/40" />
            {expanded ? "Show less" : "Details"}
          </span>
        </button>
      )}
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-[11px] uppercase tracking-[0.14em] text-ink-500 max-[767px]:hidden">{parcelIdLabel(properties.countyFips)}</p>
          <p className="mt-0.5 break-all font-mono text-sm text-clay-300 max-[767px]:hidden">{properties.parcelId}</p>
          {properties.countyFips === "12069" && lakeAltKey(properties.appraiserUrl) ? (
            <p className="mt-1 text-[11px] uppercase tracking-[0.14em] text-ink-500">
              Alt Key <span className="font-mono normal-case tracking-normal text-clay-300">{lakeAltKey(properties.appraiserUrl)}</span>
            </p>
          ) : null}
          <h2 className="mt-1 font-display text-2xl leading-tight text-white max-[767px]:line-clamp-2 max-[767px]:text-xl">
            {properties.situsAddress || missingPublicParcelValue("situs")}
          </h2>
          <p className="text-sm text-ink-300">{placeLine}</p>
          <div data-sheet-actions className="max-[767px]:mt-3 max-[767px]:grid max-[767px]:grid-cols-2 max-[767px]:gap-2">
          {appraiser.href ? (
            <a className="dls-hit mt-2 inline-block text-sm text-moss-400 underline-offset-2 hover:underline max-[767px]:mt-0 max-[767px]:flex max-[767px]:items-center max-[767px]:justify-center max-[767px]:rounded-xl max-[767px]:border max-[767px]:border-white/15 max-[767px]:bg-ink-800 max-[767px]:px-2 max-[767px]:text-center max-[767px]:text-xs max-[767px]:font-semibold max-[767px]:text-white max-[767px]:no-underline" href={appraiser.href} target="_blank" rel="noreferrer">
              {appraiser.label}
            </a>
          ) : (
            <p className="mt-2 text-sm text-ink-500">Property appraiser not available</p>
          )}
          {gisViewers ? (
            <>
              <a className="dls-hit mt-1 block text-sm text-moss-400 underline-offset-2 hover:underline max-[767px]:mt-0 max-[767px]:flex max-[767px]:items-center max-[767px]:justify-center max-[767px]:rounded-xl max-[767px]:border max-[767px]:border-white/15 max-[767px]:bg-ink-800 max-[767px]:px-2 max-[767px]:text-center max-[767px]:text-xs max-[767px]:font-semibold max-[767px]:text-white max-[767px]:no-underline" href={gisViewers.primary.href} target="_blank" rel="noreferrer">
                {gisViewers.primary.label}
              </a>
              {gisViewers.alt ? (
                <a className="dls-hit mt-1 block text-sm text-moss-400 underline-offset-2 hover:underline max-[767px]:mt-0 max-[767px]:flex max-[767px]:items-center max-[767px]:justify-center max-[767px]:rounded-xl max-[767px]:border max-[767px]:border-white/15 max-[767px]:bg-ink-800 max-[767px]:px-2 max-[767px]:text-center max-[767px]:text-xs max-[767px]:font-semibold max-[767px]:text-white max-[767px]:no-underline" href={gisViewers.alt.href} target="_blank" rel="noreferrer">
                  {gisViewers.alt.label}
                </a>
              ) : null}
            </>
          ) : null}
          {mapsHref ? (
            <a className="dls-narrow dls-hit items-center justify-center rounded-xl border border-white/15 bg-ink-800 px-2 text-center text-xs font-semibold text-white" href={mapsHref} target="_blank" rel="noreferrer">
              Google Maps
            </a>
          ) : null}
          <button
            type="button"
            data-export-pdf
            onClick={() => {
              const token = exportToken.current + 1;
              exportToken.current = token;
              setExporting(true);
              setExportError(null);
              void import("@/lib/sitePdfExport")
                .then(({ downloadSitePdf }) =>
                  downloadSitePdf({
                    parcel,
                    zoningLine,
                    fluLine,
                    screeningPoint,
                    screeningStatus,
                    rent: pdfRent,
                    eligibleTract: pdfTract,
                    showTracts,
                    tractClass,
                    filters,
                  }),
                )
                .catch((error: unknown) => {
                  if (exportToken.current !== token) return;
                  setExportError(
                    error instanceof SitePdfError ? error.message : "Could not export the PDF. Try again.",
                  );
                })
                .finally(() => {
                  if (exportToken.current === token) setExporting(false);
                });
            }}
            disabled={exporting}
            className="dls-hit mt-3 inline-flex rounded-full border border-white/15 bg-ink-800 px-3 py-1 text-sm text-white hover:bg-ink-700 disabled:opacity-60 max-[767px]:mt-0 max-[767px]:items-center max-[767px]:justify-center max-[767px]:rounded-xl max-[767px]:text-xs max-[767px]:font-semibold"
          >
            {exporting ? "Exporting PDF…" : "Export PDF"}
          </button>
          {exportError ? (
            <p role="alert" className="mt-1 max-w-[16rem] text-xs leading-snug text-clay-300 max-[767px]:col-span-2 max-[767px]:text-sm">
              {exportError}
            </p>
          ) : null}
          </div>
        </div>
        <button type="button" onClick={onClose} className="dls-hit shrink-0 rounded-full border border-white/15 px-3 py-1 text-sm">
          Close
        </button>
      </div>

      <dl data-sheet-peek className="sheet-peek-facts mt-4 grid grid-cols-2 gap-3 md:hidden">
        <Field label="Acreage" value={formatAcres(properties.acreage)} />
        <Field label="Owner" value={[properties.ownerName, properties.ownerName2].filter(Boolean).join("\n")} />
        <div className="col-span-2">
          <Field label="Opportunity Zone" value={`${ozPeek} · ${oz2Peek}`} />
        </div>
      </dl>

      <div className="sheet-rest">
      <dl className="mt-5 grid grid-cols-2 gap-4">
        <Field label="Owner" value={[properties.ownerName, properties.ownerName2].filter(Boolean).join("\n")} />
        <Field label="Property name" value={properties.propertyName} empty={missingPublicParcelValue("propertyName")} />
        <Field label="Acreage" value={formatAcres(properties.acreage)} />
        {dekalb ? (
          <Field label="Tax district" value={properties.dorCode} empty="Tax district not on this parcel" />
        ) : null}
        <Field label="Zoning" value={zoningLine} empty={zoningEmpty} />
        <Field
          label="Future Land Use"
          value={fluLine}
          empty={fluEmptyForSouthFlorida(
            properties.countyFips,
            fluEmptyForPanhandle(
            properties.countyFips,
            fluEmptyForCharlotte(
            properties.countyFips,
            fluEmptyForManateeSarasota(
            properties.countyFips,
            properties.countyFips === "12009"
            ? brevardFluReason("", null, properties.municipal, "12009")
            : fluEmptyForMartinIrc(
            properties.countyFips,
            fluEmptyForSeminole(
            properties.countyFips,
            fluEmptyForPolk(
            properties.countyFips,
            properties.municipal?.fluGap ? fluEmptyForMunicipal(properties.municipal.fluGap) : null,
            dekalb ? "No future land use joined for this parcel" : "Not joined for this county",
            ),
            ),
            ),
            ),
            ),
            ),
          )}
        />
        <Field
          label="Designated Opportunity Zone"
          value={
            oz.inZone == null
              ? null
              : oz.inZone
                ? `Yes · ${properties.opportunityZone?.tractName || properties.opportunityZone?.tractGeoid}`
                : "No — centroid is outside the joined designated QOZ tracts"
          }
          empty={missingPublicParcelValue("designatedOz")}
        />
        <Field
          label="OZ 2.0"
          value={oz2ParcelFieldValue(oz2, properties.oz2Eligibility?.tractGeoid)}
          empty={OZ2_NOT_JOINED}
        />
        <Field
          label={vintageFieldLabel("Last sale", properties.lastSale.vintage, formatSale(properties.lastSale) != null)}
          value={formatSale(properties.lastSale)}
          empty={saleEmptyForSouthFlorida(properties.countyFips) ?? missingPublicParcelValue("sale")}
        />
        <Field
          label="Qualified sale"
          value={properties.lastSale.qualified}
          empty={missingPublicParcelValue("saleQualified")}
        />
        <Field
          label={vintageFieldLabel(
            "Market value",
            properties.tax.vintage,
            properties.tax.marketValue != null && properties.tax.marketValue > 0,
          )}
          value={formatUsd(properties.tax.marketValue)}
        />
        <Field
          label={vintageFieldLabel(
            "Assessed value",
            properties.tax.vintage,
            properties.tax.assessedValue != null && properties.tax.assessedValue > 0,
          )}
          value={formatUsd(properties.tax.assessedValue)}
        />
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
        {properties.zoningOverlay ? (
          <p className="mt-2 text-ink-300">
            Overlay: {properties.zoningOverlay}. This note is not the base zoning district.
          </p>
        ) : null}
      </div>
      <div className="mt-3 rounded-2xl border border-white/10 bg-ink-800/80 p-3 text-sm">
        <p className="text-[11px] uppercase tracking-[0.14em] text-ink-500">Future Land Use</p>
        <p className="mt-1 text-ink-100">
          {brevardFluReason(
            !properties.flu?.code && properties.municipal?.fluGap ? properties.municipal.fluGap : flu.reason,
            properties.flu?.code,
            properties.municipal,
            properties.countyFips,
          )}
        </p>
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
              ? `${formatUsd(income.medianHouseholdIncome)}${income.vintage ? ` · ${income.vintage}` : ""}\n${income.name ?? ""}`
              : null
          }
          empty={incomeEmpty}
        />
        {showAadtField(properties.state, aadtKnown) ? (
          <Field
            label={aadtFieldLabel(properties.state)}
            value={
              aadtKnown
                ? `${formatNumber(properties.nearestRoad?.aadt)} vehicles/day (${properties.nearestRoad?.year ?? "year n/a"})\n${formatRoadLabel(properties.nearestRoad, florida ? "FDOT" : null)}\n${properties.nearestRoad?.distanceMeters != null ? `${formatNumber(properties.nearestRoad.distanceMeters)} m from centroid` : ""}`
                : null
            }
            empty={aadtEmpty}
          />
        ) : null}
      </div>

      <div className="mt-5 space-y-2 text-sm">
        <p className="text-[11px] uppercase tracking-[0.14em] text-ink-500">Public contact paths</p>
        {appraiser.href ? (
          <a className="block text-moss-400 underline-offset-2 hover:underline" href={appraiser.href} target="_blank" rel="noreferrer">
            {appraiser.label}
          </a>
        ) : (
          <p className="text-ink-500">Property appraiser not available</p>
        )}
        {gisViewers ? (
          <>
            <a className="block text-moss-400 underline-offset-2 hover:underline" href={gisViewers.primary.href} target="_blank" rel="noreferrer">
              {gisViewers.primary.label}
            </a>
            {gisViewers.alt ? (
              <a className="block text-moss-400 underline-offset-2 hover:underline" href={gisViewers.alt.href} target="_blank" rel="noreferrer">
                {gisViewers.alt.label}
              </a>
            ) : null}
          </>
        ) : null}
        {entityLink ? (
          <a className="block text-moss-400 underline-offset-2 hover:underline" href={entityLink.href} target="_blank" rel="noreferrer">
            {entityLink.label}
            {entityLink.prefilled ? "" : " (name is not prefilled)"}
          </a>
        ) : entityName ? (
          <p className="text-ink-300">This owner looks like an entity, but no secretary-of-state search is cataloged for this state.</p>
        ) : (
          <p className="text-ink-300">Owner does not look like an LLC or corporation in the assessor name field. Business-entity search is skipped.</p>
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
          Contact paths are the public mailing address plus official search links. This app does not scrape or invent emails
          or phone numbers.
        </p>
      </div>
      <ScreeningDetails point={screeningPoint} status={screeningStatus} />
      </div>
    </aside>
  );
}
