import {
  CheckCircle2,
  ChevronDown,
  ChevronUp,
  LoaderCircle,
  RefreshCw,
  ShieldCheck,
  Tag,
} from "lucide-react";
import { useCallback, useEffect, useMemo, useState } from "react";

import {
  applyClassificationSuggestion,
  getUncategorizedGroups,
  runClassification,
} from "../api/classificationsApi";
import { formatPrivateRupiah, PRIVACY_MODES } from "../utils/privacy";

const FINANCIAL_TYPE_OPTIONS = [
  {
    value: "need",
    label: "Need",
    direction: "expense",
    helper: "Pengeluaran penting atau rutin.",
  },
  {
    value: "want",
    label: "Want",
    direction: "expense",
    helper: "Pengeluaran pilihan atau gaya hidup.",
  },
  {
    value: "saving",
    label: "Saving",
    direction: "saving_transfer",
    helper: "Tabungan, investasi, atau pemindahan dana.",
  },
  {
    value: "income",
    label: "Income",
    direction: "income",
    helper: "Pemasukan atau dana masuk.",
  },
];

const GROUP_TYPE_LABELS = {
  raw_category: "Kategori asli",
  title_keyword: "Kata awal transaksi",
  source_fund: "Sumber dana",
};

const PATTERN_TYPE_BY_GROUP = {
  raw_category: "raw_category_equals",
  title_keyword: "title_contains",
  source_fund: "source_fund_contains",
};

const getGroupKey = (group) => `${group.group_type}:${group.pattern}`;

const getDefaultCategory = (group) => (
  group?.group_type === "raw_category" ? group.pattern : ""
);

const formatDate = (value) => {
  if (!value) {
    return "-";
  }

  return new Intl.DateTimeFormat("id-ID", {
    day: "2-digit",
    month: "short",
    year: "numeric",
  }).format(new Date(value));
};

const getFriendlyError = (error) => {
  if (error?.response?.status === 401) {
    return "Sesi Anda sudah berakhir. Silakan masuk kembali.";
  }

  if (error?.response?.status === 403) {
    return "Workspace ini belum mengizinkan aksi tersebut.";
  }

  return "Kami belum bisa memproses review ini. Coba lagi sebentar.";
};

const buildDefaultForms = (groups, currentForms = {}) => (
  groups.reduce((nextForms, group) => {
    const key = getGroupKey(group);
    nextForms[key] = currentForms[key] || {
      financialType: "need",
      category: getDefaultCategory(group),
      error: "",
    };
    return nextForms;
  }, {})
);

