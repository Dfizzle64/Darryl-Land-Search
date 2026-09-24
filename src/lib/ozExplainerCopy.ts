/** Verbatim Opportunity Zones 2.0 explainer. Do not paraphrase the Treasury wording. */

export const OZ_EXPLAINER_TITLE = "How Opportunity Zones 2.0 work";

export type OzExplainerSection = {
  heading: string;
  paragraphs?: string[];
  bullets?: string[];
};

export const OZ_EXPLAINER_SECTIONS: OzExplainerSection[] = [
  {
    heading: "What makes a tract eligible",
    paragraphs: [
      "Opportunity Zones 2.0 start from a national IRS/Treasury list (Rev. Proc. 2026-14) of census tracts that meet federal low-income community tests using American Community Survey (ACS) income and poverty data.",
    ],
    bullets: [
      "Eligible = on that federal list. It is a data screen only.",
      "Designated / Qualified Opportunity Zone (QOZ) = Treasury has certified the tract for the 2027 program.",
      "As of late September 2026, tracts on our maps are eligible (or, in some states, nominated) — not designated QOZs yet.",
      "This is not the old OZ 1.0 / HUD designation cycle. Do not treat OZ 1.0 maps as OZ 2.0 status.",
    ],
  },
  {
    heading: "How the process works",
    bullets: [
      "Step 1 — Eligibility: Treasury publishes which tracts qualify for nomination.",
      "Step 2 — Nomination: Each state’s governor may nominate up to about 25% of that state’s eligible tracts.",
      "Step 3 — Designation: Treasury certifies the final 2027 QOZs after reviewing nominations.",
      "Timing: Federal nomination window centers on late September 2026 (extension available into late October). Treasury aims to identify designated zones before they take effect January 1, 2027.",
      "Until certification: label tracts “Eligible — not designated” (or “Nominated — not designated” only when a real nomination source is confirmed).",
    ],
  },
  {
    heading: "What it means for investors (high level — not tax advice)",
    paragraphs: [
      "If a tract becomes a certified 2027 QOZ, capital-gains investments into a Qualified Opportunity Fund that deploys into that zone may be eligible for federal tax benefits typically described as:",
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
      "Eligible ≠ nominated ≠ certified. A census tract is not a buildable site; zoning, utilities, wetlands, and title still control.",
    ],
  },
];

/** Follows the investor bullets. Not a sixth section. */
export const OZ_EXPLAINER_TAX_NOTE =
  "Rules, timing, and eligibility are statute- and IRS-specific. This app does not provide tax advice; confirm with counsel or a tax advisor before underwriting benefits.";
