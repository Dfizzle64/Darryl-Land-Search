"use client";

import { useState } from "react";
import type { AoiLock } from "@/lib/aoi";
import type { BasemapMode } from "@/lib/basemap";
import type { LngLat } from "@/lib/measure";
import type { TractClassView } from "@/lib/types";
import { MeasureControl } from "./MeasureControl";

const BASEMAPS: { value: BasemapMode; label: string }[] = [
  { value: "streets", label: "Streets" },
  { value: "satellite", label: "Satellite" },
  { value: "dark", label: "Dark" },
];

type MobileMapToolsProps = {
  basemap: BasemapMode;
  onBasemap: (mode: BasemapMode) => void;
  showParcels: boolean;
  parcelLayerVisible: boolean;
  parcelHint: string;
  onToggleParcelLayer?: () => void;
  showOz2: boolean;
  tractToggleName: string;
  onToggleTractOverlay?: () => void;
  showCoverage: boolean;
  onToggleCoverage: () => void;
  measuring: boolean;
  measurePoints: LngLat[];
  onStartMeasure: () => void;
  onClearMeasure: () => void;
  onCancelMeasure: () => void;
  legendOpen: boolean;
  onToggleLegend: () => void;
  tractClass: TractClassView;
  onTractClass: (view: TractClassView) => void;
  showAoi: boolean;
  drawing: boolean;
  aoi: AoiLock | null;
  onDraw: () => void;
  onCancelDraw: () => void;
  onLockView: () => void;
  onClearAoi: () => void;
};

const hit =
  "dls-hit inline-flex items-center justify-center rounded-full border border-white px-2 text-xs font-semibold text-white";

export function MobileMapTools(props: MobileMapToolsProps) {
  const [basemapOpen, setBasemapOpen] = useState(false);
  const [overflowOpen, setOverflowOpen] = useState(false);
  const basemapLabel = BASEMAPS.find((option) => option.value === props.basemap)?.label ?? "Map";

  return (
    <div
      data-mobile-map-tools
      className="dls-narrow map-chrome absolute inset-x-0 top-2 z-30 items-start justify-between gap-2 px-[max(0.5rem,env(safe-area-inset-left))] pr-[max(0.5rem,env(safe-area-inset-right))]"
    >
      <div className="relative">
        <button
          type="button"
          className={`${hit} map-scrim h-11 min-w-11`}
          aria-expanded={basemapOpen}
          aria-label={`Basemap, ${basemapLabel}`}
          onClick={() => {
            setOverflowOpen(false);
            setBasemapOpen((current) => !current);
          }}
        >
          Map
        </button>
        {basemapOpen ? (
          <div className="absolute left-0 top-12 z-40 flex w-36 flex-col gap-1 rounded-2xl border border-white/15 bg-ink-950 p-1 shadow-2xl">
            {BASEMAPS.map((option) => (
              <button
                key={option.value}
                type="button"
                aria-pressed={props.basemap === option.value}
                className={`dls-hit rounded-xl px-3 text-left text-sm ${props.basemap === option.value ? "bg-white text-ink-950" : "text-white"}`}
                onClick={() => {
                  props.onBasemap(option.value);
                  setBasemapOpen(false);
                }}
              >
                {option.label}
              </button>
            ))}
          </div>
        ) : null}
      </div>

      <div className="flex items-start gap-1">
        <span
          data-mobile-zoom
          className="map-scrim inline-flex h-11 items-center rounded-full border px-2 text-xs font-medium text-white"
        >
          Zoom
        </span>
        <MeasureControl
          compact
          active={props.measuring}
          points={props.measurePoints}
          onStart={() => {
            setBasemapOpen(false);
            setOverflowOpen(false);
            props.onStartMeasure();
          }}
          onClear={props.onClearMeasure}
          onCancel={props.onCancelMeasure}
        />
        <button
          type="button"
          className={`${hit} map-scrim h-11 min-w-11`}
          aria-pressed={props.legendOpen}
          aria-label={props.legendOpen ? "Hide legend" : "Show legend"}
          onClick={() => {
            setBasemapOpen(false);
            setOverflowOpen(false);
            props.onToggleLegend();
          }}
        >
          Key
        </button>
        <div className="relative">
          <button
            type="button"
            className={`${hit} map-scrim h-11 min-w-11`}
            aria-expanded={overflowOpen}
            aria-label="Map tools"
            onClick={() => {
              setBasemapOpen(false);
              setOverflowOpen((current) => !current);
            }}
          >
            More
          </button>
          {overflowOpen ? (
            <div className="absolute right-0 top-12 z-40 max-h-[50dvh] w-[min(16rem,calc(100vw-5.5rem))] space-y-2 overflow-y-auto rounded-2xl border border-white/15 bg-ink-950 p-2 text-sm text-white shadow-2xl">
              <button
                type="button"
                className="dls-hit w-full rounded-xl border border-white/15 px-3 text-left"
                aria-pressed={props.showCoverage}
                onClick={props.onToggleCoverage}
              >
                {props.showCoverage ? "Hide coverage" : "Show coverage"}
              </button>
              {props.onToggleParcelLayer ? (
                <button
                  type="button"
                  className="dls-hit w-full rounded-xl border border-white/15 px-3 text-left"
                  aria-pressed={props.parcelLayerVisible}
                  onClick={props.onToggleParcelLayer}
                >
                  {props.parcelLayerVisible ? "Hide parcels" : "Show parcels"}
                </button>
              ) : null}
              {props.onToggleTractOverlay ? (
                <button
                  type="button"
                  className="dls-hit w-full rounded-xl border border-white/15 px-3 text-left"
                  aria-pressed={props.showOz2}
                  onClick={props.onToggleTractOverlay}
                >
                  {props.showOz2 ? `Hide ${props.tractToggleName}` : `Show ${props.tractToggleName}`}
                </button>
              ) : null}
              <div className="flex gap-1" role="group" aria-label="Rural or urban eligible tracts">
                {(
                  [
                    ["both", "Both"],
                    ["rural", "Rural"],
                    ["urban", "Urban"],
                  ] as const
                ).map(([value, label]) => (
                  <button
                    key={value}
                    type="button"
                    aria-pressed={props.tractClass === value}
                    className={`dls-hit flex-1 rounded-full border px-2 text-xs font-semibold ${
                      props.tractClass === value ? "bg-white text-ink-950" : "border-white/30 text-white"
                    }`}
                    onClick={() => props.onTractClass(value)}
                  >
                    {label}
                  </button>
                ))}
              </div>
              {props.showAoi ? (
                <div className="space-y-1">
                  <button
                    type="button"
                    className="dls-hit w-full rounded-xl border border-white/15 px-3 text-left"
                    aria-pressed={props.drawing}
                    onClick={props.drawing ? props.onCancelDraw : props.onDraw}
                  >
                    {props.drawing ? "Cancel draw" : "Draw area"}
                  </button>
                  <button
                    type="button"
                    className="dls-hit w-full rounded-xl border border-white/15 px-3 text-left"
                    onClick={props.onLockView}
                  >
                    Lock view
                  </button>
                  {props.aoi ? (
                    <button
                      type="button"
                      className="dls-hit w-full rounded-xl border border-white/15 px-3 text-left"
                      onClick={props.onClearAoi}
                    >
                      Clear area
                    </button>
                  ) : null}
                </div>
              ) : null}
              {props.showParcels && props.parcelHint ? (
                <p className="text-xs leading-snug text-ink-300">{props.parcelHint}</p>
              ) : null}
            </div>
          ) : null}
        </div>
      </div>
    </div>
  );
}
