import { jsPDF } from "jspdf";
import type { SitePdfFact, SitePdfImages, SitePdfLink, SitePdfModel } from "./sitePdf";

const INK: [number, number, number] = [22, 28, 36];
const MUTED: [number, number, number] = [90, 98, 108];
const MOSS: [number, number, number] = [31, 107, 74];
const RULE: [number, number, number] = [214, 218, 222];
const LINK: [number, number, number] = [20, 78, 120];
const PAGE_W = 612;
const PAGE_H = 792;
const MARGIN = 28;
const FOOTER_TOP = 742;

/** Helvetica in jsPDF is WinAnsi. Arrows and a few symbols otherwise paint as the wrong glyphs. */
function pdfSafe(value: string): string {
  return value
    .replace(/\u2192/g, "to")
    .replace(/\u2190/g, "from")
    .replace(/\u21d2/g, "to")
    .replace(/\u2248/g, "~")
    .replace(/\u2026/g, "...")
    .replace(/\u00a0/g, " ");
}

function imageFormat(dataUrl: string): "PNG" | "JPEG" {
  return dataUrl.startsWith("data:image/jpeg") || dataUrl.startsWith("data:image/jpg") ? "JPEG" : "PNG";
}

function wrapFact(doc: jsPDF, value: string, valueW: number, maxLines: number): string[] {
  const paragraphs = pdfSafe(value).split("\n");
  const all = paragraphs.flatMap((paragraph) => doc.splitTextToSize(paragraph || " ", valueW) as string[]);
  const kept = all.slice(0, maxLines);
  if (all.length > maxLines && kept.length) {
    const trimmed = kept[kept.length - 1].replace(/[.,;:\s]+$/g, "").trimEnd();
    kept[kept.length - 1] = `${trimmed || kept[kept.length - 1]}...`;
  }
  return kept.length ? kept : ["-"];
}

function drawFacts(
  doc: jsPDF,
  title: string,
  facts: SitePdfFact[],
  x: number,
  y: number,
  width: number,
  maxY: number,
  maxLines = 4,
): number {
  if (!facts.length || y > maxY - 20) return y;
  let cursor = y;
  if (title.trim()) {
    doc.setFont("helvetica", "bold");
    doc.setFontSize(8);
    doc.setTextColor(...MOSS);
    doc.text(pdfSafe(title), x, y);
    cursor = y + 12;
  } else if (title.length) {
    cursor = y + 12;
  }
  const labelW = 96;
  const valueX = x + labelW;
  const valueW = Math.max(40, width - labelW);
  for (const fact of facts) {
    doc.setFont("helvetica", "normal");
    doc.setFontSize(8);
    const lines = wrapFact(doc, fact.value, valueW, maxLines);
    const rowH = Math.max(11, lines.length * 8.6);
    if (cursor + rowH > maxY) break;
    doc.setFontSize(6.5);
    doc.setTextColor(...MUTED);
    doc.text(pdfSafe(fact.label), x, cursor);
    doc.setFontSize(8);
    doc.setTextColor(...INK);
    doc.text(lines, valueX, cursor);
    cursor += rowH;
  }
  return cursor;
}

function drawLinks(doc: jsPDF, links: SitePdfLink[], x: number, y: number, width: number, maxY: number): number {
  if (!links.length || y > maxY - 22) return y;
  doc.setFont("helvetica", "bold");
  doc.setFontSize(8);
  doc.setTextColor(...MOSS);
  doc.text("LINKS", x, y);
  let cursor = y + 12;
  for (const link of links) {
    doc.setFont("helvetica", "normal");
    doc.setFontSize(8);
    const labelLines = (doc.splitTextToSize(pdfSafe(link.label), width) as string[]).slice(0, 1);
    const urlLines = (doc.splitTextToSize(pdfSafe(link.href), width) as string[]).slice(0, 2);
    const block = urlLines.length > 1 ? 26 : 18;
    if (cursor + block > maxY) break;
    doc.setTextColor(...LINK);
    doc.text(labelLines, x, cursor);
    const labelWidth = doc.getTextWidth(labelLines[0] ?? link.label);
    doc.setDrawColor(...LINK);
    doc.setLineWidth(0.4);
    doc.line(x, cursor + 1.4, x + Math.min(labelWidth, width), cursor + 1.4);
    doc.link(x, cursor - 8, Math.min(Math.max(labelWidth, 40), width), 10, { url: link.href });
    doc.setFontSize(6.5);
    doc.setTextColor(...MUTED);
    doc.text(urlLines, x, cursor + 8);
    cursor += block;
  }
  return cursor;
}

function drawFooter(doc: jsPDF, model: SitePdfModel) {
  doc.setFillColor(244, 245, 243);
  doc.rect(0, FOOTER_TOP, PAGE_W, PAGE_H - FOOTER_TOP, "F");
  doc.setFont("helvetica", "normal");
  doc.setFontSize(6.5);
  doc.setTextColor(...MUTED);
  const sourceLine = pdfSafe(`Sources: ${model.sources.join("; ")}`);
  const wrapped = doc.splitTextToSize(sourceLine, PAGE_W - MARGIN * 2) as string[];
  const lines = wrapped.slice(0, 2);
  if (wrapped.length > 2 && lines.length) {
    const trimmed = lines[lines.length - 1].replace(/[;,\s]+$/g, "").trimEnd();
    lines[lines.length - 1] = `${trimmed}...`;
  }
  doc.text(lines, MARGIN, FOOTER_TOP + 14);
  doc.setFont("helvetica", "bold");
  doc.setTextColor(...INK);
  doc.text(model.disclaimer, MARGIN, PAGE_H - 14);
}

/**
 * One letter portrait page. Extra pages are not used; rows that do not fit
 * are left off rather than spilling onto page two.
 */
