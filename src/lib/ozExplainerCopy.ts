import { SC_COMMERCE_FINAL_RECOMMENDATIONS_URL, SC_GOVERNOR_OZ_RELEASE_URL } from "./types";

/** Opportunity Zones 2.0 explainer. Plain language for a developer, not a legal opinion. */

export const OZ_EXPLAINER_TITLE = "How Opportunity Zones 2.0 work";

export type OzExplainerLink = {
  href: string;
  label: string;
};

export type OzExplainerSection = {
  heading: string;
  paragraphs?: string[];
  bullets?: string[];
  links?: OzExplainerLink[];
};

export const OZ_EXPLAINER_SECTIONS: OzExplainerSection[] = [
  {
    heading: "What makes a tract eligible",
    paragraphs: [
      "Opportunity Zones 2.0 is the 2027 cycle. It starts from a national IRS/Treasury list (Rev. Proc. 2026-14) of census tracts that meet federal low-income community tests.",
    ],
    bullets: [
      "Eligible = on that federal list. It is a data screen only.",
      "States nominate from that list. Treasury certifies later.",
      "Designated / Qualified Opportunity Zone (QOZ) = Treasury has certified the tract for the 2027 program.",
      "Nothing on this map is a certified QOZ yet. Nomination alone is not a tax benefit.",
      "This is not the old OZ 1.0 / HUD designation cycle. Do not treat OZ 1.0 maps as OZ 2.0 status.",
    ],
  },
  {
    heading: "How the process works",
    bullets: [
      "Step 1 — Eligibility: Treasury publishes which tracts qualify for nomination.",
      "Step 2 — Nomination: Each state’s governor may nominate up to about 25% of that state’s eligible tracts.",
      "Step 3 — Designation: Treasury certifies the final 2027 QOZs after reviewing nominations.",
      "Timing: The federal nomination window centers on late September 2026 (an extension can run into late October). Designated zones are meant to take effect January 1, 2027.",
      "Until certification, an eligible tract that was not nominated stays “Eligible — not designated.”",
      "Governor-nominated / awaiting Treasury = the state filed that tract with Treasury; still not a certified 2027 QOZ.",
      "Soft-upgrade only when the state’s official nomination list is public (SC: Commerce Final Recommendations PDF, 112 tracts). Secondary scrapes alone aren’t enough.",
      "Designated / QOZ = Treasury certification only — none of our markets yet; target effective Jan 1, 2027.",
    ],
  },
  {
    heading: "South Carolina nominations",
    paragraphs: [
      "South Carolina’s governor submitted nominations to Treasury. The announcement is September 23, 2026. SC Commerce’s Final Recommendations PDF is dated September 22, 2026.",
      "That filing is 112 census tracts: 84 rural and 28 non-rural. This map soft-upgrades those same GEOIDs from the primary source. It is not a new list.",
    ],
    links: [
      { href: SC_GOVERNOR_OZ_RELEASE_URL, label: "Governor’s September 23, 2026 announcement" },
      { href: SC_COMMERCE_FINAL_RECOMMENDATIONS_URL, label: "SC Commerce Final Recommendations PDF (September 22, 2026)" },
    ],
  },
  {
    heading: "What the map chips mean",
    bullets: [
      "Eligible — not designated: on the federal eligible list, and not one of the 112 South Carolina nominations.",
      "Governor-nominated / awaiting Treasury = the state filed that tract with Treasury; still not a certified 2027 QOZ.",
      "Soft-upgrade only when the state’s official nomination list is public (SC: Commerce Final Recommendations PDF, 112 tracts). Secondary scrapes alone aren’t enough.",
      "Designated / QOZ = Treasury certification only — none of our markets yet; target effective Jan 1, 2027.",
    ],
  },
  {
    heading: "What it means for investors (high level — not tax advice)",
    paragraphs: [
      "Only if a tract becomes a certified 2027 QOZ might capital-gains investments into a Qualified Opportunity Fund that deploys into that zone be eligible for federal tax benefits typically described as:",
    ],
    bullets: [
      "Deferral of certain capital gains while the investment is held in the fund",
      "A basis increase (step-up) after a multi-year hold",
      "Potential exclusion of post-investment appreciation after a longer hold",
    ],
  },
  {
    heading: "Rural vs urban on the eligible list",
    paragraphs: [
      "Treasury tags some eligible tracts as comprised entirely of a rural area (no city/town over 50,000 and not in an urbanized area contiguous or adjacent to one). Others are non-rural (urban/suburban on our maps).",
    ],
    bullets: [
      "Rural / urban is an attribute on the eligible list.",
      "It is not designation and does not by itself create tax benefits.",
      "If designated, rural tracts may receive additional statutory investment enhancements — still contingent on final QOZ certification.",
    ],
  },
  {
    heading: "Disclaimer",
    paragraphs: [
      "Eligible ≠ nominated ≠ certified. A census tract is not a buildable site; zoning, utilities, wetlands, and title still control. Nothing on this map is a certified QOZ, and nomination alone does not create a tax benefit.",
    ],
  },
];

/** Follows the investor bullets. Not a separate section. */
export const OZ_EXPLAINER_TAX_NOTE =
  "Rules, timing, and eligibility are statute- and IRS-specific. This app does not provide tax advice; confirm with counsel or a tax advisor before underwriting benefits.";
