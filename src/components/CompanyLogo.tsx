import Image from "next/image";

/** Catalyst corner mark. The file is 110×112 so it stays sharp at 40–56px. */
export function CompanyLogo() {
  return (
    <div
      data-company-logo
      className="pointer-events-none overflow-hidden rounded-lg bg-white shadow-[0_1px_2px_rgba(12,18,24,0.22),0_6px_16px_rgba(12,18,24,0.38)] ring-1 ring-black/15"
    >
      <Image
        src="/catalyst-logo.webp"
        alt="Catalyst Development Partners"
        width={110}
        height={112}
        priority
        draggable={false}
        className="block h-10 w-auto sm:h-12"
        style={{ width: "auto" }}
      />
    </div>
  );
}
