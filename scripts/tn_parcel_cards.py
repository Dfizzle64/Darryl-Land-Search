"""Choose Tennessee parcel layers from research-card `use` and `parcelSetup`.

Older layers still carry `role: parcels`, including sibling backups that are
listed first on some cards. The ingest must not take that first parcels
layer. It selects the primary shapes/owner layer and the sale/value layer
by `use`, then checks those URLs against `parcelSetup`.

Drop a card in data/tn-parcel-cards and re-run. Endpoint choice does not
need a new per-county branch. The OIR layer has no acreage field, so a
null acreageField means the 5–150 filter is geodesic polygon area.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CARDS_DIR = ROOT / "data" / "tn-parcel-cards"

PRIMARY_USES = {"primary-geometry-owner", "primary-geometry-owner-sales-value"}
SALES_USE = "sales-value-join"
COMBINED_USE = "primary-geometry-owner-sales-value"


def normalize_use(value: Any) -> str:
    """Drop a parenthetical so 'sibling-fallback (not primary)' stays a backup."""
    text = str(value or "").strip().lower()
    if "(" in text:
        text = text.split("(", 1)[0].strip()
    return text


def normalize_rest_url(url: Any) -> str:
    """Compare card restUrl values with query URLs. Cards omit /query."""
    text = str(url or "").strip().rstrip("/")
    if text.lower().endswith("/query"):
        text = text[: -len("/query")].rstrip("/")
    return text.lower()


def query_url(url: str) -> str:
    text = str(url or "").strip()
    if not text:
        raise RuntimeError("Parcel layer URL is blank")
    if text.lower().endswith("/query"):
        return text
    return text.rstrip("/") + "/query"


def canonical_fields(layer: dict) -> dict[str, str]:
    """Map a card fieldMap (source → canonical) to canonical → source field."""
    found: dict[str, str] = {}
    for source, canonical in (layer.get("fieldMap") or {}).items():
        name = str(canonical or "").strip()
        if not name or name in found:
            continue
        found[name] = str(source)
    return found


def parcel_layers(card: dict) -> list[dict]:
    return [layer for layer in (card.get("layers") or []) if layer.get("role") == "parcels"]


def _matching(layers: list[dict], wanted: str) -> list[dict]:
    return [layer for layer in layers if normalize_rest_url(layer.get("restUrl")) == wanted]


def select_parcel_layers(card: dict) -> tuple[dict, dict]:
    """Pick geometry and sale/value layers by use, then require parcelSetup to agree.

    Layer order is ignored. A sibling-fallback listed first is not the source.
    """
    setup = card.get("parcelSetup") or {}
    geometry_source = setup.get("geometryOwnerSource")
    sales_source = setup.get("salesValueSource")
    if not geometry_source or not sales_source:
        fips = card.get("fips")
        raise RuntimeError(f"{fips} parcelSetup is missing geometryOwnerSource or salesValueSource")
    geometry_url = normalize_rest_url(geometry_source)
    sales_url = normalize_rest_url(sales_source)
    primaries: list[dict] = []
    sales_layers: list[dict] = []
    for layer in parcel_layers(card):
        use = normalize_use(layer.get("use"))
        if use in PRIMARY_USES:
            primaries.append(layer)
        elif use == SALES_USE:
            sales_layers.append(layer)
    primary_hits = _matching(primaries, geometry_url)
    if len(primary_hits) != 1:
        raise RuntimeError(
            f"{card.get('fips')} parcelSetup geometry URL matched {len(primary_hits)} "
            "primary-geometry layers. The first role:parcels layer is not a fallback."
        )
    primary = primary_hits[0]
    if geometry_url == sales_url:
        if normalize_use(primary.get("use")) != COMBINED_USE:
            raise RuntimeError(
                f"{card.get('fips')} parcelSetup uses one layer for geometry and sale/value, "
                "but that layer's use is not primary-geometry-owner-sales-value"
            )
        return primary, primary
    sales_hits = _matching(sales_layers, sales_url)
    if len(sales_hits) != 1:
        raise RuntimeError(
            f"{card.get('fips')} parcelSetup sales URL matched {len(sales_hits)} "
            "sales-value-join layers. A sibling-fallback is not the sale source."
        )
    return primary, sales_hits[0]


def resolve_acreage(primary: dict, setup: dict) -> tuple[str, str | None]:
    """OIR publishes no acreage field. Null acreageField is geodesic area."""
    field = primary.get("acreageField")
    if field in ("", "null"):
        field = None
    text = str(setup.get("acreageFilter") or "").lower()
    if field is None or "geodesic" in text:
        return "geodesic", field
    raise RuntimeError(
        "Acreage filter is not geodesic and the layer publishes an acreage field. "
        "Refusing to filter on that field."
    )


def _county_name(card: dict, overlay: dict | None) -> str:
    if overlay and overlay.get("name"):
        return str(overlay["name"])
    text = str(card.get("jurisdiction") or "").strip()
    if text.lower().endswith(" county"):
        text = text[: -len(" county")].strip()
    return text


def _where_and_county_id(setup: dict) -> tuple[str, int | None]:
    where = str(setup.get("geometryOwnerFilter") or "1=1").strip() or "1=1"
    if where.upper().startswith("COUNTY_ID="):
        county_id = int(where.split("=", 1)[1].strip())
        return f"COUNTY_ID={county_id}", county_id
    return where, None


def _vintage(setup: dict) -> str | None:
    value = setup.get("salesValueVintage", None)
    if value is None:
        return None
    text = str(value).strip()
    if not text or text.lower() == "null":
        return None
    return text


def _tncpm_layer_id(url: str) -> int | None:
    if "tn_county_parcel_map" not in url.lower():
        return None
    tail = normalize_rest_url(url).rsplit("/", 1)[-1]
    if not tail.isdigit():
        raise RuntimeError(f"TN_County_Parcel_Map URL has no layer id: {url}")
    return int(tail)


def _mode_for(primary_url: str) -> str:
    lowered = primary_url.lower()
    if "capturecama" in lowered and "/hickman/" in lowered:
        return "hickman"
    if "chestercapture" in lowered:
        return "chester"
    if "tennessee_property_boundaries_public_use" in lowered:
        return "oir"
    return "card"


def _source_for(fips: str, mode: str, overlay: dict | None) -> str:
    if overlay and overlay.get("source"):
        return str(overlay["source"])
    if mode == "oir":
        return f"tn-oir-public-use-{fips}"
    if mode == "hickman":
        return "tn-hickman-capturecama-202305"
    if mode == "chester":
        return "tn-chester-capturecama-parcels12"
    return f"tn-card-{fips}"


def _sales_join(sales: dict, sales_query: str) -> dict[str, str]:
    fields = canonical_fields(sales)
    spec = {
        "url": sales_query,
        "idField": fields.get("parcelId") or "",
        "dateField": fields.get("lastSale.date") or "",
        "priceField": fields.get("lastSale.price") or "",
        "marketField": fields.get("tax.marketValue") or "",
        "assessedField": fields.get("tax.assessedValue") or "",
        "mail1": fields.get("mailingAddress.street") or "",
        "mailCity": fields.get("mailingAddress.city") or "",
        "mailState": fields.get("mailingAddress.state") or "",
        "mailZip": fields.get("mailingAddress.zip") or "",
    }
    if fields.get("zoning"):
        spec["zoningField"] = fields["zoning"]
    if not spec["idField"]:
        raise RuntimeError(f"Sale/value layer {sales_query} has no parcelId field")
    return spec


def _usable_zoning(card: dict) -> bool:
    for layer in card.get("layers") or []:
        if layer.get("role") != "zoning":
            continue
        if layer.get("status") == "usable" and layer.get("restUrl"):
            return True
    return False


def _portal(card: dict, overlay: dict | None) -> str | None:
    if overlay and overlay.get("portal"):
        return str(overlay["portal"])
    template = str(card.get("appraiserSearchUrl") or "")
    if template and "{" not in template:
        return template
    return None


def resolve_card(card: dict, overlay: dict | None = None) -> dict[str, Any]:
    """Build the ingest row from use and parcelSetup. Overlay keeps zoning joins and source ids."""
    fips = str(card.get("fips") or "").strip()
    if len(fips) == 4:
        fips = fips.zfill(5)
    if not fips:
        raise RuntimeError("Parcel card is missing fips")
    setup = card.get("parcelSetup") or {}
    primary, sales = select_parcel_layers(card)
    acreage_method, acreage_field = resolve_acreage(primary, setup)
    geometry_query = query_url(str(primary.get("restUrl") or ""))
    sales_query = query_url(str(sales.get("restUrl") or ""))
    where, county_id = _where_and_county_id(setup)
    mode = _mode_for(geometry_query)
    same_layer = normalize_rest_url(geometry_query) == normalize_rest_url(sales_query)
    tncpm_layer = None if same_layer else _tncpm_layer_id(sales_query)
    name = _county_name(card, overlay)
    row: dict[str, Any] = {
        "fips": fips,
        "name": name,
        "mode": mode,
        "source": _source_for(fips, mode, overlay),
        "queryUrl": geometry_query,
        "where": where,
        "countyId": county_id,
        "tncpmLayer": tncpm_layer,
        "salesVintage": _vintage(setup),
        "acreageMethod": acreage_method,
        "acreageField": acreage_field,
        "primaryUse": normalize_use(primary.get("use")),
        "salesUse": normalize_use(sales.get("use")),
        "geometryFields": canonical_fields(primary),
        "hasUsableZoning": _usable_zoning(card),
        "salesOnGeometry": False,
    }
    if mode == "oir":
        row["oirName"] = name.upper()
    portal = _portal(card, overlay)
    if portal:
        row["portal"] = portal
    if overlay and isinstance(overlay.get("joins"), dict):
        row["joins"] = dict(overlay["joins"])
    if tncpm_layer is not None:
        return row
    if mode in {"hickman", "chester"}:
        return row
    sales_spec = _sales_join(sales, sales_query)
    row["salesJoin"] = sales_spec
    if same_layer:
        row["salesOnGeometry"] = True
        row["stampSalesZoning"] = not row["hasUsableZoning"] and bool(sales_spec.get("zoningField"))
        return row
    row["stampSalesZoning"] = not row["hasUsableZoning"] and bool(sales_spec.get("zoningField"))
    return row


def sales_join_kind(row: dict) -> str:
    """Which sale/value path runs. Special counties stay on their existing joins."""
    if row.get("fips") == "47155":
        return "sevier-cama"
    if row.get("fips") == "47133":
        return "overton-ucdd"
    if row.get("tncpmLayer") is not None:
        return "tncpm"
    if row.get("salesOnGeometry"):
        return "same-layer"
    if row.get("salesJoin"):
        return "mapped"
    return "none"


def load_cards(directory: Path | None = None) -> list[dict]:
    import yaml

    folder = directory or CARDS_DIR
    paths = sorted(folder.glob("*.yaml"))
    if not paths:
        raise RuntimeError(f"No parcel cards in {folder}")
    cards: list[dict] = []
    seen: set[str] = set()
    for path in paths:
        card = yaml.safe_load(path.read_text())
        if not isinstance(card, dict):
            raise RuntimeError(f"{path.name} is not a parcel card")
        fips = str(card.get("fips") or "").strip()
        if len(fips) == 4:
            fips = fips.zfill(5)
        card["fips"] = fips
        if not fips or fips in seen:
            raise RuntimeError(f"Duplicate or blank FIPS in {path.name}")
        seen.add(fips)
        cards.append(card)
    return cards


def lookup_attr(attrs: dict, name: str | None) -> Any:
    if not name:
        return None
    if name in attrs:
        return attrs[name]
    lowered = name.lower()
    for key, value in attrs.items():
        if str(key).lower() == lowered:
            return value
    return None


def card_sale_date(value: Any) -> str | None:
    """Slash dates, CaptureCAMA YYMMDD, then ArcGIS epoch. Order matters."""
    from tn_oir_parcels import clean, slash_date_to_iso, yymmdd_to_iso

    text = clean(value)
    if not text:
        return None
    if "/" in text:
        return slash_date_to_iso(text)
    if text.isdigit() and len(text) in {6, 8}:
        return yymmdd_to_iso(text)
    from seed_market_parcels import epoch_to_iso

    return epoch_to_iso(value)


def stamp_mapped_sale(
    props: dict,
    attrs: dict,
    sales: dict,
    vintage: str | None,
    *,
    stamp_zoning: bool = False,
) -> dict[str, bool]:
    """Copy sale, value, mailing, and optional zoning from a card field map."""
    from tn_oir_parcels import clean, num

    sold = card_sale_date(lookup_attr(attrs, sales.get("dateField")))
    price = num(lookup_attr(attrs, sales.get("priceField")))
    if price is not None and price <= 0:
        price = None
    appraisal = num(lookup_attr(attrs, sales.get("marketField")))
    if appraisal is not None and appraisal <= 0:
        appraisal = None
    assessed = num(lookup_attr(attrs, sales.get("assessedField")))
    if assessed is not None and assessed <= 0:
        assessed = None
    stamped_sale = False
    if sold or price is not None:
        last_sale = {"date": sold, "price": price, "qualified": None}
        if vintage:
            last_sale["vintage"] = str(vintage)
        props["lastSale"] = last_sale
        stamped_sale = True
    tax = props.setdefault("tax", {})
    stamped_value = False
    stamped_assessed = False
    if appraisal is not None:
        tax["marketValue"] = appraisal
        stamped_value = True
    if assessed is not None:
        tax["assessedValue"] = assessed
        stamped_assessed = True
    if vintage and (stamped_value or stamped_assessed):
        tax["vintage"] = str(vintage)
    mail1 = clean(lookup_attr(attrs, sales.get("mail1")))
    mail_city = clean(lookup_attr(attrs, sales.get("mailCity")))
    mail_state = clean(lookup_attr(attrs, sales.get("mailState")))
    mail_zip = clean(lookup_attr(attrs, sales.get("mailZip")))
    stamped_mail = False
    if mail1 or mail_city:
        props["mailingAddress"] = {
            "line1": mail1,
            "line2": None,
            "city": mail_city,
            "state": mail_state,
            "zip": mail_zip,
        }
        stamped_mail = True
    stamped_zoning = False
    if stamp_zoning:
        zone = clean(lookup_attr(attrs, sales.get("zoningField")))
        if zone:
            props["zoningCode"] = zone
            stamped_zoning = True
    return {
        "sale": stamped_sale,
        "value": stamped_value,
        "assessed": stamped_assessed,
        "mail": stamped_mail,
        "zoning": stamped_zoning,
    }
