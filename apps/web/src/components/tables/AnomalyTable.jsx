import { memo, useMemo } from "react";

import { formatPrivateRupiah } from "../../utils/privacy";

const formatTransactionDate = (value) => (
  new Date(value).toLocaleDateString("id-ID")
);

const AnomalyTable = memo(({ data, privacyMode }) => {
  const rows = useMemo(() => (
    data.map((item, index) => ({
      id: `${item["Waktu Transaksi"]}-${item["Nama Transaksi"]}-${index}`,
      date: formatTransactionDate(item["Waktu Transaksi"]),
      transaction: item["Nama Transaksi"],
      category: item["Kategori"],
      name: item["Nama"],
      amount: item["Harga"],
    }))
  ), [data]);

  return (
    <div className="panel rounded-2xl p-4 sm:p-6">
      <h2 className="mb-6 text-xl font-bold text-red-400 sm:text-2xl">
        Anomaly Detection
      </h2>

      {rows.length === 0 ? (
        <div className="text-muted">
          No anomalies detected
        </div>
      ) : (
        <>
          <div className="hidden overflow-x-auto md:block">
            <table className="w-full text-sm">
              <thead>
                <tr className="table-border text-muted">
                  <th className="py-3 text-left">
                    Date
                  </th>
                  <th className="py-3 text-left">
                    Transaction
                  </th>
                  <th className="py-3 text-left">
                    Category
                  </th>
                  <th className="py-3 text-left">
                    Name
                  </th>
                  <th className="py-3 text-right">
                    Amount
                  </th>
                </tr>
              </thead>

              <tbody>
                {rows.map((item) => (
                  <tr
                    key={item.id}
                    className="table-row table-border"
                  >
                    <td className="py-3">
                      {item.date}
                    </td>
                    <td className="py-3">
                      {item.transaction}
                    </td>
                    <td className="py-3">
                      {item.category}
                    </td>
                    <td className="py-3">
                      {item.name}
                    </td>
                    <td className="py-3 text-right font-semibold text-red-400">
                      {formatPrivateRupiah(item.amount, privacyMode)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div className="grid grid-cols-1 gap-3 md:hidden">
            {rows.map((item) => (
              <div
                key={item.id}
                className="rounded-xl border border-red-500/25 bg-red-500/10 p-4"
              >
                <div className="flex items-start justify-between gap-3">
                  <div className="min-w-0">
                    <p className="break-words font-semibold text-main">
                      {item.transaction}
                    </p>
                    <p className="mt-1 text-sm text-soft">
                      {item.category} - {item.name}
                    </p>
                    <p className="mt-2 text-xs text-muted">
                      {item.date}
                    </p>
                  </div>

                  <p className="shrink-0 text-right text-sm font-bold text-red-400">
                    {formatPrivateRupiah(item.amount, privacyMode)}
                  </p>
                </div>
              </div>
            ))}
          </div>
        </>
      )}
    </div>
  );
});

AnomalyTable.displayName = "AnomalyTable";

export default AnomalyTable;
