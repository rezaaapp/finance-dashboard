function KPICard({ title, value }) {
  return (
    <div className="bg-slate-800 rounded-2xl p-6 shadow-lg">
      <h2 className="text-slate-400 text-sm mb-2">
        {title}
      </h2>

      <p className="text-3xl font-bold text-white">
        Rp {Number(value).toLocaleString("id-ID")}
      </p>
    </div>
  );
}

export default KPICard;