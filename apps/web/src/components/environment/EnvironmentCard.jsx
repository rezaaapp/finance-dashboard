import { CircleOff, Server } from "lucide-react";

import { getEnvironmentPresentation } from "../../utils/environment";

const toneClasses = {
  dev: "border-emerald-300 bg-emerald-50 text-emerald-900 dark:border-emerald-800 dark:bg-emerald-950/30 dark:text-emerald-100",
  prod: "border-orange-300 bg-orange-50 text-orange-950 dark:border-orange-800 dark:bg-orange-950/30 dark:text-orange-100",
  unknown: "border-gray-300 bg-gray-100 text-gray-700 dark:border-gray-700 dark:bg-gray-900 dark:text-gray-200",
};

const EnvironmentCard = ({ systemInfoState }) => {
  const { data, status } = systemInfoState;
  const presentation = getEnvironmentPresentation(data.appEnv);
  const statusLabel = status === "loading"
    ? "Checking"
    : data.connected ? "Connected" : "Offline";

  return (
    <section
      className={`w-full rounded-lg border px-4 py-3 ${toneClasses[presentation.tone]}`}
      aria-label="Current environment"
    >
      <div className="flex min-w-0 items-center justify-between gap-3">
        <div className="flex min-w-0 items-center gap-3">
          <span className="inline-flex shrink-0 items-center rounded-full border border-current/20 bg-white/50 px-2.5 py-1 text-xs font-bold dark:bg-black/10">
            {presentation.badgeLabel}
          </span>

          <p className="min-w-0 truncate text-xs font-semibold sm:text-sm">
            {presentation.title}
          </p>
        </div>

        <span className="inline-flex shrink-0 items-center gap-1.5 text-xs font-semibold">
          {data.connected ? <Server size={14} /> : <CircleOff size={14} />}
          {statusLabel}
        </span>
      </div>
    </section>
  );
};

export default EnvironmentCard;
