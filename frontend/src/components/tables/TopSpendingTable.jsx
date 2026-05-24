const TopSpendingTable = ({ data }) => {
  return (
    <div className="bg-slate-800 p-5 rounded-2xl">
      <h2 className="text-xl font-bold mb-4">
        Top Spending
      </h2>

      <table className="w-full">
        <thead>
          <tr className="text-left border-b border-slate-600">
            <th>Transaksi</th>
            <th>Kategori</th>
            <th>Harga</th>
          </tr>
        </thead>

        <tbody>
          {data.map((item, index) => (
            <tr key={index} className="border-b border-slate-700">
              <td>{item.nama_transaksi}</td>
              <td>{item.kategori}</td>
              <td>
                Rp {item.harga?.toLocaleString("id-ID")}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};

export default TopSpendingTable;