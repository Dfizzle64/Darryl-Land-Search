import { SC_COMMERCE_OZ_URL } from "@/lib/types";

type SouthCarolinaStatusNoteProps = {
  note: string;
  className?: string;
};

export function SouthCarolinaStatusNote({ note, className }: SouthCarolinaStatusNoteProps) {
  const marker = "SC Commerce";
  const index = note.indexOf(marker);
  const link = (
    <a
      href={SC_COMMERCE_OZ_URL}
      target="_blank"
      rel="noreferrer"
      className="pointer-events-auto text-clay-400 underline-offset-2 hover:underline"
    >
      {marker}
    </a>
  );
  if (index === -1) {
    return (
      <p className={className}>
        {note} {link}
      </p>
    );
  }
  return (
    <p className={className}>
      {note.slice(0, index)}
      {link}
      {note.slice(index + marker.length)}
    </p>
  );
}
