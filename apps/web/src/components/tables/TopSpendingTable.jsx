import { formatPrivateRupiah } from "../../utils/privacy";

const TopSpendingTable = ({ data = [], privacyMode }) => {
  return (
    <div className="panel rounded-lg p-4 sm:p-5">

      <h2 className="text-xl font-bold mb-6 text-main">
        Top Spending
      </h2>

      <div className="hidden overflow-x-auto md:block">

        <table className="w-full text-sm">

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

              <th className="px-3 py-3 text-right">
                Amount
              </th>

            </tr>
          </thead>

          <tbody>

            {data.map((item, index) => (

              <tr
                key={index}
                className="table-row table-border transition"
              >

                <td className="px-3 py-4 text-main">
                  {item.nama_transaksi}
                </td>

                <td className="px-3 py-4 text-soft">
                  {item.kategori}
                </td>

                <td className="px-3 py-4 text-soft">
                  {item.nama}
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
            key={index}
            className="rounded-lg border border-[var(--color-border)] bg-[var(--color-panel-hover)] p-4"
          >
            <div className="flex items-start justify-between gap-3">
              <div className="min-w-0">
                <p className="break-words font-semibold text-main">
                  {item.nama_transaksi}
                </p>
                <p className="mt-1 text-sm text-soft">
                  {item.kategori} • {item.nama}
                </p>
              </div>

              <p className="shrink-0 text-right text-sm font-bold text-accent">
                {formatPrivateRupiah(item.harga, privacyMode)}
              </p>
            </div>
          </div>
        ))}
      </div>

    </div>
  );
};

export default TopSpendingTable;
