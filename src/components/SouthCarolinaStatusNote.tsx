import { SC_COMMERCE_OZ_URL } from "@/lib/types";

type SouthCarolinaStatusNoteProps = {
  note: string;
  className?: string;
};

export function SouthCarolinaStatusNote({ note, className }: SouthCarolinaStatusNoteProps) {
  return (
    <p className={className}>
      {note}{" "}
      <a
        href={SC_COMMERCE_OZ_URL}
        target="_blank"
        rel="noreferrer"
        className="pointer-events-auto text-clay-400 underline-offset-2 hover:underline"
      >
        SC Commerce
      </a>
    </p>
  );
}
