import { ChevronDown, Circle } from "lucide-react";
import { useEffect, useRef, useState } from "react";

import { getEnvironmentPresentation } from "../../utils/environment";
import SystemInfoPanel from "./SystemInfoPanel";

const toneClasses = {
  dev: "status-badge--success",
  prod: "status-badge--warning",
  unknown: "status-badge--neutral",
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
        className={`status-badge h-8 ${toneClasses[presentation.tone]}`}
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
          className="dialog-panel absolute left-0 top-full z-[70] mt-2 w-[min(22rem,calc(100vw-2rem))] p-4"
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
