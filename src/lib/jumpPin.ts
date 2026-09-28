/** Temporary marker for a jump-to search. One pin at a time. */

export const JUMP_PIN_TTL_MS = 60_000;
export const JUMP_PIN_FADE_MS = 500;

/** Mid blue from the Catalyst mark, light enough to read on the dark basemap. */
export const JUMP_PIN_COLOR = "#0a5694";

/**
 * The teardrop and the dismiss control take clicks. The address label does not,
 * so parcels and tracts under the text stay clickable.
 */
export const JUMP_PIN_HIT = {
  root: "none",
  body: "none",
  pin: "auto",
  label: "none",
  close: "auto",
} as const;

export type JumpPin = {
  lng: number;
  lat: number;
  label: string;
  key: number;
};

export type JumpPinState =
  | { status: "idle" }
  | { status: "pending"; pin: JumpPin }
  | { status: "visible"; pin: JumpPin; shownAt: number }
  | { status: "fading"; pin: JumpPin; shownAt: number };

export type JumpPinAction =
  | { type: "search"; pin: JumpPin }
  | { type: "fly-end"; now: number }
  | { type: "dismiss" }
  | { type: "tick"; now: number };

export const IDLE_JUMP_PIN: JumpPinState = { status: "idle" };

export function formatJumpPinLabel(query: string): string {
  return query.trim().replace(/\s+/g, " ");
}

export function jumpPinFromQuery(query: string, point: { lng: number; lat: number }, key: number): JumpPin {
  return { lng: point.lng, lat: point.lat, key, label: formatJumpPinLabel(query) };
}

/**
 * Pending until the camera move ends, then visible for 60s, then a short fade.
 * A new search replaces the current pin. Dismiss (the label x, or Escape) clears it.
 * A fly-end that arrives after dismiss does not bring the pin back.
 */
export function reduceJumpPin(state: JumpPinState, action: JumpPinAction): JumpPinState {
  switch (action.type) {
    case "search":
      return { status: "pending", pin: action.pin };
    case "fly-end":
      if (state.status !== "pending") return state;
      return { status: "visible", pin: state.pin, shownAt: action.now };
    case "dismiss":
      return IDLE_JUMP_PIN;
    case "tick": {
      if (state.status !== "visible" && state.status !== "fading") return state;
      const elapsed = action.now - state.shownAt;
      if (elapsed >= JUMP_PIN_TTL_MS + JUMP_PIN_FADE_MS) return IDLE_JUMP_PIN;
      if (elapsed >= JUMP_PIN_TTL_MS) return { status: "fading", pin: state.pin, shownAt: state.shownAt };
      return state;
    }
    default:
      return state;
  }
}

function svgEl(doc: Document, name: string, attrs: Record<string, string>): SVGElement {
  const el = doc.createElementNS("http://www.w3.org/2000/svg", name);
  for (const [key, value] of Object.entries(attrs)) el.setAttribute(key, value);
  return el;
}

/** DOM for a MapLibre Marker. The root is the marker element; anchor its bottom on the point. */
export function paintJumpPinElement(doc: Document, label: string, onDismiss: () => void): HTMLElement {
  const root = doc.createElement("div");
  root.className = "jump-pin";
  root.dataset.jumpPin = "true";
  root.style.pointerEvents = JUMP_PIN_HIT.root;

  const body = doc.createElement("div");
  body.className = "jump-pin-body";
  body.style.pointerEvents = JUMP_PIN_HIT.body;

  const pin = svgEl(doc, "svg", {
    class: "jump-pin-mark",
    viewBox: "0 0 32 44",
    width: "28",
    height: "38",
    "aria-hidden": "true",
    focusable: "false",
  });
  pin.style.pointerEvents = JUMP_PIN_HIT.pin;
  pin.append(
    svgEl(doc, "path", {
      d: "M16 41.2C16 41.2 4.2 25.6 4.2 16.2 4.2 9.4 9.5 3.8 16 3.8s11.8 5.6 11.8 12.4C27.8 25.6 16 41.2 16 41.2z",
      fill: JUMP_PIN_COLOR,
      stroke: "#ffffff",
      "stroke-width": "2.4",
      "stroke-linejoin": "round",
    }),
    svgEl(doc, "circle", { cx: "16", cy: "16", r: "4.2", fill: "#ffffff" }),
  );

  const labelEl = doc.createElement("div");
  labelEl.className = "jump-pin-label";
  labelEl.style.pointerEvents = JUMP_PIN_HIT.label;

  const text = doc.createElement("span");
  text.textContent = label;
  text.title = label;

  const close = doc.createElement("button");
  close.type = "button";
  close.className = "jump-pin-close";
  close.style.pointerEvents = JUMP_PIN_HIT.close;
  close.setAttribute("aria-label", "Dismiss searched location");
  close.textContent = "×";
  close.addEventListener("click", (event) => {
    event.preventDefault();
    event.stopPropagation();
    onDismiss();
  });

  labelEl.append(text, close);
  body.append(pin, labelEl);
  root.append(body);
  return root;
}