export function buildSitePdfBytes(model: SitePdfModel, images: SitePdfImages): Uint8Array {
  const doc = new jsPDF({ unit: "pt", format: "letter", orientation: "portrait", compress: false });
  doc.setProperties({
    title: `${model.title} — ${model.headline}`,
    creator: "Catalyst Development Partners",
    subject: model.fileName,
  });

  let y = 30;
  if (images.logo) {
    try {
      doc.addImage(images.logo, imageFormat(images.logo), MARGIN, 24, 34, 35);
    } catch {
      // A logo that cannot be embedded still leaves the title.
    }
  }
  const textX = images.logo ? MARGIN + 44 : MARGIN;
  doc.setFont("helvetica", "bold");
  doc.setFontSize(16);
  doc.setTextColor(...INK);
  doc.text(pdfSafe(model.title), textX, y + 8);
  doc.setFont("helvetica", "normal");
  doc.setFontSize(8);
  doc.setTextColor(...MUTED);
  doc.text(pdfSafe(model.generatedOn), PAGE_W - MARGIN, y + 8, { align: "right" });
  doc.setFontSize(9);
  doc.setTextColor(...INK);
  const headline = (doc.splitTextToSize(pdfSafe(model.headline), 360) as string[]).slice(0, 1);
  doc.text(headline, textX, y + 22);
  doc.setFontSize(8);
  doc.setTextColor(...MUTED);
  const subhead = (doc.splitTextToSize(pdfSafe(model.subhead), 360) as string[]).slice(0, 1);
  doc.text(subhead, textX, y + 34);
  y = 68;
  doc.setDrawColor(...MOSS);
  doc.setLineWidth(1.5);
  doc.line(MARGIN, y, PAGE_W - MARGIN, y);

  const mapX = MARGIN;
  const mapY = y + 8;
  const mapW = PAGE_W - MARGIN * 2;
  const mapH = 188;
  try {
    doc.addImage(images.main, imageFormat(images.main), mapX, mapY, mapW, mapH);
  } catch {
    doc.setFillColor(236, 232, 224);
    doc.rect(mapX, mapY, mapW, mapH, "F");
    doc.setFontSize(9);
    doc.setTextColor(...MUTED);
    doc.text("Map image unavailable", mapX + 12, mapY + 20);
  }
  doc.setDrawColor(...RULE);
  doc.setLineWidth(0.6);
  doc.rect(mapX, mapY, mapW, mapH);

  const insetW = 112;
  const insetH = 76;
  const insetX = mapX + 8;
  const insetY = mapY + mapH - insetH - 8;
  try {
    doc.setFillColor(255, 255, 255);
    doc.rect(insetX - 2, insetY - 2, insetW + 4, insetH + 4, "F");
    doc.addImage(images.locator, imageFormat(images.locator), insetX, insetY, insetW, insetH);
  } catch {
    // The main map still stands when the locator image fails.
  }
  doc.setDrawColor(...INK);
  doc.setLineWidth(0.7);
  doc.rect(insetX, insetY, insetW, insetH);
  doc.setFillColor(255, 255, 255);
  doc.rect(insetX, insetY, 42, 9, "F");
  doc.setFont("helvetica", "bold");
  doc.setFontSize(6);
  doc.setTextColor(...INK);
  doc.text("REGION", insetX + 3, insetY + 6.5);

  y = mapY + mapH + 12;
  doc.setFont("helvetica", "normal");
  doc.setFontSize(7);
  doc.setTextColor(...MUTED);
  const captionLeft = "Parcel outline. Eligible tract tint matches the map.";
  doc.text(captionLeft, mapX, y);
  if (images.scaleLabel) {
    doc.text(`Scale ~ ${pdfSafe(images.scaleLabel)}`, mapX + mapW, y, { align: "right" });
  }

  const linkBlock = model.links.length ? 14 + model.links.length * 18 : 0;
  const contentMax = FOOTER_TOP - 8 - linkBlock;
  const columnsTop = y + 16;
  const columnW = (mapW - 16) / 2;
  const schools = model.screeningFacts.filter((fact) => fact.label === "Schools");
  const screening = model.screeningFacts.filter((fact) => fact.label !== "Schools");
  const schoolReserve = schools.length ? 52 : 0;
  const leftBottom = drawFacts(doc, "PARCEL", model.parcelFacts, mapX, columnsTop, columnW, contentMax - schoolReserve);
  const rightBottom = drawFacts(doc, "TRACT", model.tractFacts, mapX + columnW + 16, columnsTop, columnW, contentMax - schoolReserve);
  let cursor = Math.max(leftBottom, rightBottom) + 8;
  if (screening.length && cursor < contentMax - schoolReserve - 16) {
    const half = Math.ceil(screening.length / 2);
    const left = screening.slice(0, half);
    const right = screening.slice(half);
    const screenLeft = drawFacts(doc, "SCREENING", left, mapX, cursor, columnW, contentMax - schoolReserve, 3);
    const screenRight = right.length
      ? drawFacts(doc, " ", right, mapX + columnW + 16, cursor, columnW, contentMax - schoolReserve, 3)
      : cursor;
    cursor = Math.max(screenLeft, screenRight) + 6;
  }
  if (schools.length && cursor < contentMax - 16) {
    cursor = drawFacts(doc, screening.length ? "" : "SCREENING", schools, mapX, cursor, mapW, contentMax, 5) + 4;
  }
  if (model.links.length) {
    drawLinks(doc, model.links, mapX, Math.min(cursor, contentMax), mapW, FOOTER_TOP - 4);
  }

  drawFooter(doc, model);
  while (doc.getNumberOfPages() > 1) doc.deletePage(doc.getNumberOfPages());
  return new Uint8Array(doc.output("arraybuffer"));
}
