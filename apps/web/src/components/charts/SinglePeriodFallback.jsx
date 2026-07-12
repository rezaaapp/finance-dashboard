const SinglePeriodFallback = ({
  title = "Tren",
  description = "Data baru tersedia untuk satu periode. Pilih rentang yang lebih panjang untuk melihat tren.",
}) => (
  <div className="empty-state-panel flex min-h-[220px] items-center justify-center px-5 py-8 text-center">
    <div className="max-w-sm">
      <p className="text-sm font-bold text-main">
        {title}
      </p>
      <p className="mt-2 text-sm leading-6 text-muted">
        {description}
      </p>
    </div>
  </div>
);

export default SinglePeriodFallback;
