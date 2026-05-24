function TopSpendingTable({ data }) {
  return (
    <div className="bg-slate-800 p-6 rounded-2xl">
      <h2 className="text-xl font-bold mb-4">
        Top Spending
      </h2>

      <div className="overflow-auto">
        <table className="w-full">

          <thead>
            <tr className="text-left border-b border-slate-700">
              <th className="pb-3">Transaksi</th>
              <th className="pb-3">Kategori</th>
              <th className="pb-3">Harga</th>
            </tr>
          </thead>

          <tbody>
            {data.map((item, index) => (
              <tr
                key={index}
                className="border-b border-slate-700"
              >
                <td className="py-3">
                  {item["Nama Transaksi"]}
                </td>

                <td className="py-3">
                  {item.Kategori}
                </td>

                <td className="py-3 font-bold">
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