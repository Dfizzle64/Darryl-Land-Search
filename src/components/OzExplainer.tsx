"use client";

import { useEffect, useRef } from "react";
import { OZ_EXPLAINER_SECTIONS, OZ_EXPLAINER_TAX_NOTE, OZ_EXPLAINER_TITLE } from "@/lib/ozExplainerCopy";

type OzExplainerProps = {
  open: boolean;
  onClose: () => void;
};

export function OzExplainer({ open, onClose }: OzExplainerProps) {
  const dialogRef = useRef<HTMLDivElement | null>(null);

  const onCloseRef = useRef(onClose);
  onCloseRef.current = onClose;

  useEffect(() => {
    if (!open) return;
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") onCloseRef.current();
    };
    window.addEventListener("keydown", onKey);
    dialogRef.current?.focus();
    return () => window.removeEventListener("keydown", onKey);
  }, [open]);

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center overflow-y-auto bg-black/60 p-4 sm:items-center" onClick={onClose}>
      <div
        ref={dialogRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby="oz-explainer-title"
        tabIndex={-1}
        className="my-4 w-full max-w-xl rounded-2xl border border-white/15 bg-ink-900 p-5 text-ink-100 shadow-2xl outline-none"
        onClick={(event) => event.stopPropagation()}
      >
        <div className="flex items-start justify-between gap-3">
          <h2 id="oz-explainer-title" className="font-display text-2xl leading-tight text-white">
            {OZ_EXPLAINER_TITLE}
          </h2>
          <button type="button" className="rounded-full border border-white/20 px-3 py-1 text-sm text-white" onClick={onClose}>
            Close
          </button>
        </div>
        <div className="mt-4 max-h-[70vh] space-y-5 overflow-y-auto pr-1 text-sm leading-relaxed">
          {OZ_EXPLAINER_SECTIONS.map((section) => (
            <section key={section.heading}>
              <h3 className="text-[11px] uppercase tracking-[0.16em] text-clay-400">{section.heading}</h3>
              {section.paragraphs?.map((paragraph) => (
                <p key={paragraph} className="mt-2 text-ink-100">
                  {paragraph}
                </p>
              ))}
              {section.bullets ? (
                <ul className="mt-2 list-disc space-y-1 pl-5 text-ink-100">
                  {section.bullets.map((bullet) => (
                    <li key={bullet}>{bullet}</li>
                  ))}
                </ul>
              ) : null}
              {section.links?.map((link) => (
                <p key={link.href} className="mt-2">
                  <a
                    href={link.href}
                    target="_blank"
                    rel="noreferrer"
                    className="text-clay-400 underline-offset-2 hover:underline"
                  >
                    {link.label}
                  </a>
                </p>
              ))}
              {section.heading.startsWith("What it means for investors") ? (
                <p className="mt-2 text-ink-300">{OZ_EXPLAINER_TAX_NOTE}</p>
              ) : null}
            </section>
          ))}
        </div>
      </div>
    </div>
  );
}
