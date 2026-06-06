import {
  Wallet,
  PiggyBank,
  Landmark,
  Minus,
  TrendingUp,
  TrendingDown,
} from "lucide-react";

import { formatPrivateRupiah } from "../utils/privacy";

const formatTrend = (value) => {
  if (!Number.isFinite(Number(value))) {
    return "N/A";
  }

  const numericValue = Number(value);
  const prefix = numericValue > 0 ? "+" : "";

  return new Intl.NumberFormat("id-ID", {
    maximumFractionDigits: 1,
    minimumFractionDigits: 1,
  }).format(numericValue).replace(/^/, prefix);
};

const SummaryCard = ({
  title,
  value,
  trend,
  trendDirection,
  comparisonLabel = "vs last month",
  privacyMode,
}) => {

  const getIcon = () => {

    if (title.includes("Expenses")) {
      return <Wallet size={28} />;
    }

    if (title.includes("Saving")) {
      return <PiggyBank size={28} />;
    }

    return <Landmark size={28} />;
  };

  const numericTrend = Number(trend);
  const hasTrend = Number.isFinite(numericTrend);
  const direction = trendDirection || (
    hasTrend
      ? (numericTrend > 0 ? "up" : numericTrend < 0 ? "down" : "flat")
      : "unavailable"
  );
  const isTrendUp = direction === "up";
  const isTrendDown = direction === "down";
  const isExpenseCard = title.includes("Expenses");
  const isTrendHealthy = isExpenseCard
    ? direction === "down" || direction === "flat"
    : direction === "up" || direction === "flat";
  const TrendIcon = isTrendUp
    ? TrendingUp
    : isTrendDown
      ? TrendingDown
      : Minus;
  const trendClassName = direction === "unavailable"
    ? "text-muted"
    : isTrendHealthy
      ? "metric-positive"
      : "metric-negative";
  const trendLabel = direction === "unavailable"
    ? comparisonLabel || "no previous data"
    : comparisonLabel;

  return (
    <div
      className="
        panel
        relative
        overflow-hidden
        rounded-lg
        p-4
        sm:p-6
        shadow-lg
        hover:scale-[1.02]
        transition-all
        duration-300
      "
    >

      {/* Glow Effect */}
      <div className="
        absolute
        -top-10
        -right-10
        w-32
        h-32
        bg-accent-glow
        rounded-full
        blur-3xl
      " />

      <div className="relative z-10">

        {/* Header */}
        <div className="flex justify-between items-start gap-3 mb-5 sm:mb-6">

          <div className="min-w-0 flex-1">
            <p className="text-muted text-sm mb-2">
              {title}
            </p>

            <h2 className="whitespace-nowrap text-[clamp(1.05rem,4.5vw,1.75rem)] font-bold leading-tight text-main tabular-nums">
              {formatPrivateRupiah(value, privacyMode)}
            </h2>
          </div>

          <div className="
            icon-badge
            shrink-0
            p-2.5
            sm:p-3
            rounded-xl
          ">
            {getIcon()}
          </div>

        </div>

        {/* Footer */}
        <div className="flex items-center gap-2">

          <div
            className={`
              flex items-center gap-1 text-sm font-bold sm:text-base
              ${trendClassName}
            `}
          >

            <TrendIcon size={16} strokeWidth={2.5} />

            {hasTrend ? `${formatTrend(numericTrend)}%` : "N/A"}

          </div>

          <span className="text-subtle text-sm">
            {trendLabel}
          </span>

        </div>

      </div>

    </div>
  );
};

export default SummaryCard;
