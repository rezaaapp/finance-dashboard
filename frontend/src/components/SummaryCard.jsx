import { formatRupiah } from "../utils/currency";

const SummaryCard = ({ title, value }) => {
  return (
    <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 shadow-lg hover:scale-[1.02] transition-all duration-300">
      
      <h3 className="text-slate-400 text-sm mb-2">
        {title}
      </h3>

      <p className="text-3xl font-bold text-white">
        {formatRupiah(value)}
      </p>

    </div>
  );
};

export default SummaryCard;