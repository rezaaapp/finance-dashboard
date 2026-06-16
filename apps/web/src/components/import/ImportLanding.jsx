import { FileText, Upload } from "lucide-react";
import { useRef } from "react";

const comingSoonProviders = [
  "BCA PDF",
  "SeaBank PDF",
  "GoPay PDF",
  "OVO PDF",
];

const ProviderBadge = ({ children, variant = "default" }) => (
  <span className={`inline-flex items-center rounded-full px-2.5 py-1 text-xs font-bold ${
    variant === "success"
      ? "bg-emerald-50 text-emerald-700 dark:bg-emerald-950/40 dark:text-emerald-300"
      : "bg-[var(--color-accent-bg)] text-accent"
  }`}>
    {children}
  </span>
);

const ImportLanding = () => {
  const fileInputRef = useRef(null);

  const openFilePicker = () => {
    fileInputRef.current?.click();
  };

  return (
    <div className="grid grid-cols-1 gap-6">
      <section>
        <h2 className="text-2xl font-bold text-main">
          Import Transaksi
        </h2>
        <p className="mt-2 max-w-3xl text-sm leading-6 text-muted sm:text-base">
          Import transaksi dari file mutasi bank untuk mempercepat pencatatan keuangan.
        </p>
      </section>

      <section className="grid grid-cols-1 gap-4 lg:grid-cols-2 xl:grid-cols-3">
        <article className="rounded-lg border border-gray-200 bg-white p-5 shadow-sm dark:border-[var(--color-border)] dark:bg-[var(--color-panel)]">
          <div className="flex items-start justify-between gap-4">
            <div className="flex min-w-0 items-center gap-3">
              <span className="flex h-11 w-11 shrink-0 items-center justify-center rounded-lg bg-[var(--color-accent-bg)] text-accent">
                <FileText size={22} />
              </span>
              <div className="min-w-0">
                <h3 className="truncate text-base font-bold text-main">
                  Blu PDF Statement
                </h3>
                <p className="mt-1 text-sm font-semibold text-emerald-700 dark:text-emerald-300">
                  Didukung
                </p>
              </div>
            </div>

            <ProviderBadge variant="success">Beta</ProviderBadge>
          </div>

          <button
            type="button"
            onClick={openFilePicker}
            className="primary-button mt-6 inline-flex min-h-11 w-full items-center justify-center gap-2 rounded-lg px-4 py-2 text-sm font-semibold sm:w-auto"
          >
            <Upload size={18} />
            Upload PDF
          </button>

          <input
            ref={fileInputRef}
            type="file"
            accept="application/pdf,.pdf"
            className="hidden"
          />
        </article>

        {comingSoonProviders.map((provider) => (
          <article
            key={provider}
            className="rounded-lg border border-gray-200 bg-white p-5 opacity-70 shadow-sm dark:border-[var(--color-border)] dark:bg-[var(--color-panel)]"
          >
            <div className="flex items-start justify-between gap-4">
              <div className="flex min-w-0 items-center gap-3">
                <span className="flex h-11 w-11 shrink-0 items-center justify-center rounded-lg bg-gray-100 text-muted dark:bg-[var(--color-panel-hover)]">
                  <FileText size={22} />
                </span>
                <div className="min-w-0">
                  <h3 className="truncate text-base font-bold text-main">
                    {provider}
                  </h3>
                  <p className="mt-1 text-sm font-semibold text-muted">
                    Belum tersedia
                  </p>
                </div>
              </div>

              <ProviderBadge>Coming Soon</ProviderBadge>
            </div>

            <button
              type="button"
              disabled
              className="mt-6 inline-flex min-h-11 w-full cursor-not-allowed items-center justify-center gap-2 rounded-lg border border-gray-200 px-4 py-2 text-sm font-semibold text-muted dark:border-[var(--color-border)] sm:w-auto"
            >
              Upload PDF
            </button>
          </article>
        ))}
      </section>

      <section className="rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm leading-6 text-amber-900 dark:border-amber-900/60 dark:bg-amber-950/30 dark:text-amber-200">
        Saat ini Import Transaksi hanya mendukung PDF e-Statement Blu.
        Dukungan source dana lain akan ditambahkan secara bertahap.
      </section>
    </div>
  );
};

export default ImportLanding;
