import { CircleOff, Server } from "lucide-react";

import { getEnvironmentPresentation } from "../../utils/environment";

const toneClasses = {
  dev: "alert-panel--success",
  prod: "alert-panel--warning",
  unknown: "alert-panel--neutral",
};

const EnvironmentCard = ({ systemInfoState }) => {
  const { data, status } = systemInfoState;
  const presentation = getEnvironmentPresentation(data.appEnv);
  const statusLabel = status === "loading"
    ? "Checking"
    : data.connected ? "Connected" : "Offline";

  return (
    <section
      className={`alert-panel w-full p-4 ${toneClasses[presentation.tone]}`}
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
