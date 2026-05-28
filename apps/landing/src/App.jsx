import {
  ArrowRight,
  BellRing,
  Bot,
  ChartNoAxesColumnIncreasing,
  CheckCircle2,
  Columns3,
  HeartHandshake,
  LayoutDashboard,
  Menu,
  Sheet,
  Sparkles,
  TrendingUp,
  UsersRound,
  X,
} from "lucide-react";
import { useState } from "react";

const colors = {
  sage: "#4A5D4E",
  navy: "#002B45",
  offWhite: "#F8F9FA",
  coral: "#dd8484",
};

const rows = [
  {
    date: "12 Mei",
    description: "Beli token listrik rumah",
    category: "Utilities",
    amount: "Rp150k",
  },
  {
    date: "13 Mei",
    description: "Belanja bulanan bersama",
    category: "Groceries",
    amount: "Rp780k",
  },
  {
    date: "14 Mei",
    description: "Dinner setelah kerja",
    category: "Dining Out",
    amount: "Rp320k",
    critical: true,
  },
  {
    date: "15 Mei",
    description: "Transport kantor",
    category: "Operational Costs",
    amount: "Rp95k",
  },
];

const budgetBars = [
  { label: "Groceries", value: 64, amount: "Rp1.28M" },
  { label: "Utilities", value: 42, amount: "Rp420k" },
  { label: "Dining Out", value: 91, amount: "Rp910k", critical: true },
  { label: "Transport", value: 58, amount: "Rp580k" },
];

const dashboardMetrics = [
  {
    label: "Total Expenses",
    value: "Rp 8.450.000",
    trend: "+12.4%",
    status: "bad",
  },
  {
    label: "Total Saving",
    value: "Rp 3.250.000",
    trend: "+18.7%",
    status: "good",
  },
  {
    label: "Total Income",
    value: "Rp 14.800.000",
    trend: "+6.2%",
    status: "good",
  },
];

const monthlySeries = [52, 66, 44, 74, 58, 82];

const topSpending = [
  ["Dining Out", "Rp 910.000"],
  ["Groceries", "Rp 780.000"],
  ["Utilities", "Rp 420.000"],
];

const features = [
  {
    icon: Sheet,
    title: "Familiar Input Interface",
    body: "Ketik pengeluaran harian secara natural seperti di Excel atau Google Sheets. Tidak ada kurva belajar, tidak perlu rumus akuntansi rumit, dan tetap fleksibel untuk kebiasaan mencatat yang sudah Anda punya.",
  },
  {
    icon: BellRing,
    title: "Predictive Runway & Alerts",
    body: "Setiap baris spreadsheet langsung berubah menjadi analytics hidup. Sistem membaca tren, memprediksi kapan uang berisiko habis sebelum akhir bulan, lalu memberi alert agar keputusan belanja bisa dikoreksi lebih awal.",
  },
  {
    icon: UsersRound,
    title: "Couples Shared Transparency",
    body: "Dirancang untuk pasangan muda. Satu workspace bersama memungkinkan dua partner mencatat pengeluaran secara transparan tanpa harus berbagi satu Google Account atau saling menunggu update manual.",
  },
];

