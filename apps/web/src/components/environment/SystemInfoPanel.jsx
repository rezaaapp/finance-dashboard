import { CheckCircle2, CircleOff, Database, Server } from "lucide-react";

import { getEnvironmentPresentation } from "../../utils/environment";

const InfoRow = ({ label, value, mono = false }) => (
  <div className="grid min-w-0 grid-cols-[minmax(92px,0.7fr)_minmax(0,1.3fr)] gap-3 py-2 text-sm">
    <dt className="text-muted">{label}</dt>
    <dd className={`min-w-0 break-words text-right font-semibold text-main ${
      mono ? "font-mono text-xs" : ""
    }`}>
      {value || "Unavailable"}
    </dd>
  </div>
);

const SystemInfoPanel = ({ systemInfoState, compact = false }) => {
  const { data, status } = systemInfoState;
  const presentation = getEnvironmentPresentation(data.appEnv);
  const statusLabel = status === "loading"
    ? "Checking"
    : data.connected ? "Connected" : "Offline";

  return (
    <section
      className={compact
        ? "min-w-0"
        : "panel min-w-0 rounded-lg p-5 sm:p-6"}
      aria-label="System information"
    >
      {!compact && (
        <div className="mb-4 flex items-start justify-between gap-4 border-b border-[var(--color-border)] pb-4">
          <div className="min-w-0">
            <p className="text-xs font-bold uppercase text-muted">
              System Information
            </p>
            <h2 className="mt-1 text-lg font-bold text-main">
              {presentation.title}
            </h2>
          </div>

          <span className={`inline-flex shrink-0 items-center gap-2 rounded-full px-3 py-1 text-xs font-bold ${
            data.connected
              ? "bg-emerald-500/10 text-emerald-700 dark:text-emerald-300"
              : "bg-gray-500/10 text-gray-600 dark:text-gray-300"
          }`}>
            {data.connected ? <CheckCircle2 size={14} /> : <CircleOff size={14} />}
            {statusLabel}
          </span>
        </div>
      )}

      <dl className="divide-y divide-[var(--color-border)]">
        <InfoRow label="Environment" value={presentation.badgeLabel} />
        <InfoRow label="Profile" value={data.envProfile} />
        <InfoRow label="Database" value={presentation.databaseLabel} />
        <InfoRow label="DB target" value={data.dbTarget} />
        <InfoRow label="API" value={data.apiUrl} mono />
        <InfoRow label="Frontend port" value={data.frontendPort || "Unavailable"} />
        <InfoRow label="Backend port" value={data.backendPort || "Unavailable"} />
        {!compact && (
          <>
            <InfoRow label="Database host" value={data.databaseHost} mono />
            <InfoRow label="Database name" value={data.databaseName} />
            <InfoRow label="Import temp" value={data.importTempDir} mono />
          </>
        )}
        <InfoRow label="Migration" value={data.latestMigration} mono />
        <InfoRow label="Version" value={data.version} />
        {compact && <InfoRow label="Status" value={statusLabel} />}
      </dl>

      {!compact && (
        <div className="mt-4 flex items-start gap-3 rounded-lg bg-[var(--color-panel-hover)] px-4 py-3 text-sm text-muted">
          <Database size={17} className="mt-0.5 shrink-0" />
          <p className="min-w-0 leading-6">
            Host database sudah di-mask. Password, token, connection string,
            dan credential tidak pernah ditampilkan.
          </p>
        </div>
      )}

      {compact && (
        <div className="mt-3 flex items-center gap-2 text-xs text-muted">
          <Server size={14} />
          Safe runtime metadata only
        </div>
      )}
    </section>
  );
};

export default SystemInfoPanel;
