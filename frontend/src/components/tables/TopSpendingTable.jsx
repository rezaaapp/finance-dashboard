const formatRupiah = (value) => {
  return new Intl.NumberFormat("id-ID", {
    style: "currency",
    currency: "IDR",
    maximumFractionDigits: 0,
  }).format(value || 0);
};

const TopSpendingTable = ({ data = [] }) => {
  return (
    <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5">

      <h2 className="text-xl font-bold mb-6 text-white">
        Top Spending
      </h2>

      <div className="overflow-x-auto">

        <table className="w-full text-sm">

          <thead>
            <tr className="border-b border-slate-800 text-slate-400">

              <th className="text-left py-3">
                Transaksi
              </th>

              <th className="text-left py-3">
                Kategori
              </th>

              <th className="text-left py-3">
                Nama
              </th>

              <th className="text-right py-3">
                Harga
              </th>

            </tr>
          </thead>

          <tbody>

            {data.map((item, index) => (

              <tr
                key={index}
                className="border-b border-slate-800 hover:bg-slate-800/40 transition"
              >

                <td className="py-4 text-white">
                  {item.nama_transaksi}
                </td>

                <td className="py-4 text-slate-300">
                  {item.kategori}
                </td>

                <td className="py-4 text-slate-300">
                  {item.nama}
                </td>

                <td className="py-4 text-right font-semibold text-cyan-400">
                  {formatRupiah(item.harga)}
                </td>

              </tr>

            ))}

          </tbody>

        </table>

      </div>

    </div>
  );
};

export default TopSpendingTable;