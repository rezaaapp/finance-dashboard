import {
  ChevronDown,
  ChevronLeft,
  ChevronRight,
  ChevronUp,
  X,
  FileText,
  Loader2,
  Search as SearchIcon,
} from "lucide-react";
import { useEffect, useMemo, useRef, useState } from "react";

import { getInquiryDetail, searchInquiry } from "../api/inquiryApi";
import { formatPrivateRupiah, PRIVACY_MODES } from "../utils/privacy";


const exampleQueries = ["kopi", "groceries", "indomaret", "transport"];
const MIN_QUERY_LENGTH = 2;
const DETAIL_LIMIT = 25;
const RECENT_SEARCHES_KEY = "finance-dashboard-recent-inquiries";

const monthOptions = [
  { value: "", label: "All Months" },
  { value: "1", label: "January" },
  { value: "2", label: "February" },
  { value: "3", label: "March" },
  { value: "4", label: "April" },
  { value: "5", label: "May" },
  { value: "6", label: "June" },
  { value: "7", label: "July" },
  { value: "8", label: "August" },
  { value: "9", label: "September" },
  { value: "10", label: "October" },
  { value: "11", label: "November" },
  { value: "12", label: "December" },
];


const getTransactionCount = (result) => (
  Number(result?.summary?.total_transactions || 0)
);


const getPreviewRows = (result) => (
  Array.isArray(result?.preview) ? result.preview.slice(0, 10) : []
);

const getDefaultYear = (selectedYear) => (
  String(selectedYear || new Date().getFullYear())
);


const getMonthLabel = (month) => (
  monthOptions.find((option) => option.value === String(month || ""))?.label
  || "All Months"
);

const getPeriodLabel = (year, month) => (
  `${year || "-"} · ${getMonthLabel(month)}`
);

const getSafeText = (value, fallback = "-") => {
  const text = String(value ?? "").trim();

  return text || fallback;
};

const maskTextAmounts = (text, privacyMode) => {
  const safeText = getSafeText(text, "");

  if (privacyMode !== PRIVACY_MODES.hide) {
    return safeText;
  }

  return safeText
    .replace(/Rp\s?[\d.,]+/gi, "Rp ••••••••")
    .replace(/\b\d{4,}(?:[.,]\d+)?\b/g, "••••");
};

const getDisplayQuery = (query, privacyMode) => {
  const safeQuery = getSafeText(query, "");

  if (privacyMode === PRIVACY_MODES.hide && /\d/.test(safeQuery)) {
    return "Pencarian nominal disembunyikan";
  }

  return safeQuery;
};

const formatSearchAmount = (value, privacyMode) => (
  formatPrivateRupiah(value || 0, privacyMode)
);


const readRecentSearches = () => {
  try {
    const storedValue = localStorage.getItem(RECENT_SEARCHES_KEY);
    const parsedValue = JSON.parse(storedValue || "[]");

    return Array.isArray(parsedValue) ? parsedValue.slice(0, 5) : [];
  } catch {
    return [];
  }
};


const buildRecentSearches = (currentSearches, nextSearch) => {
  const dedupedSearches = currentSearches.filter((search) => !(
    search.query === nextSearch.query
    && String(search.year || "") === String(nextSearch.year || "")
    && String(search.month || "") === String(nextSearch.month || "")
  ));

  return [nextSearch, ...dedupedSearches].slice(0, 5);
};


const SummaryMetric = ({ label, value }) => (
  <div className="panel rounded-lg p-4">
    <p className="text-xs font-bold uppercase tracking-[0.12em] text-subtle">
      {label}
    </p>
    <p className="mt-2 text-2xl font-bold text-main">
      {value}
    </p>
  </div>
);


