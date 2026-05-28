function TopSpendingTable({ data }) {
  return (
    <div className="panel rounded-lg p-6">
      <h2 className="text-xl font-bold mb-4 text-main">
        Top Spending
      </h2>

      <div className="overflow-auto">
        <table className="w-full">

          <thead>
            <tr className="table-header table-border text-left">
              <th className="px-3 py-3">Transaction</th>
              <th className="px-3 py-3">Category</th>
              <th className="px-3 py-3">Amount</th>
            </tr>
          </thead>

          <tbody>
            {data.map((item, index) => (
              <tr
                key={index}
                className="table-row table-border"
              >
                <td className="px-3 py-3 text-main">
                  {item["Nama Transaksi"]}
                </td>

                <td className="px-3 py-3">
                  {item.Kategori}
                </td>

                <td className="px-3 py-3 font-bold text-accent">
                  Rp {Number(item.Harga).toLocaleString("id-ID")}
                </td>
              </tr>
            ))}
          </tbody>

        </table>
      </div>
    </div>
  );
}

export default TopSpendingTable;
