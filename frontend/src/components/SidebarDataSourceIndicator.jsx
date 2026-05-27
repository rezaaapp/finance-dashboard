import { Database } from "lucide-react";

const SidebarDataSourceIndicator = ({
  sheetName,
  isCollapsed = false,
}) => {
  const displayName = sheetName || "Waiting for data source";

  return (
    <div
      className={`
        mt-auto
        border-t
        border-slate-800
        pt-4
        ${isCollapsed ? "flex justify-center" : ""}
      `}
      title={`Connected: ${displayName}`}
    >
      {isCollapsed ? (
        <span className="relative flex h-8 w-8 items-center justify-center rounded-xl border border-slate-800 bg-slate-900/70 text-emerald-400">
          <span className="absolute right-1.5 top-1.5 h-2 w-2 rounded-full bg-emerald-500 shadow-[0_0_8px_rgba(16,185,129,0.9)] animate-pulse" />
          <Database size={15} />
        </span>
      ) : (
        <div className="flex items-start gap-2">
          <span className="mt-1.5 h-2 w-2 shrink-0 rounded-full bg-emerald-500 shadow-[0_0_8px_rgba(16,185,129,0.9)] animate-pulse" />
          <div className="min-w-0">
            <p className="text-[10px] font-mono uppercase tracking-wide text-slate-500">
              Connected
            </p>
            <p className="mt-1 truncate font-mono text-[10px] tracking-wide text-slate-400">
              {displayName}
            </p>
          </div>
        </div>
      )}
    </div>
  );
};

export default SidebarDataSourceIndicator;