function App() {
  const [menuOpen, setMenuOpen] = useState(false);
  const dashboardUrl =
    import.meta.env.VITE_DASHBOARD_URL || "http://127.0.0.1:5173";

  const navItems = [
    ["Fitur", "#features"],
    ["Cerita", "#testimonial"],
    ["Demo", dashboardUrl],
  ];

  return (
    <main className="min-h-screen bg-[#F8F9FA] text-[#002B45]">
      <header className="sticky top-0 z-30 border-b border-[#dfe6dd] bg-[#F8F9FA]/92 backdrop-blur">
        <div className="mx-auto flex max-w-7xl items-center justify-between px-5 py-4 lg:px-8">
          <a className="flex items-center gap-3" href="#top" aria-label="Finance Dashboard">
            <span className="grid h-10 w-10 place-items-center rounded-lg bg-[#4A5D4E] text-white">
              <Columns3 size={21} aria-hidden="true" />
            </span>
            <span className="text-base font-semibold tracking-normal">Finance Dashboard</span>
          </a>

          <nav className="hidden items-center gap-7 text-sm font-semibold text-[#52645d] md:flex">
            {navItems.map(([label, href]) => (
              <a className="transition hover:text-[#002B45]" href={href} key={label}>
                {label}
              </a>
            ))}
          </nav>

          <a
            className="hidden min-h-11 items-center gap-2 rounded-lg bg-[#002B45] px-5 text-sm font-semibold text-white shadow-sm transition hover:bg-[#0b3b5a] md:inline-flex"
            href={dashboardUrl}
          >
            Mulai Demo Gratis <ArrowRight size={16} aria-hidden="true" />
          </a>

          <button
            className="grid h-10 w-10 place-items-center rounded-lg border border-[#d7e0d9] bg-white text-[#002B45] md:hidden"
            onClick={() => setMenuOpen((value) => !value)}
            type="button"
            aria-label={menuOpen ? "Tutup menu" : "Buka menu"}
          >
            {menuOpen ? <X size={20} /> : <Menu size={20} />}
          </button>
        </div>

        {menuOpen && (
          <nav className="border-t border-[#dfe6dd] bg-white px-5 py-4 md:hidden">
            <div className="mx-auto grid max-w-7xl gap-3 text-sm font-semibold text-[#52645d]">
              {navItems.map(([label, href]) => (
                <a className="py-2" href={href} key={label} onClick={() => setMenuOpen(false)}>
                  {label}
                </a>
              ))}
              <a
                className="mt-2 inline-flex min-h-11 items-center justify-center gap-2 rounded-lg bg-[#002B45] px-5 text-white"
                href={dashboardUrl}
              >
                Mulai Demo Gratis <ArrowRight size={16} aria-hidden="true" />
              </a>
            </div>
          </nav>
        )}
      </header>

      <section id="top" className="bg-[#F8F9FA]">
        <div className="mx-auto grid min-h-[calc(100vh-73px)] max-w-7xl items-center gap-10 px-5 py-12 lg:grid-cols-2 lg:gap-14 lg:px-8 lg:py-16">
          <div className="flex flex-col justify-center">
            <div className="mb-6 inline-flex w-fit items-center gap-2 rounded-full border border-[#cbd9cf] bg-white px-3 py-2 text-sm font-semibold text-[#4A5D4E]">
              <Sparkles size={16} aria-hidden="true" />
              Dari catatan familiar ke keputusan harian
            </div>

            <h1 className="max-w-2xl text-4xl font-semibold leading-[1.07] tracking-normal text-[#002B45] sm:text-5xl lg:text-6xl">
              Input Se-familiar Spreadsheet. Putuskan Langkah Keuangan Lebih Tepat.
            </h1>

            <p className="mt-6 max-w-2xl text-base leading-8 text-[#52645d] sm:text-lg">
              Mulai langkah finansial pertama Anda sebagai pasangan muda ataupun individu secara ringan. Cukup masukkan data harian Anda dengan format spreadsheet yang fleksibel, dan biarkan dasbor cerdas kami menyajikan visualisasi kaya akan insight untuk keputusan harian yang percaya diri.
            </p>

            <div className="mt-8 flex flex-col gap-3 sm:flex-row">
              <a
                className="inline-flex min-h-12 items-center justify-center gap-2 rounded-lg bg-[#002B45] px-6 font-semibold text-white shadow-sm transition hover:bg-[#0b3b5a]"
                href={dashboardUrl}
              >
                Mulai Ambil Kendali Keuangan <ArrowRight size={18} aria-hidden="true" />
              </a>
            </div>

            <div className="mt-8 grid max-w-xl grid-cols-1 gap-3 sm:grid-cols-3">
              <TrustMetric value="0" label="rumus rumit" />
              <TrustMetric value="2 orang" label="satu workspace" />
              <TrustMetric value="Live" label="budget alert" />
            </div>
          </div>

          <FeatureMockup />
        </div>
      </section>

      <section id="features" className="border-y border-[#dfe6dd] bg-white py-16 lg:py-20">
        <div className="mx-auto max-w-7xl px-5 lg:px-8">
          <div className="mx-auto max-w-3xl text-center">
            <p className="text-sm font-semibold uppercase tracking-[0.14em] text-[#4A5D4E]">
              Spreadsheet + Automation
            </p>
            <h2 className="mt-3 text-3xl font-semibold tracking-normal text-[#002B45] sm:text-4xl">
              Tetap mudah seperti spreadsheet, tapi hasilnya mendorong keputusan.
            </h2>
          </div>

          <div className="mt-10 grid gap-4 lg:grid-cols-3">
            {features.map(({ icon: Icon, title, body }) => (
              <article className="rounded-lg border border-[#dfe6dd] bg-[#F8F9FA] p-6" key={title}>
                <span className="grid h-12 w-12 place-items-center rounded-lg bg-[#e7efe9] text-[#4A5D4E]">
                  <Icon size={23} aria-hidden="true" />
                </span>
                <h3 className="mt-6 text-xl font-semibold text-[#002B45]">{title}</h3>
                <p className="mt-4 text-sm leading-7 text-[#52645d]">{body}</p>
              </article>
            ))}
          </div>
        </div>
      </section>

      <section id="testimonial" className="bg-[#F8F9FA] py-16 lg:py-20">
        <div className="mx-auto max-w-5xl px-5 lg:px-8">
          <blockquote className="rounded-lg border border-l-8 border-[#b9cebf] border-l-[#4A5D4E] bg-[#f0f6f1] p-7 shadow-sm sm:p-10">
            <HeartHandshake className="mb-6 text-[#4A5D4E]" size={34} aria-hidden="true" />
            <p className="text-xl font-medium leading-9 text-[#002B45] sm:text-2xl sm:leading-10">
              "Dulu kami pakai spreadsheet cuma buat jadi 'tukang catat' pasif yang tahu uang habis ke mana tanpa solusi. Pas pakai produk ini, inputnya se-simpel spreadsheet lama kami, tapi visualisasi tren dan alert keputusannya nyata banget. Sekarang kalau mau beli barang hobi atau mutusin anggaran liburan, tinggal lihat alert dasbor. Diskusi keuangan sama suami jadi sehat dan tenang."
            </p>
            <footer className="mt-6 text-base font-semibold text-[#52645d]">
              - Risa & Fadel, Pasangan Muda.
            </footer>
          </blockquote>
        </div>
      </section>

      <section className="bg-[#002B45] py-16 text-white lg:py-20">
        <div className="mx-auto max-w-4xl px-5 text-center lg:px-8">
          <h2 className="text-3xl font-semibold tracking-normal sm:text-4xl">
            Siap Melihat ke Mana Jalur Keuangan Anda Membawa Keputusan Hari Ini?
          </h2>
          <p className="mx-auto mt-5 max-w-2xl text-base leading-8 text-[#d9e3dc]">
            Bergabunglah dengan ribuan pasangan muda dan individu yang cerdas mengelola masa depan finansialnya.
          </p>
          <a
            className="mt-8 inline-flex min-h-12 items-center justify-center gap-2 rounded-lg bg-[#4A5D4E] px-7 font-semibold text-white shadow-sm transition hover:bg-[#5f7564]"
            href={dashboardUrl}
          >
            Mulai Demo Gratis <ArrowRight size={18} aria-hidden="true" />
          </a>
        </div>
      </section>
    </main>
  );
}

