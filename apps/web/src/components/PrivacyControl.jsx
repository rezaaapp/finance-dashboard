import {
  Check,
  ChevronDown,
  Eye,
  Lock,
  VenetianMask,
} from "lucide-react";
import { memo, useCallback, useEffect, useMemo, useRef, useState } from "react";

import { PRIVACY_MODES } from "../utils/privacy";

const privacyOptions = [
  {
    value: PRIVACY_MODES.normal,
    label: "Normal",
    description: "Original data is fully visible.",
    icon: Eye,
  },
  {
    value: PRIVACY_MODES.hide,
    label: "Hide",
    description: "Amounts are hidden for public viewing.",
    icon: Lock,
  },
  {
    value: PRIVACY_MODES.guest,
    label: "Guest",
    description: "Amounts are replaced with realistic dummy values.",
    icon: VenetianMask,
  },
];

const PrivacyControl = memo(({ value, onChange }) => {
  const [isOpen, setIsOpen] = useState(false);
  const containerRef = useRef(null);
  const selectedOption = useMemo(() => (
    privacyOptions.find((option) => option.value === value)
    ?? privacyOptions[0]
  ), [value]);
  const SelectedIcon = selectedOption.icon;
  const toggleOpen = useCallback(() => {
    setIsOpen((current) => !current);
  }, []);
  const handleSelect = useCallback((optionValue) => {
    onChange(optionValue);
    setIsOpen(false);
  }, [onChange]);

  useEffect(() => {
    const handleClickOutside = (event) => {
      if (
        containerRef.current
        && !containerRef.current.contains(event.target)
      ) {
        setIsOpen(false);
      }
    };

    document.addEventListener("mousedown", handleClickOutside);

    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
    };
  }, []);

  return (
    <div ref={containerRef} className="relative min-w-0">
      <button
        type="button"
        onClick={toggleOpen}
        className="theme-toggle w-full justify-between rounded-xl px-3 py-2 sm:min-w-[190px] xl:w-auto"
        aria-expanded={isOpen}
        aria-label="Privacy mode"
        title={selectedOption.description}
      >
        <span className="flex items-center gap-2">
          <SelectedIcon size={17} />
          <span className="flex flex-col items-start leading-tight">
            <span className="text-[11px] font-semibold uppercase text-muted">
              Privacy
            </span>
            <span className="text-sm font-bold">
              {selectedOption.label}
            </span>
          </span>
        </span>

        <ChevronDown
          size={16}
          className={`transition-transform ${isOpen ? "rotate-180" : ""}`}
        />
      </button>

      {isOpen && (
        <div className="relative z-30 mt-2 w-full rounded-xl border border-[var(--color-border)] bg-[var(--color-panel)] p-2 shadow-2xl sm:absolute sm:right-0 sm:w-[min(280px,calc(100vw-32px))]">
          {privacyOptions.map((option) => {
            const Icon = option.icon;
            const isActive = option.value === value;

            return (
              <button
                key={option.value}
                type="button"
                onClick={() => handleSelect(option.value)}
                className={`
                  flex
                  w-full
                  items-start
                  gap-3
                  rounded-lg
                  px-3
                  py-3
                  text-left
                  transition-colors
                  ${isActive
                    ? "bg-[var(--color-accent-bg)] text-accent"
                    : "text-soft hover:bg-[var(--color-panel-hover)]"}
                `}
              >
                <Icon size={18} className="mt-0.5 shrink-0" />

                <span className="min-w-0 flex-1">
                  <span className="block text-sm font-bold">
                    {option.label}
                  </span>
                  <span className="mt-1 block text-xs text-muted">
                    {option.description}
                  </span>
                </span>

                {isActive && <Check size={16} className="mt-0.5 shrink-0" />}
              </button>
            );
          })}
        </div>
      )}
    </div>
  );
});

PrivacyControl.displayName = "PrivacyControl";

export default PrivacyControl;
