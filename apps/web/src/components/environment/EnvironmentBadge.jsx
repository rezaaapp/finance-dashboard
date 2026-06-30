import { ChevronDown, Circle } from "lucide-react";
import { useEffect, useRef, useState } from "react";

import { getEnvironmentPresentation } from "../../utils/environment";
import SystemInfoPanel from "./SystemInfoPanel";

const toneClasses = {
  dev: "border-emerald-300 bg-emerald-50 text-emerald-800 dark:border-emerald-800 dark:bg-emerald-950/30 dark:text-emerald-200",
  prod: "border-orange-300 bg-orange-50 text-orange-900 dark:border-orange-800 dark:bg-orange-950/30 dark:text-orange-200",
  unknown: "border-gray-300 bg-gray-100 text-gray-600 dark:border-gray-700 dark:bg-gray-900 dark:text-gray-300",
};

const EnvironmentBadge = ({ systemInfoState }) => {
  const [isOpen, setIsOpen] = useState(false);
  const containerRef = useRef(null);
  const presentation = getEnvironmentPresentation(systemInfoState.data.appEnv);

  useEffect(() => {
    if (!isOpen) {
      return undefined;
    }

    const closeOnPointerDown = (event) => {
      if (containerRef.current && !containerRef.current.contains(event.target)) {
        setIsOpen(false);
      }
    };
    const closeOnEscape = (event) => {
      if (event.key === "Escape") {
        setIsOpen(false);
      }
    };

    document.addEventListener("pointerdown", closeOnPointerDown);
    document.addEventListener("keydown", closeOnEscape);
    return () => {
      document.removeEventListener("pointerdown", closeOnPointerDown);
      document.removeEventListener("keydown", closeOnEscape);
    };
  }, [isOpen]);

  return (
    <div ref={containerRef} className="relative mt-3 inline-flex">
      <button
        type="button"
        onClick={() => setIsOpen((current) => !current)}
        className={`inline-flex h-8 items-center gap-2 rounded-full border px-3 text-xs font-bold ${toneClasses[presentation.tone]}`}
        aria-expanded={isOpen}
        aria-haspopup="dialog"
        title="Open environment details"
      >
        <Circle
          size={9}
          fill="currentColor"
          className={systemInfoState.data.connected ? "opacity-100" : "opacity-40"}
        />
        {presentation.badgeLabel}
        <ChevronDown size={13} className={isOpen ? "rotate-180" : ""} />
      </button>

      {isOpen && (
        <div
          className="absolute left-0 top-full z-[70] mt-2 w-[min(22rem,calc(100vw-2rem))] rounded-lg border border-[var(--color-border)] bg-[var(--color-panel)] p-4 shadow-xl"
          role="dialog"
          aria-label="Environment details"
        >
          <SystemInfoPanel systemInfoState={systemInfoState} compact />
        </div>
      )}
    </div>
  );
};

export default EnvironmentBadge;