function TrustMetric({ value, label }) {
  return (
    <div className="rounded-lg border border-[#dfe6dd] bg-white p-4">
      <div className="text-2xl font-semibold text-[#002B45]">{value}</div>
      <div className="mt-1 text-sm leading-5 text-[#66756e]">{label}</div>
    </div>
  );
}

function FeatureMockup() {
  return (
    <div className="relative flex min-h-[560px] items-center lg:min-h-[650px]">
      <div className="w-full overflow-hidden rounded-[1.75rem] border border-[#cfded3] bg-[#002B45] p-3 shadow-2xl shadow-[#002B45]/18">
        <div className="grid min-h-[560px] overflow-hidden rounded-[1.2rem] bg-[#F8F9FA] text-[#1A1A1A] lg:grid-cols-[92px_1fr]">
          <aside className="hidden bg-[#002B45] p-4 text-white lg:block">
            <div className="grid h-10 w-10 place-items-center rounded-lg bg-[#4A5D4E]">
              <Columns3 size={20} aria-hidden="true" />
            </div>
            <nav className="mt-8 grid gap-3">
              <MiniNav active icon={LayoutDashboard} />
              <MiniNav icon={ChartNoAxesColumnIncreasing} />
              <MiniNav icon={BellRing} />
              <MiniNav icon={Sheet} />
            </nav>
          </aside>

          <div className="min-w-0 p-4 sm:p-5">
            <div className="mb-4 flex items-center justify-between gap-3 border-b border-[#e5e7eb] pb-4">
              <div className="min-w-0">
                <p className="text-xs font-semibold uppercase tracking-[0.12em] text-[#4A5D4E]">
                  Dummy dashboard preview
                </p>
                <h2 className="mt-1 truncate text-lg font-semibold text-[#002B45]">
                  Mei household workspace
                </h2>
              </div>
              <span className="inline-flex shrink-0 items-center gap-2 rounded-lg border border-[#d7ded9] bg-white px-3 py-2 text-xs font-semibold text-[#4A5D4E]">
                <UsersRound size={14} aria-hidden="true" />
                Risa + Fadel
              </span>
            </div>

            <div className="grid gap-3 sm:grid-cols-3">
              {dashboardMetrics.map((metric) => (
                <MetricPreview metric={metric} key={metric.label} />
              ))}
            </div>

            <div className="mt-4 grid gap-4 xl:grid-cols-[1.05fr_0.95fr]">
              <section className="rounded-lg border border-[#e5e7eb] bg-white p-4">
                <div className="mb-4 flex items-center justify-between gap-3">
                  <div>
                    <p className="text-xs font-semibold uppercase tracking-[0.12em] text-[#4A5D4E]">
                      Monthly Spending
                    </p>
                    <h3 className="mt-1 text-base font-semibold text-[#002B45]">
                      Dummy cashflow trend
                    </h3>
                  </div>
                  <span className="rounded-lg bg-[#eef3ef] px-2.5 py-1 text-xs font-bold text-[#4A5D4E]">
                    Live
                  </span>
                </div>
                <MiniChart />
              </section>

              <section className="rounded-lg border border-[#e5e7eb] bg-white p-4">
                <p className="text-xs font-semibold uppercase tracking-[0.12em] text-[#4A5D4E]">
                  Top Spending
                </p>
                <div className="mt-3 grid gap-2">
                  {topSpending.map(([label, amount], index) => (
                    <div
                      className="grid grid-cols-[1fr_auto] items-center gap-3 rounded-lg border border-[#edf0ee] px-3 py-2 text-sm"
                      key={label}
                    >
                      <span className="font-semibold text-[#1A1A1A]">
                        {index + 1}. {label}
                      </span>
                      <span className="font-bold text-[#002B45]">{amount}</span>
                    </div>
                  ))}
                </div>
              </section>
            </div>

            <div className="mt-4 grid gap-4 xl:grid-cols-[1fr_1fr]">
              <SpreadsheetTable />
              <BudgetTracker />
            </div>

            <div className="mt-4 rounded-lg border border-[#dbe3de] bg-white p-4">
              <div className="flex gap-3">
                <span className="grid h-9 w-9 shrink-0 place-items-center rounded-lg bg-[#eef3ef] text-[#4A5D4E]">
                  <Bot size={18} aria-hidden="true" />
                </span>
                <p className="text-sm leading-6 text-[#52645d]">
                  <strong className="text-[#002B45]">AI Financial Insight:</strong>{" "}
                  Dining Out naik dari pola normal. Pertahankan saving ratio dengan masak di rumah malam ini.
                </p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

function MiniNav({ icon: Icon, active = false }) {
  return (
    <span
      className={`grid h-11 w-full place-items-center rounded-lg border ${
        active
          ? "border-white/10 bg-[#4A5D4E]/45 text-white"
          : "border-transparent text-white/70"
      }`}
    >
      <Icon size={18} aria-hidden="true" />
    </span>
  );
}

function MetricPreview({ metric }) {
  const isGood = metric.status === "good";

  return (
    <article className="rounded-lg border border-[#e5e7eb] bg-white p-3">
      <p className="text-xs font-semibold text-[#6b7280]">{metric.label}</p>
      <p className="mt-2 whitespace-nowrap text-[clamp(0.95rem,2.4vw,1.15rem)] font-bold tabular-nums text-[#1A1A1A]">
        {metric.value}
      </p>
      <p
        className={`mt-2 inline-flex items-center gap-1 text-xs font-bold ${
          isGood ? "text-[#4A5D4E]" : "text-[#D9534F]"
        }`}
      >
        <TrendingUp size={13} aria-hidden="true" />
        {metric.trend} vs last month
      </p>
    </article>
  );
}

function MiniChart() {
  return (
    <div className="flex h-36 items-end gap-2 border-b border-l border-[#e5e7eb] px-2 pb-2">
      {monthlySeries.map((value, index) => (
        <div className="flex flex-1 items-end" key={`${value}-${index}`}>
          <div
            className="w-full rounded-t"
            style={{
              height: `${value}%`,
              backgroundColor: index % 2 === 0 ? colors.navy : colors.sage,
            }}
          />
        </div>
      ))}
    </div>
  );
}

function SpreadsheetTable() {
  return (
    <section className="min-w-0 overflow-hidden rounded-lg border border-[#dfe6dd] bg-white">
      <div className="overflow-x-auto">
        <div className="min-w-[520px]">
          <div className="grid grid-cols-[0.85fr_2fr_1.2fr_1fr] bg-[#f1f6f2] text-xs font-bold uppercase tracking-[0.08em] text-[#60756a]">
            <div className="border-r border-[#dfe6dd] px-3 py-3">Date</div>
            <div className="border-r border-[#dfe6dd] px-3 py-3">Description</div>
            <div className="border-r border-[#dfe6dd] px-3 py-3">Category</div>
            <div className="px-3 py-3 text-right">Amount</div>
          </div>

          {rows.map((row) => (
            <div
              className={`grid grid-cols-[0.85fr_2fr_1.2fr_1fr] border-t border-[#edf2ee] text-sm ${
                row.critical ? "bg-[#fff7f7]" : "bg-white"
              }`}
              key={`${row.date}-${row.description}`}
            >
              <Cell>{row.date}</Cell>
              <Cell>{row.description}</Cell>
              <Cell>
                <span
                  className={`rounded-full px-2 py-1 text-xs font-semibold ${
                    row.critical
                      ? "bg-[#f8dddd] text-[#9c4848]"
                      : "bg-[#edf4ef] text-[#557865]"
                  }`}
                >
                  {row.category}
                </span>
              </Cell>
              <Cell align="right">{row.amount}</Cell>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

function Cell({ children, align = "left" }) {
  return (
    <div
      className={`border-r border-[#edf2ee] px-3 py-3 last:border-r-0 ${
        align === "right" ? "text-right font-semibold text-[#002B45]" : "text-[#41524a]"
      }`}
    >
      {children}
    </div>
  );
}

function BudgetTracker() {
  return (
    <section className="rounded-lg border border-[#dfe6dd] bg-white p-4">
      <div className="flex flex-col justify-between gap-3 sm:flex-row sm:items-center">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.12em] text-[#4A5D4E]">
            Automated from sheet rows
          </p>
          <h3 className="mt-1 text-lg font-semibold text-[#002B45]">
            Budget Limit Tracker
          </h3>
        </div>
        <span className="inline-flex w-fit items-center gap-2 rounded-lg bg-[#eef5f0] px-3 py-2 text-xs font-semibold text-[#557865]">
          <TrendingUp size={14} aria-hidden="true" />
          Live sync
        </span>
      </div>

      <div className="mt-5 grid gap-4">
        {budgetBars.map((bar) => (
          <div key={bar.label}>
            <div className="mb-2 flex items-center justify-between gap-3 text-sm">
              <span className="font-semibold text-[#26382f]">{bar.label}</span>
              <span className={bar.critical ? "font-bold text-[#9c4848]" : "text-[#66756e]"}>
                {bar.amount}
              </span>
            </div>
            <div className="h-3 overflow-hidden rounded-full bg-[#edf2ee]">
              <div
                className="h-full rounded-full"
                style={{
                  width: `${bar.value}%`,
                  backgroundColor: bar.critical ? colors.coral : colors.sage,
                }}
              />
            </div>
          </div>
        ))}
      </div>

      <div className="mt-5 rounded-lg border border-[#dd8484] bg-[#fff0f0] px-4 py-3 text-sm font-bold leading-6 text-[#8d3c3c]">
        ⚠️ Decision Alert: Anggaran 'Dining Out' hampir habis. Keputusan malam ini: Masak di rumah!
      </div>

      <div className="mt-4 flex items-center gap-2 text-sm font-semibold text-[#52645d]">
        <CheckCircle2 size={17} className="text-[#4A5D4E]" aria-hidden="true" />
        Data pasif berubah menjadi keputusan yang bisa langsung dibicarakan.
      </div>
    </section>
  );
}

export default App;