const ReviewUncategorized = ({
  onUnauthorized,
  privacyMode = PRIVACY_MODES.normal,
}) => {
  const [groups, setGroups] = useState([]);
  const [forms, setForms] = useState({});
  const [isLoading, setIsLoading] = useState(true);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [submittingKey, setSubmittingKey] = useState("");
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [expandedGroups, setExpandedGroups] = useState({});

  const totalRows = useMemo(() => (
    groups.reduce((total, group) => total + Number(group.rows || 0), 0)
  ), [groups]);

  const totalAmount = useMemo(() => (
    groups.reduce((total, group) => total + Number(group.total_amount || 0), 0)
  ), [groups]);

  const averageAmount = totalRows > 0 ? totalAmount / totalRows : 0;

  const loadGroups = useCallback(async ({ silent = false } = {}) => {
    if (silent) {
      setIsRefreshing(true);
    } else {
      setIsLoading(true);
    }

    setError("");

    try {
      const response = await getUncategorizedGroups({ limit: 100 });
      const nextGroups = response?.groups || response || [];
      setGroups(nextGroups);
      setForms((currentForms) => buildDefaultForms(nextGroups, currentForms));
    } catch (requestError) {
      if (requestError?.response?.status === 401) {
        onUnauthorized?.();
        return;
      }

      setError(getFriendlyError(requestError));
    } finally {
      setIsLoading(false);
      setIsRefreshing(false);
    }
  }, [onUnauthorized]);

  useEffect(() => {
    loadGroups();
  }, [loadGroups]);

  const handleFormChange = (group, field, value) => {
    const key = getGroupKey(group);
    setForms((currentForms) => ({
      ...currentForms,
      [key]: {
        ...(currentForms[key] || {}),
        [field]: value,
        error: "",
      },
    }));
  };

  const handleApply = async (group) => {
    const key = getGroupKey(group);
    const form = forms[key] || {};
    const category = String(form.category || "").trim();
    const option = FINANCIAL_TYPE_OPTIONS.find((item) => (
      item.value === form.financialType
    ));

    if (!category) {
      setForms((currentForms) => ({
        ...currentForms,
        [key]: {
          ...(currentForms[key] || {}),
          error: "Isi kategori tujuan sebelum menyimpan rule.",
        },
      }));
      return;
    }

    setSubmittingKey(key);
    setNotice("");
    setError("");

    try {
      const response = await applyClassificationSuggestion({
        pattern_type: PATTERN_TYPE_BY_GROUP[group.group_type] || "title_contains",
        pattern: group.pattern,
        target_direction: option?.direction || "expense",
        target_financial_type: option?.value || "need",
        target_category: category,
        confidence_score: 0.9,
        reason: "Reviewed from Omon Uncategorized review.",
        apply_to_existing: true,
      });

      const updatedCount = Number(response?.updated_classifications || 0);
      const skippedManual = Number(response?.skipped_manual || 0);
      setNotice(
        `${updatedCount} transaksi diperbarui. ${
          skippedManual
            ? `${skippedManual} transaksi manual tetap dipertahankan.`
            : "Rule baru siap dipakai untuk transaksi berikutnya."
        }`
      );
      await loadGroups({ silent: true });
    } catch (requestError) {
      if (requestError?.response?.status === 401) {
        onUnauthorized?.();
        return;
      }

      setForms((currentForms) => ({
        ...currentForms,
        [key]: {
          ...(currentForms[key] || {}),
          error: getFriendlyError(requestError),
        },
      }));
    } finally {
      setSubmittingKey("");
    }
  };

  const handleRunClassification = async () => {
    setIsRefreshing(true);
    setNotice("");
    setError("");

    try {
      const response = await runClassification({ limit: 500 });
      const classified = Number(response?.classified || 0);
      const skipped = Number(response?.skipped || 0);
      setNotice(
        `Review otomatis selesai. ${classified} transaksi diklasifikasi, ${skipped} dilewati.`
      );
      await loadGroups({ silent: true });
    } catch (requestError) {
      if (requestError?.response?.status === 401) {
        onUnauthorized?.();
        return;
      }

      setError(getFriendlyError(requestError));
    } finally {
      setIsRefreshing(false);
    }
  };

  const toggleGroupDetails = (group) => {
    const key = getGroupKey(group);
    setExpandedGroups((currentGroups) => ({
      ...currentGroups,
      [key]: !currentGroups[key],
    }));
  };

  if (isLoading) {
    return (
      <section className="panel rounded-lg p-5 shadow-lg" role="status" aria-live="polite">
        <div className="flex items-center gap-3 text-sm font-semibold text-muted">
          <LoaderCircle size={18} className="animate-spin text-accent" />
          Menyiapkan daftar transaksi yang perlu direview...
        </div>
      </section>
    );
  }

  return (
    <div className="grid gap-5">
      <section className="panel rounded-lg p-4 shadow-lg sm:p-5">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
          <div className="max-w-2xl">
            <div className="flex items-center gap-3">
              <span className="icon-badge rounded-lg p-2">
                <Tag size={18} />
              </span>
              <div>
                <h2 className="text-xl font-bold text-main">
                  Review Uncategorized
                </h2>
                <p className="mt-1 text-sm leading-6 text-muted">
                  Kelompokkan transaksi yang belum punya tipe finansial agar ringkasan, chart, dan insight bisa lebih rapi.
                </p>
              </div>
            </div>
          </div>

          <div className="grid gap-2 sm:grid-cols-2 lg:min-w-[340px]">
            <div className="empty-state-panel rounded-lg p-3">
              <p className="text-xs font-bold uppercase text-subtle">
                Perlu review
              </p>
              <p className="mt-1 text-lg font-bold text-main">
                {totalRows.toLocaleString("id-ID")} transaksi
              </p>
            </div>
            <div className="empty-state-panel rounded-lg p-3">
              <p className="text-xs font-bold uppercase text-subtle">
                Rata-rata
              </p>
              <p className="mt-1 text-lg font-bold text-main">
                {formatPrivateRupiah(averageAmount, privacyMode)}
              </p>
              <p className="mt-1 text-xs text-muted">
                Total akumulasi {formatPrivateRupiah(totalAmount, privacyMode)}
              </p>
            </div>
          </div>
        </div>

        <div className="mt-5 flex flex-col gap-3 sm:flex-row">
          <button
            type="button"
            onClick={() => loadGroups({ silent: true })}
            disabled={isRefreshing || Boolean(submittingKey)}
            className="secondary-button min-h-11 rounded-lg px-4 py-2 text-sm font-semibold disabled:cursor-not-allowed disabled:opacity-60"
          >
            <RefreshCw size={16} className={isRefreshing ? "animate-spin" : ""} />
            Muat ulang
          </button>
          <button
            type="button"
            onClick={handleRunClassification}
            disabled={isRefreshing || Boolean(submittingKey)}
            className="primary-button min-h-11 rounded-lg px-4 py-2 text-sm font-semibold disabled:cursor-not-allowed disabled:opacity-60"
          >
            {isRefreshing ? <LoaderCircle size={16} className="animate-spin" /> : <ShieldCheck size={16} />}
            Jalankan klasifikasi ulang
          </button>
        </div>

        {notice && (
          <div className="alert-panel alert-panel--success mt-4 flex items-start gap-3 px-4 py-3 text-sm" role="status">
            <CheckCircle2 size={18} className="mt-0.5 shrink-0" />
            <p>{notice}</p>
          </div>
        )}

        {error && (
          <div className="alert-panel alert-panel--danger mt-4 px-4 py-3 text-sm" role="alert">
            {error}
          </div>
        )}
      </section>

      {groups.length === 0 ? (
        <section className="empty-state-panel rounded-lg p-6 text-center">
          <h3 className="text-lg font-bold text-main">
            Tidak ada transaksi Uncategorized.
          </h3>
          <p className="mx-auto mt-2 max-w-xl text-sm leading-6 text-muted">
            Semua transaksi yang terbaca sudah punya klasifikasi aktif. Jika baru menambah rule, muat ulang dashboard untuk melihat perubahan di chart.
          </p>
        </section>
      ) : (
        <section className="grid gap-4">
          {groups.map((group) => {
            const key = getGroupKey(group);
            const form = forms[key] || {};
            const selectedOption = FINANCIAL_TYPE_OPTIONS.find((item) => (
              item.value === form.financialType
            )) || FINANCIAL_TYPE_OPTIONS[0];
            const isSubmitting = submittingKey === key;
            const isExpanded = Boolean(expandedGroups[key]);
            const samples = group.samples || [];
            const visibleSamples = isExpanded ? samples : samples.slice(0, 3);
            const categoryInputId = `category-${key.replace(/[^a-z0-9]/gi, "-")}`;

            return (
              <article key={key} className="panel rounded-lg p-4 shadow-lg sm:p-5">
                <div className="grid gap-5 xl:grid-cols-[1fr_360px] xl:items-start">
                  <div>
                    <p className="text-xs font-bold uppercase tracking-[0.12em] text-subtle">
                      {GROUP_TYPE_LABELS[group.group_type] || "Pola transaksi"}
                    </p>
                    <h3 className="mt-2 break-words text-xl font-bold text-main">
                      {group.pattern}
                    </h3>

                    <div className="mt-4 grid gap-3 sm:grid-cols-3">
                      <div className="empty-state-panel rounded-lg p-3">
                        <p className="text-xs font-bold uppercase text-subtle">
                          Jumlah
                        </p>
                        <p className="mt-1 font-bold text-main">
                          {Number(group.rows || 0).toLocaleString("id-ID")} transaksi
                        </p>
                      </div>
                      <div className="empty-state-panel rounded-lg p-3">
                        <p className="text-xs font-bold uppercase text-subtle">
                          Rata-rata
                        </p>
                        <p className="mt-1 font-bold text-main">
                          {formatPrivateRupiah(group.average_amount, privacyMode)}
                        </p>
                      </div>
                      <div className="empty-state-panel rounded-lg p-3">
                        <p className="text-xs font-bold uppercase text-subtle">
                          Akumulasi
                        </p>
                        <p className="mt-1 font-bold text-main">
                          {formatPrivateRupiah(group.total_amount, privacyMode)}
                        </p>
                      </div>
                    </div>

                    <p className="mt-4 text-sm leading-6 text-muted">
                      Total di atas adalah akumulasi dari semua transaksi dalam grup ini. Cek contoh transaksi sebelum menyimpan rule.
                    </p>

                    <div className="mt-4 rounded-lg border border-[var(--color-border)]">
                      <div className="flex flex-col gap-2 border-b border-[var(--color-border)] px-4 py-3 sm:flex-row sm:items-center sm:justify-between">
                        <div>
                          <p className="text-sm font-bold text-main">
                            Contoh transaksi
                          </p>
                          <p className="text-xs leading-5 text-muted">
                            Menampilkan {visibleSamples.length} dari {Number(group.rows || 0).toLocaleString("id-ID")} transaksi yang cocok.
                          </p>
                        </div>

                        {samples.length > 3 && (
                          <button
                            type="button"
                            onClick={() => toggleGroupDetails(group)}
                            className="secondary-button min-h-9 rounded-lg px-3 py-1.5 text-xs font-semibold"
                            aria-expanded={isExpanded}
                          >
                            {isExpanded ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
                            {isExpanded ? "Ringkas" : "Lihat lagi"}
                          </button>
                        )}
                      </div>

                      {visibleSamples.length ? (
                        <div className="overflow-x-auto">
                          <table className="min-w-full text-left text-sm">
                            <thead className="text-xs uppercase text-subtle">
                              <tr>
                                <th className="px-4 py-3 font-bold">Tanggal</th>
                                <th className="px-4 py-3 font-bold">Transaksi</th>
                                <th className="px-4 py-3 font-bold">Sumber</th>
                                <th className="px-4 py-3 text-right font-bold">Nominal</th>
                              </tr>
                            </thead>
                            <tbody className="divide-y divide-[var(--color-border)]">
                              {visibleSamples.map((sample) => (
                                <tr key={sample.id}>
                                  <td className="whitespace-nowrap px-4 py-3 text-muted">
                                    {formatDate(sample.date)}
                                  </td>
                                  <td className="px-4 py-3">
                                    <p className="font-semibold text-main">
                                      {sample.title}
                                    </p>
                                    <p className="mt-1 text-xs text-muted">
                                      {sample.user} · {sample.raw_category}
                                    </p>
                                  </td>
                                  <td className="whitespace-nowrap px-4 py-3 text-muted">
                                    {sample.source_fund}
                                  </td>
                                  <td className="whitespace-nowrap px-4 py-3 text-right font-semibold text-main">
                                    {formatPrivateRupiah(sample.amount, privacyMode)}
                                  </td>
                                </tr>
                              ))}
                            </tbody>
                          </table>
                        </div>
                      ) : (
                        <div className="px-4 py-5 text-sm text-muted">
                          Detail contoh belum tersedia untuk grup ini.
                        </div>
                      )}
                    </div>
                  </div>

                  <div className="rounded-lg border border-[var(--color-border)] bg-[var(--color-panel-hover)] p-4">
                    <div className="grid gap-4">
                      <label className="grid gap-2 text-sm font-semibold text-main">
                        Tipe finansial
                        <select
                          value={form.financialType || "need"}
                          onChange={(event) => handleFormChange(group, "financialType", event.target.value)}
                          className="form-control w-full rounded-lg px-3 py-2"
                        >
                          {FINANCIAL_TYPE_OPTIONS.map((option) => (
                            <option key={option.value} value={option.value}>
                              {option.label}
                            </option>
                          ))}
                        </select>
                        <span className="text-xs font-normal leading-5 text-muted">
                          {selectedOption.helper}
                        </span>
                      </label>

                      <label className="grid gap-2 text-sm font-semibold text-main" htmlFor={categoryInputId}>
                        Kategori tujuan
                        <input
                          id={categoryInputId}
                          type="text"
                          value={form.category || ""}
                          onChange={(event) => handleFormChange(group, "category", event.target.value)}
                          className="form-control w-full rounded-lg px-3 py-2"
                          placeholder="Contoh: Food, Ibadah, Tagihan Bulanan"
                        />
                      </label>

                      {form.error && (
                        <p className="alert-panel alert-panel--danger px-3 py-2 text-sm" role="alert">
                          {form.error}
                        </p>
                      )}

                      <button
                        type="button"
                        onClick={() => handleApply(group)}
                        disabled={isSubmitting || Boolean(submittingKey && !isSubmitting)}
                        className="primary-button min-h-11 rounded-lg px-4 py-2 text-sm font-semibold disabled:cursor-not-allowed disabled:opacity-60"
                      >
                        {isSubmitting && <LoaderCircle size={16} className="animate-spin" />}
                        {isSubmitting ? "Menyimpan..." : "Simpan rule"}
                      </button>
                    </div>
                  </div>
                </div>
              </article>
            );
          })}
        </section>
      )}
    </div>
  );
};

export default ReviewUncategorized;
