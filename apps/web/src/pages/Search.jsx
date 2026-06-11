import {
  ChevronDown,
  ChevronLeft,
  ChevronRight,
  ChevronUp,
  FileText,
  Loader2,
  Search as SearchIcon,
} from "lucide-react";
import { useEffect, useMemo, useRef, useState } from "react";

import { getInquiryDetail, searchInquiry } from "../api/inquiryApi";
import { formatRupiah } from "../utils/currency";


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


const InquiryEmptyState = () => (
  <div className="panel rounded-lg p-8 text-center">
    <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-lg bg-accent-glow text-accent">
      <SearchIcon size={22} />
    </div>
    <p className="mt-4 text-lg font-bold text-main">
      Apa yang ingin kamu cari?
    </p>
    <p className="mx-auto mt-2 max-w-xl text-sm leading-6 text-muted">
      Gunakan kata kunci seperti kategori, merchant, catatan, atau sumber dana.
    </p>
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


const InquiryNoResultState = () => (
  <section className="panel rounded-lg p-6 text-center">
    <p className="text-lg font-bold text-main">
      Tidak ditemukan transaksi yang sesuai.
    </p>
    <p className="mx-auto mt-2 max-w-xl text-sm leading-6 text-muted">
      Coba gunakan kata kunci lain seperti kategori, merchant, atau sumber dana.
    </p>
  </section>
);


const InquirySummaryCards = ({ result }) => (
  <section className="grid grid-cols-1 gap-4 md:grid-cols-3">
    <SummaryMetric
      label="Transactions"
      value={getTransactionCount(result)}
    />
    <SummaryMetric
      label="Total Amount"
      value={formatRupiah(result?.summary?.total_amount || 0)}
    />
    <SummaryMetric
      label="Average"
      value={formatRupiah(result?.summary?.average_amount || 0)}
    />
  </section>
);


const getInsights = (result) => (
  Array.isArray(result?.insights) ? result.insights : []
);


const InquirySmartInsights = ({ result }) => {
  const insights = getInsights(result);

  if (insights.length === 0) {
    return null;
  }

  return (
    <section className="panel rounded-lg p-5">
      <p className="text-xs font-bold uppercase tracking-[0.14em] text-subtle">
        Smart Insight
      </p>

      <div className="mt-4 grid grid-cols-1 gap-3 md:grid-cols-2">
        {insights.map((insight) => (
          <article
            key={`${insight.type}-${insight.title}`}
            className="rounded-lg border border-[var(--color-border)] bg-[var(--color-panel-hover)] p-4"
          >
            <h4 className="text-sm font-bold text-main">
              {insight.title || "Insight"}
            </h4>
            <p className="mt-2 text-sm leading-6 text-muted">
              {insight.message || "-"}
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
                  <th className="px-4 py-3 font-bold">Nama</th>
                  <th className="px-4 py-3 font-bold">Kategori</th>
                  <th className="px-4 py-3 font-bold">Source Dana</th>
                  <th className="px-4 py-3 text-right font-bold">Amount</th>
                  <th className="px-4 py-3 font-bold">Note</th>
                </tr>
              </thead>
              <tbody>
                {detailRows.map((transaction) => (
                  <tr key={transaction.id} className="table-row table-border">
                    <td className="whitespace-nowrap px-4 py-3">
                      {transaction.transaction_date || "-"}
                    </td>
                    <td className="min-w-56 px-4 py-3 font-semibold text-main">
                      {transaction.transaction_name || "-"}
                    </td>
                    <td className="whitespace-nowrap px-4 py-3">
                      {transaction.category || "-"}
                    </td>
                    <td className="whitespace-nowrap px-4 py-3">
                      {transaction.source_dana || "-"}
                    </td>
                    <td className="whitespace-nowrap px-4 py-3 text-right font-bold text-main">
                      {formatRupiah(transaction.amount || 0)}
                    </td>
                    <td className="min-w-48 px-4 py-3">
                      {transaction.note || "-"}
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
              Previous
            </button>

            <p className="text-center text-sm font-bold text-muted">
              Page {page}
            </p>

            <button
              type="button"
              onClick={onNextPage}
              className="secondary-button rounded-lg px-4 py-2 text-sm font-bold disabled:cursor-not-allowed disabled:opacity-60"
              disabled={disableNext}
            >
              Next
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
            Preview Transactions
          </h3>
          <p className="mt-1 text-sm text-muted">
            Latest matching transactions, max 10.
          </p>
        </div>
      </div>

      {result?.detail_available && (
        <p className="mb-3 rounded-lg bg-accent-glow px-4 py-2 text-sm font-semibold text-accent">
          Detail tersedia untuk hasil lainnya.
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
                {transaction.transaction_name || "-"}
              </p>
              <p className="mt-1 text-sm text-muted">
                {transaction.transaction_date || "-"} - {transaction.category || "-"} - {transaction.source_dana || "-"}
              </p>
            </div>

            <p className="text-base font-bold text-main sm:text-right">
              {formatRupiah(transaction.amount || 0)}
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
            {detailOpen ? "Sembunyikan Detail" : "Lihat Detail"}
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
          Ringkasan
        </p>
        <h3 className="mt-2 text-xl font-bold text-main">
          {result?.answer || "Ringkasan belum tersedia."}
        </h3>
      </section>

      <InquirySummaryCards result={result} />

      <InquirySmartInsights result={result} />

      {hasNoResult ? (
        <InquiryNoResultState />
      ) : (
        <InquiryPreviewList
          detailCache={detailCache}
          detailError={detailError}
          detailLoading={detailLoading}
          detailOpen={detailOpen}
          offset={offset}
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

      setError(err?.response?.data?.detail || "Search is not available.");
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = (event) => {
    event.preventDefault();
    runSearch();
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

      setDetailError(err?.response?.data?.detail || "Detail transaksi tidak tersedia.");
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
      <div>
        <h2 className="text-2xl font-bold text-main sm:text-3xl">
          Search
        </h2>
        <p className="mt-2 max-w-2xl text-sm leading-6 text-muted">
          Cari transaksi dari merchant, kategori, catatan, atau sumber dana.
        </p>
      </div>

      <section className="panel rounded-lg p-4 sm:p-5">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
          <div>
            <p className="text-xs font-bold uppercase tracking-[0.14em] text-subtle">
              Current Context
            </p>
            <p className="mt-2 text-sm font-semibold text-main">
              Year: {contextYear || "-"} · Month: {getMonthLabel(contextMonth)}
            </p>
          </div>

          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:min-w-[360px]">
            <label className="grid gap-1">
              <span className="text-xs font-bold uppercase tracking-[0.12em] text-subtle">
                Year
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
                Month
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

      <form onSubmit={handleSubmit} className="panel rounded-lg p-4 sm:p-5">
        <div className="flex flex-col gap-3 sm:flex-row">
          <label className="relative min-w-0 flex-1">
            <span className="sr-only">Search query</span>
            <SearchIcon
              size={18}
              className="pointer-events-none absolute left-4 top-1/2 -translate-y-1/2 text-subtle"
            />
            <input
              ref={searchInputRef}
              type="search"
              value={query}
              onChange={(event) => {
                setQuery(event.target.value);
                setError("");
              }}
              className="form-control w-full rounded-lg py-3 pl-11 pr-4 text-sm sm:text-base"
              placeholder="Cari transaksi, kategori, merchant, atau sumber dana..."
              maxLength={100}
            />
          </label>

          <button
            type="submit"
            className="primary-button h-12 rounded-lg px-5 font-bold disabled:cursor-not-allowed disabled:opacity-60"
            disabled={!isQueryValid || loading}
          >
            {loading ? <Loader2 size={18} className="animate-spin" /> : <SearchIcon size={18} />}
            Search
          </button>
        </div>

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

      {recentSearches.length > 0 && (
        <section className="panel rounded-lg p-4 sm:p-5">
          <p className="text-xs font-bold uppercase tracking-[0.14em] text-subtle">
            Recent Search
          </p>
          <div className="mt-3 flex flex-wrap gap-2">
            {recentSearches.map((recentSearch) => (
              <button
                key={`${recentSearch.query}-${recentSearch.year}-${recentSearch.month}-${recentSearch.timestamp}`}
                type="button"
                onClick={() => handleRecentSearchClick(recentSearch)}
                className="secondary-button min-h-10 rounded-lg px-3 py-2 text-left text-sm font-semibold disabled:cursor-not-allowed disabled:opacity-60"
                disabled={loading}
                title={`${recentSearch.query} (${recentSearch.year || "-"} / ${getMonthLabel(recentSearch.month)})`}
              >
                {recentSearch.query}
                <span className="ml-2 text-xs font-normal text-muted">
                  {recentSearch.year || "-"} · {getMonthLabel(recentSearch.month)}
                </span>
              </button>
            ))}
          </div>
        </section>
      )}

      {error && (
        <div className="rounded-lg border border-[var(--color-danger)] bg-[var(--color-danger-bg)] px-4 py-3 text-sm font-semibold text-[var(--color-danger)]">
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
          onDetailToggle={handleDetailToggle}
          onNextPage={handleNextPage}
          onPreviousPage={handlePreviousPage}
          page={page}
          result={result}
        />
      ) : !error ? (
        <InquiryEmptyState />
      ) : null}
    </div>
  );
};

export default Search;
