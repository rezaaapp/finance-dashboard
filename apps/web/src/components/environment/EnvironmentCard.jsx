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
      className={`w-full rounded-lg border p-4 ${toneClasses[presentation.tone]}`}
      aria-label="Current environment"
    >
      <div className="flex items-start justify-between gap-4">
        <div className="min-w-0">
          <p className="text-xs font-bold uppercase">
            {presentation.badgeLabel}
          </p>
          <h2 className="mt-1 text-sm font-bold sm:text-base">
            {presentation.title}
          </h2>
        </div>

        <span className="inline-flex shrink-0 items-center gap-1.5 text-xs font-semibold">
          {data.connected ? <Server size={14} /> : <CircleOff size={14} />}
          {statusLabel}
        </span>
      </div>

      <div className="mt-3 grid grid-cols-1 gap-1 text-xs sm:grid-cols-2 sm:text-sm">
        <p>Database: <strong>{presentation.databaseLabel}</strong></p>
        <p className="sm:text-right">API: <strong>{data.apiUrl}</strong></p>
        <p>Migration: <strong>{data.latestMigration}</strong></p>
        <p className="sm:text-right">Version: <strong>{data.version}</strong></p>
      </div>
    </section>
  );
};

export default EnvironmentCard;