const InquiryEmptyState = ({ hasRecentSearches }) => (
  <div className="panel rounded-lg p-8 text-center">
    <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-lg bg-accent-glow text-accent">
      <SearchIcon size={22} />
    </div>
    <p className="mt-4 text-lg font-bold text-main">
      Cari transaksi tanpa perlu istilah teknis.
    </p>
    <p className="mx-auto mt-2 max-w-xl text-sm leading-6 text-muted">
      Gunakan nama merchant, kategori, catatan, atau sumber dana. Hasil akan
      mengikuti konteks tahun dan bulan yang sedang dipilih.
    </p>
    {!hasRecentSearches && (
      <p className="mt-3 text-sm font-semibold text-subtle">
        Belum ada pencarian terbaru.
      </p>
    )}
  </div>
);


const SkeletonBlock = ({ className = "" }) => (
  <div className={`animate-pulse rounded-lg bg-[var(--color-panel-hover)] ${className}`} />
);


const InquiryLoadingState = () => (
  <div className="grid grid-cols-1 gap-6" aria-live="polite">
    <section className="panel rounded-lg p-5">
      <p className="text-xs font-bold uppercase tracking-[0.14em] text-subtle">
        Ringkasan
      </p>
      <div className="mt-3 flex items-center gap-3 text-sm font-semibold text-muted">
        <Loader2 size={18} className="animate-spin" />
        Omon sedang menyiapkan ringkasan...
      </div>
      <SkeletonBlock className="mt-5 h-7 w-full max-w-xl" />
    </section>

    <section className="grid grid-cols-1 gap-4 md:grid-cols-3">
      <SkeletonBlock className="h-24" />
      <SkeletonBlock className="h-24" />
      <SkeletonBlock className="h-24" />
    </section>

    <section className="panel rounded-lg p-5">
      <SkeletonBlock className="h-6 w-48" />
      <div className="mt-5 grid gap-4">
        <SkeletonBlock className="h-14" />
        <SkeletonBlock className="h-14" />
        <SkeletonBlock className="h-14" />
      </div>
    </section>
  </div>
);


const InquiryNoResultState = ({ query, periodLabel, privacyMode }) => (
  <section className="panel rounded-lg p-6 text-center">
    <p className="text-lg font-bold text-main">
      Belum ada hasil yang cocok.
    </p>
    <p className="mx-auto mt-2 max-w-xl text-sm leading-6 text-muted">
      Kami belum menemukan transaksi untuk “{getDisplayQuery(query, privacyMode)}”
      pada {periodLabel}. Coba gunakan nama merchant, kategori, atau kata yang
      lebih singkat.
    </p>
  </section>
);


const InquirySummaryCards = ({ result, privacyMode }) => (
  <section className="grid grid-cols-1 gap-4 md:grid-cols-3">
    <SummaryMetric
      label="Transaksi"
      value={getTransactionCount(result)}
    />
    <SummaryMetric
      label="Total nominal"
      value={formatSearchAmount(result?.summary?.total_amount, privacyMode)}
    />
    <SummaryMetric
      label="Rata-rata"
      value={formatSearchAmount(result?.summary?.average_amount, privacyMode)}
    />
  </section>
);


const getInsights = (result) => (
  Array.isArray(result?.insights) ? result.insights : []
);


const InquirySmartInsights = ({ result, privacyMode }) => {
  const insights = getInsights(result);

  if (insights.length === 0) {
    return null;
  }

  return (
    <section className="panel rounded-lg p-5">
      <p className="text-xs font-bold uppercase tracking-[0.14em] text-subtle">
        Ringkasan bantuan
      </p>

      <div className="mt-4 grid grid-cols-1 gap-3 md:grid-cols-2">
        {insights.map((insight) => (
          <article
            key={`${insight.type}-${insight.title}`}
            className="rounded-lg border border-[var(--color-border)] bg-[var(--color-panel-hover)] p-4"
          >
            <h4 className="text-sm font-bold text-main">
              {maskTextAmounts(insight.title || "Ringkasan", privacyMode)}
            </h4>
            <p className="mt-2 text-sm leading-6 text-muted">
              {maskTextAmounts(insight.message || "-", privacyMode)}
            </p>
          </article>
        ))}
      </div>
    </section>
  );
};


