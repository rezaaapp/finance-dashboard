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

    if (title.includes("Pengeluaran")) {
      return <Wallet size={28} />;
    }

    if (title.includes("Saving")) {
      return <PiggyBank size={28} />;
    }

    return <Landmark size={28} />;
  };

  const isPositive = trend >= 0;

  return (
    <div
      className="
        panel
        relative
        overflow-hidden
        rounded-2xl
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

            <h2 className="break-words text-[clamp(1.35rem,6vw,1.875rem)] font-bold text-main leading-tight">
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
              flex items-center gap-1 text-sm font-semibold
              ${isPositive
                ? "text-emerald-400"
                : "text-red-400"}
            `}
          >

            {isPositive
              ? <TrendingUp size={16} />
              : <TrendingDown size={16} />
            }

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
