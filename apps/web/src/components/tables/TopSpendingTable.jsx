import { formatPrivateRupiah } from "../../utils/privacy";

const formatDate = (value) => {
  if (!value) {
    return "";
  }

  return new Date(value).toLocaleDateString("id-ID");
};

const TopSpendingTable = ({ data = [], privacyMode }) => {
  return (
    <div className="panel rounded-lg p-4 sm:p-5">

      <h2 className="text-xl font-bold mb-6 text-main">
        Top Spending
      </h2>

      {data.length === 0 ? (
        <div className="rounded-xl border border-dashed border-[var(--color-border)] p-6 text-center text-sm text-muted">
          No expense transactions available for this period.
        </div>
      ) : (
        <>
          <div className="hidden overflow-x-auto md:block">

            <table className="w-full min-w-[780px] text-sm">

              <thead>
                <tr className="table-header table-border text-muted">

                  <th className="text-left px-3 py-3">
                    Transaction
                  </th>

                  <th className="text-left px-3 py-3">
                    Category
                  </th>

                  <th className="text-left px-3 py-3">
                    Name
                  </th>

                  <th className="text-left px-3 py-3">
                    Source
                  </th>

                  <th className="px-3 py-3 text-right">
                    Amount
                  </th>

                </tr>
              </thead>

              <tbody>

                {data.map((item, index) => (

                  <tr
                    key={`${item.nama_transaksi}-${index}`}
                    className="table-row table-border transition"
                  >

                    <td className="max-w-[260px] px-3 py-4 text-main">
                      <div className="truncate" title={item.nama_transaksi}>
                        {item.nama_transaksi}
                      </div>
                      {item.date && (
                        <div className="mt-1 text-xs text-muted">
                          {formatDate(item.date)}
                        </div>
                      )}
                    </td>

                    <td className="px-3 py-4 text-soft">
                      {item.kategori}
                    </td>

                    <td className="px-3 py-4 text-soft">
                      {item.nama}
                    </td>

                    <td className="px-3 py-4 text-soft">
                      {item.source_fund || "-"}
                    </td>

                    <td className="px-3 py-4 text-right font-semibold text-accent">
                      {formatPrivateRupiah(item.harga, privacyMode)}
                    </td>

                  </tr>

                ))}

              </tbody>

            </table>

          </div>

          <div className="grid grid-cols-1 gap-3 md:hidden">
            {data.map((item, index) => (
              <div
                key={`${item.nama_transaksi}-${index}`}
                className="rounded-lg border border-[var(--color-border)] bg-[var(--color-panel-hover)] p-4"
              >
                <div className="flex items-start justify-between gap-3">
                  <div className="min-w-0">
                    <p className="break-words font-semibold text-main">
                      {item.nama_transaksi}
                    </p>
                    <p className="mt-1 text-sm text-soft">
                      {[item.kategori, item.nama, item.source_fund]
                        .filter(Boolean)
                        .join(" - ")}
                    </p>
                    {item.date && (
                      <p className="mt-2 text-xs text-muted">
                        {formatDate(item.date)}
                      </p>
                    )}
                    {item.note && (
                      <p className="mt-2 line-clamp-2 text-xs text-muted">
                        {item.note}
                      </p>
                    )}
                  </div>

                  <p className="shrink-0 text-right text-sm font-bold text-accent">
                    {formatPrivateRupiah(item.harga, privacyMode)}
                  </p>
                </div>
              </div>
            ))}
          </div>
        </>
      )}

    </div>
  );
};

export default TopSpendingTable;
