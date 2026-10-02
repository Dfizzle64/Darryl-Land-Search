import { SitePdfError, assembleSiteSummary, type SitePdfInput } from "./sitePdf";

async function loadLogoPng(): Promise<string | null> {
  try {
    const response = await fetch("/catalyst-logo.webp");
    if (!response.ok) return null;
    const blob = await response.blob();
    const url = URL.createObjectURL(blob);
    try {
      const image = await new Promise<HTMLImageElement>((resolve, reject) => {
        const img = new Image();
        img.onload = () => resolve(img);
        img.onerror = () => reject(new Error("logo"));
        img.src = url;
      });
      const canvas = document.createElement("canvas");
      canvas.width = image.naturalWidth || 110;
      canvas.height = image.naturalHeight || 112;
      const ctx = canvas.getContext("2d");
      if (!ctx) return null;
      ctx.fillStyle = "#ffffff";
      ctx.fillRect(0, 0, canvas.width, canvas.height);
      ctx.drawImage(image, 0, 0);
      return canvas.toDataURL("image/png");
    } finally {
      URL.revokeObjectURL(url);
    }
  } catch {
    return null;
  }
}

function downloadBytes(bytes: Uint8Array, fileName: string) {
  const buffer = new ArrayBuffer(bytes.byteLength);
  new Uint8Array(buffer).set(bytes);
  const blob = new Blob([buffer], { type: "application/pdf" });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = fileName;
  anchor.rel = "noopener";
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  window.setTimeout(() => URL.revokeObjectURL(url), 1500);
}

/** Lazy-loads map capture and jsPDF the first time Export PDF is clicked. */
export async function downloadSitePdf(input: SitePdfInput): Promise<void> {
  const model = assembleSiteSummary(input);
  const [{ buildSitePdfBytes }, { captureSiteMaps }, logo] = await Promise.all([
    import("./sitePdfDocument"),
    import("./sitePdfMap"),
    loadLogoPng(),
  ]);
  let images: { main: string; locator: string; scaleLabel: string };
  try {
    images = await captureSiteMaps({
      parcel: model.parcelGeometry,
      centroid: model.centroid,
      eligibleTract: model.eligibleTract,
    });
  } catch (error) {
    if (error instanceof SitePdfError) throw error;
    throw new SitePdfError("Could not export the PDF. The map did not finish loading. Try again.");
  }
  const bytes = buildSitePdfBytes(model, { ...images, logo });
  if (bytes.byteLength < 500) {
    throw new SitePdfError("Could not export the PDF. Try again.");
  }
  downloadBytes(bytes, model.fileName);
}
