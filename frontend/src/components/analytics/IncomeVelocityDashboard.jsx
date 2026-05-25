import { AlertTriangle, Gauge, Info, TimerReset } from "lucide-react";
import { useMemo } from "react";

import {
  formatPrivateRupiah,
  maskNumber,
} from "../../utils/privacy";

const formatDate = (dateString) => (
  dateString
    ? new Date(dateString).toLocaleDateString("id-ID")
    : "-"
);

const getPeriodLabel = (periodString = "") => {
  const [year, month] = periodString.split("-");

  if (!year || !month) {
    return "-";
  }

  return new Date(Number(year), Number(month) - 1, 1).toLocaleDateString(
    "id-ID",
    {
      month: "long",
      year: "numeric",
    }
  );
};

const getLatestPeriod = (transactions) => (
  transactions.reduce((latestPeriod, transaction) => {
    const period = transaction.date?.slice(0, 7);

    if (!period) {
      return latestPeriod;
    }

    return !latestPeriod || period > latestPeriod
      ? period
      : latestPeriod;
  }, "")
);

const MetricTooltip = ({ children }) => (
  <div className="pointer-events-none absolute left-0 top-full z-40 mt-3 hidden w-[min(22rem,calc(100vw-2rem))] rounded-xl border border-slate-700 bg-slate-950 p-4 text-left text-xs leading-5 text-slate-200 shadow-2xl group-hover/tooltip:block group-focus-within/tooltip:block">
    {children}
  </div>
);

const MetricCard = ({
  title,
  value,
  description,
  accentClass,
  iconBgClass,
  icon: Icon,
  children,
}) => (
  <div className="group/tooltip relative rounded-xl border border-slate-800 bg-slate-900/70 p-5">
    <div className="mb-5 flex items-start justify-between gap-4">
      <div>
        <div className="flex items-center gap-2">
          <p className="text-sm font-semibold text-slate-400">
            {title}
          </p>
          <Info size={14} className="text-slate-500" />
        </div>
        <p className="mt-1 text-xs text-slate-500">
          {description}
        </p>
      </div>

      <div className={`rounded-xl p-3 ${iconBgClass} ${accentClass}`}>
        <Icon size={22} />
      </div>
    </div>

    <p className={`break-words text-3xl font-bold ${accentClass}`}>
      {value}
    </p>

    <MetricTooltip>
      {children}
    </MetricTooltip>
  </div>
);

