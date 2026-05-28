function KPICard({ title, value }) {
  return (
    <div className="panel rounded-lg p-6 shadow-lg">
      <h2 className="text-muted text-sm mb-2">
        {title}
      </h2>

      <p className="text-3xl font-bold text-main">
        Rp {Number(value).toLocaleString("id-ID")}
      </p>
    </div>
  );
}

export default KPICard;
