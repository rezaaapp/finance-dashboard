import { X } from "lucide-react";
import { useMemo, useState } from "react";

import { formatPrivateRupiah } from "../../utils/privacy";

const REASON_LABELS = {
  IMPORTED: "Berhasil diimpor",
  UPDATED: "Transaksi existing diperbarui",
  DUPLICATE_BATCH: "Duplikat dalam Spreadsheet ini",
  ALREADY_IMPORTED: "Sudah pernah diimpor",
  EXISTING_TRANSACTION: "Sudah ada di workspace",
  VALIDATION_FAILED: "Format belum sesuai",
  DATABASE_WRITE_FAILED: "Belum bisa disimpan ke Omon",
  UNKNOWN: "Belum diketahui",
};

const STATUSES = ["inserted", "updated", "skipped", "failed"];
const STATUS_LABELS = {
  inserted: "Baru",
  updated: "Diperbarui",
  skipped: "Dilewati",
  failed: "Gagal",
};

export default function ImportResultDetailsModal({ result, onClose, privacyMode }) {
  const available = useMemo(
    () => STATUSES.filter((status) => (result?.details?.[status] || []).length > 0),
    [result]
  );
  const [active, setActive] = useState(available[0] || "inserted");
  const rows = result?.details?.[active] || [];
  const money = (value) => formatPrivateRupiah(value, privacyMode);

  return (
    <div className="fixed inset-0 z-50 flex items-end justify-center bg-black/50 p-0 md:items-center md:p-6" role="dialog" aria-modal="true" aria-label="Detail hasil sinkronisasi">
      <div className="dialog-panel max-h-[92vh] w-full overflow-hidden rounded-t-3xl md:max-w-6xl md:rounded-3xl">
        <div className="flex items-center justify-between border-b border-[var(--color-border)] px-5 py-4">
          <div>
            <h2 className="text-lg font-bold text-main">Detail hasil sinkronisasi</h2>
            <p className="text-sm text-muted">Maksimal 500 baris per status.</p>
          </div>
          <button type="button" onClick={onClose} className="secondary-button rounded-xl p-2" aria-label="Tutup detail hasil sinkronisasi">
            <X size={18} />
          </button>
        </div>

        <div className="flex gap-2 overflow-x-auto border-b border-[var(--color-border)] px-5 py-3">
          {STATUSES.map((status) => {
            const count = result?.details?.[status]?.length || 0;
            return (
              <button
                key={status}
                type="button"
                disabled={!count}
                onClick={() => setActive(status)}
                className={`rounded-xl border px-3 py-2 text-sm font-bold ${active === status ? "border-[var(--success-border)] bg-[var(--success-bg)] text-[var(--success-text)]" : "border-transparent text-muted"} disabled:opacity-40`}
              >
                {STATUS_LABELS[status]} ({count})
              </button>
            );
          })}
        </div>

        <div className="max-h-[68vh] overflow-auto p-5">
          <div className="hidden overflow-x-auto md:block">
            <table className="w-full text-left text-sm">
              <thead className="text-muted">
                <tr>
                  {["Sheet", "Tanggal", "Merchant", "Nominal", "Pemilik", "Alasan"].map((label) => (
                    <th key={label} className="px-3 py-2">{label}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {rows.map((row, index) => (
                  <tr key={`${row.sheet_name}-${row.date}-${index}`} className="border-t border-[var(--color-border)]">
                    <td className="px-3 py-3">{row.sheet_name || "-"}</td>
                    <td className="px-3 py-3">{row.date || "-"}</td>
                    <td className="px-3 py-3 font-semibold text-main">{row.merchant || "-"}</td>
                    <td className="px-3 py-3">{money(row.amount)}</td>
                    <td className="px-3 py-3">{row.owner || "-"}</td>
                    <td className="px-3 py-3">{REASON_LABELS[row.reason] || REASON_LABELS.UNKNOWN}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div className="space-y-3 md:hidden">
            {rows.map((row, index) => (
              <article key={`${row.sheet_name}-${row.date}-${index}`} className="rounded-2xl border border-[var(--color-border)] p-4">
                <div className="flex justify-between gap-3">
                  <p className="font-bold text-main">{row.merchant || "Transaksi"}</p>
                  <p className="font-bold text-main">{money(row.amount)}</p>
                </div>
                <p className="mt-1 text-xs text-muted">{row.sheet_name || "Sheet"} - {row.date || "Tanpa tanggal"}</p>
                <p className="mt-2 text-sm text-muted">{row.owner || "Pemilik belum tersedia"}</p>
                <p className="mt-2 text-sm font-semibold">{REASON_LABELS[row.reason] || REASON_LABELS.UNKNOWN}</p>
              </article>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
