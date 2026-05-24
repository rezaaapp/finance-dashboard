const AnomalyTable = ({ data }) => {

  return (
    <div className="panel rounded-2xl p-6">

      <h2 className="text-2xl font-bold mb-6 text-red-400">
        Anomaly Detection
      </h2>

      {data.length === 0 ? (

        <div className="text-muted">
          Tidak ada anomaly terdeteksi
        </div>

      ) : (

        <div className="overflow-x-auto">

          <table className="w-full text-sm">

            <thead>
              <tr className="table-border text-muted">

                <th className="text-left py-3">
                  Tanggal
                </th>

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
                  Nominal
                </th>

              </tr>
            </thead>

            <tbody>

              {data.map((item, index) => (

                <tr
                  key={index}
                  className="table-row table-border"
                >

                  <td className="py-3">
                    {
                      new Date(item["Waktu Transaksi"])
                      .toLocaleDateString("id-ID")
                    }
                  </td>

                  <td className="py-3">
                    {item["Nama Transaksi"]}
                  </td>

                  <td className="py-3">
                    {item["Kategori"]}
                  </td>

                  <td className="py-3">
                    {item["Nama"]}
                  </td>

                  <td className="py-3 text-right text-red-400 font-semibold">
                    Rp {Number(item["Harga"])
                      .toLocaleString("id-ID")}
                  </td>

                </tr>

              ))}

            </tbody>

          </table>

        </div>

      )}

    </div>
  );
};

export default AnomalyTable;
