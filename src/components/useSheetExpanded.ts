"use client";

import { useEffect, useRef, useState, type PointerEvent as ReactPointerEvent } from "react";
import { sheetExpandedAfterGesture } from "@/lib/detailSheet";

/** Peek / expand state for a narrow-screen bottom sheet. Resets when the record changes. */
export function useSheetExpanded(resetKey: string | null) {
  const [expanded, setExpanded] = useState(false);
  const startY = useRef(0);
  const dragged = useRef(false);

  useEffect(() => {
    setExpanded(false);
  }, [resetKey]);

  const onPointerDown = (event: ReactPointerEvent<HTMLButtonElement>) => {
    startY.current = event.clientY;
    dragged.current = false;
    event.currentTarget.setPointerCapture(event.pointerId);
  };

  const onPointerUp = (event: ReactPointerEvent<HTMLButtonElement>) => {
    const deltaY = startY.current - event.clientY;
    if (Math.abs(deltaY) > 24) {
      dragged.current = true;
      setExpanded(sheetExpandedAfterGesture(false, deltaY));
    }
  };

  const onClick = () => {
    if (dragged.current) {
      dragged.current = false;
      return;
    }
    setExpanded((current) => !current);
  };

  return {
    expanded,
    handleProps: {
      onPointerDown,
      onPointerUp,
      onClick,
    },
  };
}