const getDetailItems = (detailPage) => (
  Array.isArray(detailPage?.items)
    ? detailPage.items
    : Array.isArray(detailPage?.transactions)
      ? detailPage.transactions
      : []
);


const DetailSkeletonRows = () => (
  <div className="grid gap-3">
    <SkeletonBlock className="h-12" />
    <SkeletonBlock className="h-12" />
    <SkeletonBlock className="h-12" />
  </div>
);


const InquiryEvidenceLayer = ({
  detailCache,
  detailError,
  detailLoading,
  offset,
  page,
  privacyMode,
  onPreviousPage,
  onNextPage,
}) => {
  const detailPage = detailCache[offset];
  const detailRows = getDetailItems(detailPage);
  const hasMore = Boolean(detailPage?.has_more);
  const disablePrevious = page <= 1 || detailLoading;
  const disableNext = detailLoading || !hasMore;

  return (
    <section className="mt-5 border-t border-[var(--color-border)] pt-5">
      <div className="mb-4 flex items-center gap-2">
        <FileText size={18} className="text-accent" />
        <h4 className="text-lg font-bold text-main">
          Detail Transaksi
        </h4>
      </div>

      {detailLoading && (
        <>
          <p className="mb-4 text-sm font-semibold text-muted">
            Memuat detail transaksi...
          </p>
          <DetailSkeletonRows />
        </>
      )}

      {!detailLoading && detailError && (
        <div className="rounded-lg border border-[var(--color-danger)] bg-[var(--color-danger-bg)] px-4 py-3 text-sm font-semibold text-[var(--color-danger)]">
          {detailError}
        </div>
      )}

      {!detailLoading && !detailError && detailRows.length > 0 && (
        <>
          <div className="overflow-x-auto rounded-lg border border-[var(--color-border)]">
            <table className="min-w-full border-collapse text-left text-sm">
              <thead className="table-header">
                <tr>
                  <th className="px-4 py-3 font-bold">Tanggal</th>
                  <th className="px-4 py-3 font-bold">Transaksi</th>
                  <th className="px-4 py-3 font-bold">Kategori</th>
                  <th className="px-4 py-3 font-bold">Source Dana</th>
                  <th className="px-4 py-3 text-right font-bold">Nominal</th>
                  <th className="px-4 py-3 font-bold">Catatan</th>
                </tr>
              </thead>
              <tbody>
                {detailRows.map((transaction) => (
                  <tr key={transaction.id || `${transaction.transaction_date}-${transaction.transaction_name}-${transaction.amount}`} className="table-row table-border">
                    <td className="whitespace-nowrap px-4 py-3">
                      {getSafeText(transaction.transaction_date)}
                    </td>
                    <td className="min-w-56 px-4 py-3 font-semibold text-main">
                      {getSafeText(transaction.transaction_name, "Transaksi tanpa nama")}
                    </td>
                    <td className="whitespace-nowrap px-4 py-3">
                      {getSafeText(transaction.category)}
                    </td>
                    <td className="whitespace-nowrap px-4 py-3">
                      {getSafeText(transaction.source_dana)}
                    </td>
                    <td className="whitespace-nowrap px-4 py-3 text-right font-bold text-main">
                      {formatSearchAmount(transaction.amount, privacyMode)}
                    </td>
                    <td className="min-w-48 px-4 py-3">
                      {getSafeText(transaction.note)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div className="mt-4 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <button
              type="button"
              onClick={onPreviousPage}
              className="secondary-button rounded-lg px-4 py-2 text-sm font-bold disabled:cursor-not-allowed disabled:opacity-60"
              disabled={disablePrevious}
            >
              <ChevronLeft size={16} />
              Sebelumnya
            </button>

            <p className="text-center text-sm font-bold text-muted">
              Halaman {page}
            </p>

            <button
              type="button"
              onClick={onNextPage}
              className="secondary-button rounded-lg px-4 py-2 text-sm font-bold disabled:cursor-not-allowed disabled:opacity-60"
              disabled={disableNext}
            >
              Berikutnya
              <ChevronRight size={16} />
            </button>
          </div>
        </>
      )}

      {!detailLoading && !detailError && detailPage && detailRows.length === 0 && (
        <div className="rounded-lg border border-dashed border-[var(--color-border)] px-4 py-6 text-center text-sm text-muted">
          Tidak ada detail transaksi untuk halaman ini.
        </div>
      )}
    </section>
  );
};


const InquiryPreviewList = ({
  detailCache,
  detailError,
  detailLoading,
  detailOpen,
  offset,
  periodLabel,
  privacyMode,
  onDetailToggle,
  onNextPage,
  onPreviousPage,
  page,
  result,
}) => {
  const previewRows = getPreviewRows(result);

  return (
    <section className="panel rounded-lg p-5">
      <div className="mb-4">
        <div>
          <h3 className="text-lg font-bold text-main">
            Hasil transaksi
          </h3>
          <p className="mt-1 text-sm text-muted">
            Menampilkan hingga 10 transaksi yang cocok pada {periodLabel}.
          </p>
        </div>
      </div>

      {result?.detail_available && (
        <p className="mb-3 rounded-lg bg-accent-glow px-4 py-2 text-sm font-semibold text-accent">
          Detail tambahan tersedia bila kamu ingin melihat hasil lainnya.
        </p>
      )}

      <div className="divide-y divide-[var(--color-border)]">
        {previewRows.map((transaction) => (
          <article
            key={transaction.id}
            className="grid grid-cols-1 gap-2 py-4 sm:grid-cols-[1fr_auto] sm:items-center"
          >
            <div className="min-w-0">
              <p className="truncate font-bold text-main">
                {getSafeText(transaction.transaction_name, "Transaksi tanpa nama")}
              </p>
              <p className="mt-1 text-sm text-muted">
                {getSafeText(transaction.transaction_date)} · {getSafeText(transaction.category)} · {getSafeText(transaction.source_dana)}
              </p>
            </div>

            <p className="text-base font-bold text-main sm:text-right">
              {formatSearchAmount(transaction.amount, privacyMode)}
            </p>
          </article>
        ))}
      </div>

      {result?.detail_available && (
        <div className="mt-5 border-t border-[var(--color-border)] pt-4">
          <button
            type="button"
            onClick={onDetailToggle}
            className="secondary-button rounded-lg px-4 py-2 text-sm font-bold disabled:cursor-not-allowed disabled:opacity-60"
            disabled={detailLoading}
          >
            {detailOpen ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
            {detailOpen ? "Sembunyikan detail" : "Lihat detail"}
          </button>
        </div>
      )}

      {detailOpen && (
        <InquiryEvidenceLayer
          detailCache={detailCache}
          detailError={detailError}
          detailLoading={detailLoading}
          offset={offset}
          page={page}
          privacyMode={privacyMode}
          onPreviousPage={onPreviousPage}
          onNextPage={onNextPage}
        />
      )}
    </section>
  );
};


const InquiryResult = ({
  detailCache,
  detailError,
  detailLoading,
  detailOpen,
  offset,
  periodLabel,
  privacyMode,
  onDetailToggle,
  onNextPage,
  onPreviousPage,
  page,
  result,
}) => {
  const totalTransactions = getTransactionCount(result);
  const previewRows = getPreviewRows(result);
  const hasNoResult = totalTransactions === 0 || previewRows.length === 0;

  return (
    <div className="grid grid-cols-1 gap-6">
      <section className="panel rounded-lg p-5">
        <p className="text-xs font-bold uppercase tracking-[0.14em] text-subtle">
          Hasil untuk “{getDisplayQuery(result?.query, privacyMode)}”
        </p>
        <h3 className="mt-2 text-xl font-bold text-main">
          {maskTextAmounts(result?.answer || "Ringkasan belum tersedia.", privacyMode)}
        </h3>
        <p className="mt-2 text-sm text-muted">
          Ditemukan {totalTransactions} transaksi pada {periodLabel}.
        </p>
      </section>

      <InquirySummaryCards result={result} privacyMode={privacyMode} />

      <InquirySmartInsights result={result} privacyMode={privacyMode} />

      {hasNoResult ? (
        <InquiryNoResultState
          query={result?.query}
          periodLabel={periodLabel}
          privacyMode={privacyMode}
        />
      ) : (
        <InquiryPreviewList
          detailCache={detailCache}
          detailError={detailError}
          detailLoading={detailLoading}
          detailOpen={detailOpen}
          offset={offset}
          periodLabel={periodLabel}
          privacyMode={privacyMode}
          onDetailToggle={onDetailToggle}
          onNextPage={onNextPage}
          onPreviousPage={onPreviousPage}
          page={page}
          result={result}
        />
      )}
    </div>
  );
};


const Search = ({
  availableYears = [],
  privacyMode = PRIVACY_MODES.normal,
  selectedYear,
  selectedMonth,
  onUnauthorized,
}) => {
  const [query, setQuery] = useState("");
  const [contextYear, setContextYear] = useState(() => getDefaultYear(selectedYear));
  const [contextMonth, setContextMonth] = useState(() => String(selectedMonth || ""));
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [detailOpen, setDetailOpen] = useState(false);
  const [detailLoading, setDetailLoading] = useState(false);
  const [detailError, setDetailError] = useState("");
  const [detailCache, setDetailCache] = useState({});
  const [page, setPage] = useState(1);
  const [offset, setOffset] = useState(0);
  const [recentSearches, setRecentSearches] = useState(() => readRecentSearches());
  const searchInputRef = useRef(null);

  const yearOptions = useMemo(() => {
    const years = [
      ...new Set([
        ...availableYears.map((year) => String(year)),
        String(contextYear || ""),
      ].filter(Boolean)),
    ];

    return years.sort((firstYear, secondYear) => Number(secondYear) - Number(firstYear));
  }, [availableYears, contextYear]);

  const trimmedQuery = query.trim();
  const isQueryValid = trimmedQuery.length >= MIN_QUERY_LENGTH;
  const periodLabel = getPeriodLabel(contextYear, contextMonth);
  const hasRecentSearches = recentSearches.length > 0;

  const resetDetailState = () => {
    setDetailOpen(false);
    setDetailLoading(false);
    setDetailError("");
    setDetailCache({});
    setPage(1);
    setOffset(0);
  };

  const resetResultState = () => {
    setError("");
    setResult(null);
    resetDetailState();
  };

  const saveRecentSearch = (search) => {
    const nextSearch = {
      query: search.query,
      year: String(search.year || ""),
      month: String(search.month || ""),
      timestamp: new Date().toISOString(),
    };
    const nextSearches = buildRecentSearches(recentSearches, nextSearch);

    setRecentSearches(nextSearches);
    localStorage.setItem(RECENT_SEARCHES_KEY, JSON.stringify(nextSearches));
  };

  useEffect(() => {
    const handleSearchShortcut = (event) => {
      const target = event.target;
      const isTypingTarget = (
        target instanceof HTMLInputElement
        || target instanceof HTMLTextAreaElement
        || target instanceof HTMLSelectElement
        || target?.isContentEditable
      );

      if (event.key !== "/" || isTypingTarget) {
        return;
      }

      event.preventDefault();
      searchInputRef.current?.focus();
    };

    window.addEventListener("keydown", handleSearchShortcut);

    return () => {
      window.removeEventListener("keydown", handleSearchShortcut);
    };
  }, []);

  useEffect(() => {
    const nextYear = getDefaultYear(selectedYear);
    const nextMonth = String(selectedMonth || "");

    setContextYear(nextYear);
    setContextMonth(nextMonth);
    setError("");
    setResult(null);
    setDetailOpen(false);
    setDetailLoading(false);
    setDetailError("");
    setDetailCache({});
    setPage(1);
    setOffset(0);
  }, [selectedYear, selectedMonth]);

  const runSearch = async (
    nextQuery = query,
    nextContext = {
      year: contextYear,
      month: contextMonth,
    },
  ) => {
    const nextTrimmedQuery = String(nextQuery || "").trim();
    const requestYear = String(nextContext.year || "");
    const requestMonth = String(nextContext.month || "");

    if (loading) {
      return;
    }

    if (!nextTrimmedQuery) {
      setError("Masukkan kata kunci pencarian.");
      return;
    }

    if (nextTrimmedQuery.length < MIN_QUERY_LENGTH) {
      setError("Kata kunci minimal 2 karakter.");
      return;
    }

    try {
      setLoading(true);
      setError("");
      resetDetailState();
      const response = await searchInquiry({
        query: nextTrimmedQuery,
        year: requestYear,
        month: requestMonth,
      });

      setResult(response);
      setQuery(nextTrimmedQuery);
      setContextYear(requestYear);
      setContextMonth(requestMonth);
      saveRecentSearch({
        query: nextTrimmedQuery,
        year: requestYear,
        month: requestMonth,
      });
    } catch (err) {
      console.error("Failed to search inquiry.");

      if (err?.response?.status === 401) {
        onUnauthorized();
        return;
      }

      setError("Pencarian belum dapat dilakukan. Periksa koneksi, lalu coba lagi.");
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = (event) => {
    event.preventDefault();
    runSearch();
  };

  const handleClearSearch = () => {
    setQuery("");
    resetResultState();
    searchInputRef.current?.focus();
  };

  const handleExampleClick = (exampleQuery) => {
    setQuery(exampleQuery);
    runSearch(exampleQuery);
  };

  const handleContextYearChange = (nextYear) => {
    setContextYear(nextYear);
    resetResultState();
  };

  const handleContextMonthChange = (nextMonth) => {
    setContextMonth(nextMonth);
    resetResultState();
  };

  const handleRecentSearchClick = (recentSearch) => {
    const nextYear = String(recentSearch.year || getDefaultYear(selectedYear));
    const nextMonth = String(recentSearch.month || "");

    setQuery(recentSearch.query);
    setContextYear(nextYear);
    setContextMonth(nextMonth);
    runSearch(recentSearch.query, {
      year: nextYear,
      month: nextMonth,
    });
  };

  const fetchDetailPage = async (nextOffset = offset, nextPage = page) => {
    if (!result?.query || detailLoading) {
      return;
    }

    if (detailCache[nextOffset]) {
      setOffset(nextOffset);
      setPage(nextPage);
      return;
    }

    try {
      setDetailLoading(true);
      setDetailError("");
      const response = await getInquiryDetail({
        query: result.query,
        year: contextYear,
        month: contextMonth,
        limit: DETAIL_LIMIT,
        offset: nextOffset,
      });

      setDetailCache((currentCache) => ({
        ...currentCache,
        [nextOffset]: response,
      }));
      setOffset(nextOffset);
      setPage(nextPage);
    } catch (err) {
      console.error("Failed to fetch inquiry detail.");

      if (err?.response?.status === 401) {
        onUnauthorized();
        return;
      }

      setDetailError("Detail transaksi belum dapat dimuat. Coba lagi sebentar lagi.");
    } finally {
      setDetailLoading(false);
    }
  };

  const handleDetailToggle = () => {
    if (detailLoading) {
      return;
    }

    if (detailOpen) {
      setDetailOpen(false);
      return;
    }

    setDetailOpen(true);
    fetchDetailPage(offset, page);
  };

  const handlePreviousPage = () => {
    const nextPage = Math.max(1, page - 1);
    const nextOffset = Math.max(0, offset - DETAIL_LIMIT);

    if (nextOffset === offset) {
      return;
    }

    fetchDetailPage(nextOffset, nextPage);
  };

  const handleNextPage = () => {
    const nextPage = page + 1;
    const nextOffset = offset + DETAIL_LIMIT;

    fetchDetailPage(nextOffset, nextPage);
  };

  return (
    <div className="grid grid-cols-1 gap-6">
      <section className="panel rounded-lg p-4 sm:p-5">
        <div className="flex flex-col gap-5 lg:flex-row lg:items-start lg:justify-between">
          <div className="min-w-0">
            <p className="text-xs font-bold uppercase text-accent">
              Cari transaksi
            </p>
            <h2 className="mt-1 text-2xl font-bold text-main sm:text-3xl">
              Temukan transaksi dengan kata yang kamu ingat.
            </h2>
            <p className="mt-2 max-w-2xl text-sm leading-6 text-muted">
              Cari berdasarkan merchant, kategori, catatan, atau sumber dana.
              Hasil mengikuti konteks periode yang dipilih.
            </p>
          </div>

          <div className="grid min-w-0 grid-cols-1 gap-3 sm:grid-cols-3 lg:w-[520px]">
            <div className="rounded-lg border border-[var(--color-border)] bg-[var(--color-panel-hover)] p-4">
              <p className="text-xs font-bold uppercase text-muted">
                Periode
              </p>
              <p className="mt-2 truncate text-sm font-bold text-main">
                {periodLabel}
              </p>
            </div>

            <div className="rounded-lg border border-[var(--color-border)] bg-[var(--color-panel-hover)] p-4 sm:col-span-2">
              <p className="text-xs font-bold uppercase text-muted">
                Privasi
              </p>
              <p className="mt-2 text-sm font-bold text-main">
                {privacyMode === PRIVACY_MODES.hide ? "Nominal disembunyikan" : "Nominal terlihat"}
              </p>
            </div>
          </div>
        </div>
      </section>

      <section className="panel rounded-lg p-4 sm:p-5">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
          <div>
            <p className="text-xs font-bold uppercase tracking-[0.14em] text-subtle">
              Konteks pencarian
            </p>
            <p className="mt-2 text-sm font-semibold text-main">
              Year: {contextYear || "-"} · Month: {getMonthLabel(contextMonth)}
            </p>
          </div>

          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:min-w-[360px]">
            <label className="grid gap-1">
              <span className="text-xs font-bold uppercase tracking-[0.12em] text-subtle">
                Tahun
              </span>
              <select
                value={contextYear}
                onChange={(event) => handleContextYearChange(event.target.value)}
                className="form-control w-full rounded-lg px-3 py-2 text-sm"
              >
                {yearOptions.map((year) => (
                  <option key={year} value={year}>
                    {year}
                  </option>
                ))}
              </select>
            </label>

            <label className="grid gap-1">
              <span className="text-xs font-bold uppercase tracking-[0.12em] text-subtle">
                Bulan
              </span>
              <select
                value={contextMonth}
                onChange={(event) => handleContextMonthChange(event.target.value)}
                className="form-control w-full rounded-lg px-3 py-2 text-sm"
              >
                {monthOptions.map((month) => (
                  <option key={month.value || "all"} value={month.value}>
                    {month.label}
                  </option>
                ))}
              </select>
            </label>
          </div>
        </div>
      </section>

      <form onSubmit={handleSubmit} className="panel rounded-lg p-4 sm:p-5" role="search">
        <div className="flex flex-col gap-3 sm:flex-row">
          <label className="relative min-w-0 flex-1">
            <span className="mb-2 block text-sm font-bold text-main">
              Kata kunci
            </span>
            <SearchIcon
              size={18}
              className="pointer-events-none absolute left-4 top-[3.05rem] text-subtle"
            />
            <input
              ref={searchInputRef}
              type="search"
              value={query}
              onChange={(event) => {
                setQuery(event.target.value);
                setError("");
              }}
              className="form-control w-full rounded-lg py-3 pl-11 pr-12 text-sm sm:text-base"
              placeholder="Cari merchant, kategori, atau transaksi"
              maxLength={100}
              aria-describedby="search-helper"
            />
            {query && (
              <button
                type="button"
                onClick={handleClearSearch}
                className="absolute right-3 top-[2.55rem] flex h-8 w-8 items-center justify-center rounded-lg text-muted transition-colors hover:bg-[var(--color-panel-hover)] hover:text-main disabled:opacity-50"
                aria-label="Bersihkan pencarian"
                disabled={loading}
              >
                <X size={16} />
              </button>
            )}
          </label>

          <button
            type="submit"
            className="primary-button min-h-12 rounded-lg px-5 font-bold disabled:cursor-not-allowed disabled:opacity-60 sm:self-end"
            disabled={!isQueryValid || loading}
          >
            {loading ? <Loader2 size={18} className="animate-spin" /> : <SearchIcon size={18} />}
            Cari
          </button>
        </div>

        <p id="search-helper" className="mt-2 text-sm text-muted">
          Tekan Enter untuk mencari. Minimal 2 karakter.
        </p>

        <div className="mt-4 flex flex-wrap gap-2">
          {exampleQueries.map((exampleQuery) => (
            <button
              key={exampleQuery}
              type="button"
              onClick={() => handleExampleClick(exampleQuery)}
              className="secondary-button min-h-9 rounded-lg px-3 py-1 text-sm font-semibold disabled:cursor-not-allowed disabled:opacity-60"
              disabled={loading}
            >
              {exampleQuery}
            </button>
          ))}
        </div>
      </form>

      {hasRecentSearches && (
        <section className="panel rounded-lg p-4 sm:p-5">
          <p className="text-xs font-bold uppercase tracking-[0.14em] text-subtle">
            Pencarian terbaru
          </p>
          <div className="mt-3 flex flex-wrap gap-2">
            {recentSearches.map((recentSearch) => (
              <button
                key={`${recentSearch.query}-${recentSearch.year}-${recentSearch.month}-${recentSearch.timestamp}`}
                type="button"
                onClick={() => handleRecentSearchClick(recentSearch)}
                className="secondary-button min-h-10 rounded-lg px-3 py-2 text-left text-sm font-semibold disabled:cursor-not-allowed disabled:opacity-60"
                disabled={loading}
                title={`${getDisplayQuery(recentSearch.query, privacyMode)} (${recentSearch.year || "-"} / ${getMonthLabel(recentSearch.month)})`}
              >
                {getDisplayQuery(recentSearch.query, privacyMode)}
                <span className="ml-2 text-xs font-normal text-muted">
                  {recentSearch.year || "-"} · {getMonthLabel(recentSearch.month)}
                </span>
              </button>
            ))}
          </div>
        </section>
      )}

      {error && (
        <div role="alert" className="rounded-lg border border-[var(--color-danger)] bg-[var(--color-danger-bg)] px-4 py-3 text-sm font-semibold text-[var(--color-danger)]">
          {error}
        </div>
      )}

      {loading ? (
        <InquiryLoadingState />
      ) : result ? (
        <InquiryResult
          detailCache={detailCache}
          detailError={detailError}
          detailLoading={detailLoading}
          detailOpen={detailOpen}
          offset={offset}
          periodLabel={periodLabel}
          privacyMode={privacyMode}
          onDetailToggle={handleDetailToggle}
          onNextPage={handleNextPage}
          onPreviousPage={handlePreviousPage}
          page={page}
          result={result}
        />
      ) : !error ? (
        <InquiryEmptyState hasRecentSearches={hasRecentSearches} />
      ) : null}
    </div>
  );
};

export default Search;
