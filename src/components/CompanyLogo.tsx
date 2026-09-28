import Image from "next/image";

/** Header mark. The file is 110×112 so it stays sharp at the title-block height. */
export function CompanyLogo() {
  return (
    <div
      data-company-logo
      className="pointer-events-none shrink-0 overflow-hidden rounded-lg bg-white ring-1 ring-white/40"
    >
      <Image
        src="/catalyst-logo.webp"
        alt="Catalyst Development Partners"
        width={110}
        height={112}
        priority
        draggable={false}
        className="block h-11 w-auto md:h-12"
        style={{ width: "auto" }}
      />
    </div>
  );
}