const IncomeVelocityDashboard = ({
  rawTransactions = [],
  privacyMode,
}) => {
  const velocity = useMemo(() => {
    const latestPeriod = getLatestPeriod(rawTransactions);
    const periodTransactions = rawTransactions.filter((transaction) => (
      transaction.date?.startsWith(latestPeriod)
    ));
    const incomeTransactions = periodTransactions.filter((transaction) => (
      transaction.category === "Income"
    ));
    const spendingTransactions = periodTransactions
      .filter((transaction) => (
        transaction.category !== "Income"
        && transaction.category !== "Saving"
      ))
      .sort((a, b) => a.date.localeCompare(b.date));

    const totalIncome = incomeTransactions.reduce((sum, transaction) => (
      sum + Number(transaction.amount || 0)
    ), 0);
    const totalSpending = spendingTransactions.reduce((sum, transaction) => (
      sum + Number(transaction.amount || 0)
    ), 0);
    const threshold = totalIncome * 0.5;
    const latestDate = periodTransactions.reduce((date, transaction) => (
      !date || transaction.date > date ? transaction.date : date
    ), "");
    const elapsedDays = latestDate
      ? Number(latestDate.slice(8, 10))
      : 0;

    let cumulativeSpending = 0;
    let burnDate = "";
    let burnAmount = 0;

    spendingTransactions.some((transaction) => {
      cumulativeSpending += Number(transaction.amount || 0);

      if (cumulativeSpending >= threshold && !burnDate) {
        burnDate = transaction.date;
        burnAmount = cumulativeSpending;
        return true;
      }

      return false;
    });

    const dailyBurnRate = elapsedDays > 0
      ? totalSpending / elapsedDays
      : 0;
    const remainingFunds = totalIncome - totalSpending;
    const runwayDays = dailyBurnRate > 0 && remainingFunds > 0
      ? Math.floor(remainingFunds / dailyBurnRate)
      : 0;
    const spendingProgress = totalIncome > 0
      ? Math.min(totalSpending / totalIncome * 100, 100)
      : 0;

    return {
      latestPeriod,
      totalIncome,
      totalSpending,
      threshold,
      burnAmount,
      burnDate,
      d2b50: burnDate ? Number(burnDate.slice(8, 10)) : null,
      elapsedDays,
      dailyBurnRate,
      remainingFunds,
      runwayDays,
      spendingProgress,
    };
  }, [rawTransactions]);

  const maskedProgress = maskNumber(velocity.spendingProgress, privacyMode);
  const isCritical = velocity.d2b50 !== null && velocity.d2b50 < 7;

  return (
    <section className="rounded-xl border border-slate-800 bg-slate-900/50 p-4 shadow-lg sm:p-6">
      <div className="mb-6">
        <h2 className="text-xl font-bold text-main">
          Income Velocity
        </h2>
        <p className="mt-1 text-sm text-muted">
          Burn pace analysis for {getPeriodLabel(velocity.latestPeriod)}
        </p>
      </div>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <MetricCard
          title="Days to Burn 50%"
          value={velocity.d2b50 === null ? "-" : `${velocity.d2b50} hari`}
          description="Hari saat spending melewati 50% income."
          accentClass="text-cyan-400"
          iconBgClass="bg-cyan-400/15"
          icon={TimerReset}
        >
          <p>
            Total Income:{" "}
            <span className="font-bold text-white">
              {formatPrivateRupiah(velocity.totalIncome, privacyMode)}
            </span>
            .
          </p>
          <p>
            Total Pengeluaran Saat Menyentuh 50%:{" "}
            <span className="font-bold text-white">
              {formatPrivateRupiah(velocity.burnAmount || velocity.threshold, privacyMode)}
            </span>
            .
          </p>
          <p>
            Terjadi pada tanggal:{" "}
            <span className="font-bold text-white">
              {formatDate(velocity.burnDate)}
            </span>
            .
          </p>
          {isCritical && (
            <p className="mt-2 inline-flex items-center gap-1 rounded-full bg-red-500/15 px-2 py-1 font-bold text-red-300">
              <AlertTriangle size={13} />
              Critical
            </p>
          )}
        </MetricCard>

        <MetricCard
          title="Daily Burn Rate Score"
          value={formatPrivateRupiah(velocity.dailyBurnRate, privacyMode)}
          description="Rata-rata pengeluaran per hari berjalan."
          accentClass="text-emerald-400"
          iconBgClass="bg-emerald-400/15"
          icon={Gauge}
        >
          <p>
            Total pengeluaran bulan ini (
            <span className="font-bold text-white">
              {formatPrivateRupiah(velocity.totalSpending, privacyMode)}
            </span>
            ) dibagi dengan{" "}
            <span className="font-bold text-white">
              {velocity.elapsedDays}
            </span>{" "}
            hari berjalan.
          </p>
        </MetricCard>
      </div>

      <div className="mt-6 rounded-xl border border-slate-800 bg-slate-900/70 p-5">
        <div className="mb-4 flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <h3 className="font-bold text-main">
              The Runway Calendar
            </h3>
            <p className="text-sm text-muted">
              Current spending runway against monthly income.
            </p>
          </div>
          <p className="font-mono text-sm font-bold text-cyan-400">
            {maskedProgress.toFixed(1)}%
          </p>
        </div>

        <div className="group/tooltip relative">
          <div className="h-5 overflow-hidden rounded-full bg-slate-800">
            <div
              className={`h-full rounded-full transition-all duration-500 ${
                velocity.spendingProgress >= 100
                  ? "bg-red-500"
                  : velocity.spendingProgress >= 75
                    ? "bg-amber-400"
                    : "bg-cyan-400"
              }`}
              style={{ width: `${velocity.spendingProgress}%` }}
            />
          </div>

          <MetricTooltip>
            <p>
              Sisa dana Anda saat ini{" "}
              <span className="font-bold text-white">
                {formatPrivateRupiah(velocity.remainingFunds, privacyMode)}
              </span>
              .
            </p>
            <p>
              Estimasi pengeluaran harian{" "}
              <span className="font-bold text-white">
                {formatPrivateRupiah(velocity.dailyBurnRate, privacyMode)}
              </span>
              .
            </p>
            <p>
              Dana diprediksi habis dalam{" "}
              <span className="font-bold text-white">
                {velocity.runwayDays}
              </span>{" "}
              hari lagi jika pola belanja konsisten.
            </p>
          </MetricTooltip>
        </div>

        <p className="mt-4 text-sm leading-6 text-slate-300">
          Dengan burn rate saat ini, sisa dana aman sekitar{" "}
          <span className="font-bold text-emerald-400">
            {formatPrivateRupiah(velocity.remainingFunds, privacyMode)}
          </span>
          , estimasi runway{" "}
          <span className="font-bold text-cyan-400">
            {velocity.runwayDays} hari
          </span>
          .
        </p>
      </div>
    </section>
  );
};

export default IncomeVelocityDashboard;
