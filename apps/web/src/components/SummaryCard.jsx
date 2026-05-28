import {
  Wallet,
  PiggyBank,
  Landmark,
  TrendingUp,
  TrendingDown,
} from "lucide-react";

import { formatPrivateRupiah } from "../utils/privacy";

const formatTrend = (value) => {
  return new Intl.NumberFormat("id-ID", {
    maximumFractionDigits: 2,
  }).format(Math.abs(value || 0));
};

const SummaryCard = ({
  title,
  value,
  trend = 0,
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

  const isTrendUp = trend >= 0;
  const isExpenseCard = title.includes("Expenses");
  const isTrendHealthy = isExpenseCard ? trend <= 0 : isTrendUp;
  const TrendIcon = isTrendUp ? TrendingUp : TrendingDown;

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
              ${isTrendHealthy
                ? "metric-positive"
                : "metric-negative"}
            `}
          >

            <TrendIcon size={16} strokeWidth={2.5} />

            {formatTrend(trend)}%

          </div>

          <span className="text-subtle text-sm">
            vs last month
          </span>

        </div>

      </div>

    </div>
  );
};

export default SummaryCard;
