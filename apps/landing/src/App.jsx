import {
  ArrowRight,
  BarChart3,
  BellRing,
  Check,
  DatabaseZap,
  Gauge,
  LineChart,
  LockKeyhole,
  Menu,
  PieChart,
  ShieldCheck,
  Sparkles,
  TrendingUp,
  WalletCards,
  X,
} from "lucide-react";
import { useState } from "react";
import heroAsset from "./assets/hero.png";

const features = [
  {
    icon: Gauge,
    title: "KPI real-time",
    body: "Pantau income, spending, saving rate, dan runway tanpa spreadsheet manual.",
  },
  {
    icon: BellRing,
    title: "Budget alerts",
    body: "Tandai kategori yang melewati batas dan kirim sinyal sebelum cashflow terasa berat.",
  },
  {
    icon: DatabaseZap,
    title: "Data source siap scale",
    body: "Fondasi dashboard dibuat agar mudah disambungkan ke API, bank feed, atau workflow internal.",
  },
  {
    icon: ShieldCheck,
    title: "Privacy-first",
    body: "Kontrol visibilitas angka sensitif untuk demo, review tim, atau presentasi investor.",
  },
];

const plans = [
  {
    name: "Starter",
    price: "Gratis",
    description: "Untuk validasi personal finance dan demo internal.",
    items: ["Dashboard inti", "Import data manual", "Privacy mode"],
  },
  {
    name: "Growth",
    price: "Rp149k",
    description: "Untuk founder dan tim kecil yang butuh kontrol rutin.",
    items: ["Budget alerts", "Multi-source analytics", "Monthly insight"],
    highlighted: true,
  },
  {
    name: "Scale",
    price: "Custom",
    description: "Untuk workflow SaaS dengan integrasi dan governance.",
    items: ["Role-based access", "Custom integration", "Priority support"],
  },
];

function App() {
  const [menuOpen, setMenuOpen] = useState(false);
  const dashboardUrl =
    import.meta.env.VITE_DASHBOARD_URL || "http://127.0.0.1:5173";

  const navItems = [
    ["Fitur", "#features"],
    ["Workflow", "#workflow"],
    ["Harga", "#pricing"],
    ["FAQ", "#faq"],
  ];

  return (
    <main className="min-h-screen bg-[#f7faf8] text-[#13201b]">
      <header className="sticky top-0 z-30 border-b border-[#dfe8e3] bg-[#f7faf8]/90 backdrop-blur">
        <div className="mx-auto flex max-w-7xl items-center justify-between px-5 py-4 lg:px-8">
          <a className="flex items-center gap-3" href="#top" aria-label="Finance Dashboard">
            <span className="grid h-10 w-10 place-items-center rounded-lg bg-[#16352d] text-white">
              <LineChart size={21} aria-hidden="true" />
            </span>
            <span className="text-base font-semibold tracking-normal">Finance Dashboard</span>
          </a>

          <nav className="hidden items-center gap-7 text-sm font-medium text-[#53645c] md:flex">
            {navItems.map(([label, href]) => (
              <a className="transition hover:text-[#16352d]" href={href} key={label}>
                {label}
              </a>
            ))}
          </nav>

          <div className="hidden items-center gap-3 md:flex">
            <a className="text-sm font-semibold text-[#2f4f46]" href={dashboardUrl}>
              Masuk
            </a>
            <a className="inline-flex min-h-11 items-center gap-2 rounded-lg bg-[#16352d] px-5 text-sm font-semibold text-white shadow-sm transition hover:bg-[#0f2923]" href={dashboardUrl}>
              Coba dashboard <ArrowRight size={16} aria-hidden="true" />
            </a>
          </div>

          <button
            className="grid h-10 w-10 place-items-center rounded-lg border border-[#d4ded8] bg-white text-[#16352d] md:hidden"
            onClick={() => setMenuOpen((value) => !value)}
            type="button"
            aria-label={menuOpen ? "Tutup menu" : "Buka menu"}
          >
            {menuOpen ? <X size={20} /> : <Menu size={20} />}
          </button>
        </div>

        {menuOpen && (
          <nav className="border-t border-[#dfe8e3] bg-white px-5 py-4 md:hidden">
            <div className="mx-auto grid max-w-7xl gap-3 text-sm font-semibold text-[#53645c]">
              {navItems.map(([label, href]) => (
                <a className="py-2" href={href} key={label} onClick={() => setMenuOpen(false)}>
                  {label}
                </a>
              ))}
              <a className="mt-2 inline-flex min-h-11 items-center justify-center gap-2 rounded-lg bg-[#16352d] px-5 text-white" href={dashboardUrl}>
                Coba dashboard <ArrowRight size={16} aria-hidden="true" />
              </a>
            </div>
          </nav>
        )}
      </header>

      <section id="top" className="relative overflow-hidden">
        <div className="absolute inset-x-0 top-0 h-52 bg-[#e8f1ee]" aria-hidden="true" />
        <div className="relative mx-auto grid max-w-7xl gap-12 px-5 pb-14 pt-16 lg:grid-cols-[0.95fr_1.05fr] lg:px-8 lg:pb-20 lg:pt-24">
          <div className="flex flex-col justify-center">
            <div className="mb-6 inline-flex w-fit items-center gap-2 rounded-full border border-[#b8d8ce] bg-white px-3 py-2 text-sm font-semibold text-[#25624f]">
              <Sparkles size={16} aria-hidden="true" />
              Built for SaaS finance operations
            </div>
            <h1 className="max-w-3xl text-5xl font-semibold leading-[1.02] tracking-normal text-[#10231d] sm:text-6xl lg:text-7xl">
              Finance Dashboard
            </h1>
            <p className="mt-6 max-w-2xl text-lg leading-8 text-[#53645c]">
              Landing page dan dashboard SaaS untuk membaca kesehatan finansial,
              menemukan anomali pengeluaran, dan menjaga keputusan tim tetap berbasis data.
            </p>
            <div className="mt-8 flex flex-col gap-3 sm:flex-row">
              <a className="inline-flex min-h-12 items-center justify-center gap-2 rounded-lg bg-[#16352d] px-6 font-semibold text-white shadow-sm transition hover:bg-[#0f2923]" href={dashboardUrl}>
                Mulai eksplorasi <ArrowRight size={18} aria-hidden="true" />
              </a>
              <a className="inline-flex min-h-12 items-center justify-center rounded-lg border border-[#bfd0c8] bg-white px-6 font-semibold text-[#183a31] transition hover:border-[#183a31]" href="#pricing">
                Lihat pricing
              </a>
            </div>
            <div className="mt-8 grid max-w-xl grid-cols-3 gap-3 text-sm">
              <Metric label="Spending tracked" value="98%" />
              <Metric label="Review time saved" value="12h" />
              <Metric label="Alert coverage" value="24/7" />
            </div>
          </div>

          <div className="relative min-h-[480px]">
            <img
              className="absolute right-0 top-0 h-36 w-36 object-contain opacity-80 sm:h-44 sm:w-44"
              src={heroAsset}
              alt=""
              aria-hidden="true"
            />
            <DashboardPreview />
          </div>
        </div>
      </section>

      <section id="features" className="border-y border-[#dfe8e3] bg-white py-16">
        <div className="mx-auto max-w-7xl px-5 lg:px-8">
          <div className="max-w-2xl">
            <p className="text-sm font-semibold uppercase tracking-[0.14em] text-[#2f7c66]">Fitur inti</p>
            <h2 className="mt-3 text-3xl font-semibold tracking-normal sm:text-4xl">
              Dibuat untuk berubah dari personal dashboard menjadi SaaS yang rapi.
            </h2>
          </div>
          <div className="mt-10 grid gap-4 md:grid-cols-2 lg:grid-cols-4">
            {features.map(({ icon: Icon, title, body }) => (
              <article className="rounded-lg border border-[#dfe8e3] bg-[#fbfdfc] p-5" key={title}>
                <span className="grid h-11 w-11 place-items-center rounded-lg bg-[#e6f3ee] text-[#1f6b57]">
                  <Icon size={21} aria-hidden="true" />
                </span>
                <h3 className="mt-5 text-lg font-semibold">{title}</h3>
                <p className="mt-3 text-sm leading-6 text-[#5d6d66]">{body}</p>
              </article>
            ))}
          </div>
        </div>
      </section>

      <section id="workflow" className="bg-[#f7faf8] py-16">
        <div className="mx-auto grid max-w-7xl gap-10 px-5 lg:grid-cols-[0.9fr_1.1fr] lg:px-8">
          <div>
            <p className="text-sm font-semibold uppercase tracking-[0.14em] text-[#a45b22]">Workflow</p>
            <h2 className="mt-3 text-3xl font-semibold tracking-normal sm:text-4xl">
              Dari data mentah ke keputusan mingguan.
            </h2>
            <p className="mt-5 text-base leading-7 text-[#5d6d66]">
              Landing page ini sengaja dipisah dari dashboard agar SEO, campaign,
              analytics, dan eksperimen pricing bisa berkembang tanpa mengganggu app utama.
            </p>
          </div>
          <div className="grid gap-4 sm:grid-cols-3">
            {["Connect", "Analyze", "Act"].map((step, index) => (
              <div className="rounded-lg border border-[#dfe8e3] bg-white p-5" key={step}>
                <span className="text-sm font-semibold text-[#2f7c66]">0{index + 1}</span>
                <h3 className="mt-4 text-xl font-semibold">{step}</h3>
                <p className="mt-3 text-sm leading-6 text-[#5d6d66]">
                  {index === 0 && "Satukan data transaksi, kategori, dan budget dalam satu alur."}
                  {index === 1 && "Baca tren, sumber pengeluaran, dan kategori yang butuh perhatian."}
                  {index === 2 && "Ambil tindakan dari alert, insight, dan review performa bulanan."}
                </p>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section id="pricing" className="bg-[#10231d] py-16 text-white">
        <div className="mx-auto max-w-7xl px-5 lg:px-8">
          <div className="flex flex-col justify-between gap-5 md:flex-row md:items-end">
            <div className="max-w-2xl">
              <p className="text-sm font-semibold uppercase tracking-[0.14em] text-[#82d5be]">Pricing</p>
              <h2 className="mt-3 text-3xl font-semibold tracking-normal sm:text-4xl">
                Mulai kecil, tetap siap naik kelas.
              </h2>
            </div>
            <p className="max-w-md text-sm leading-6 text-[#b6cbc3]">
              Struktur ini cocok untuk SaaS awal: validasi gratis, paid plan sederhana,
              lalu enterprise/custom saat kebutuhan integrasi muncul.
            </p>
          </div>

          <div className="mt-10 grid gap-4 lg:grid-cols-3">
            {plans.map((plan) => (
              <article
                className={`rounded-lg border p-6 ${
                  plan.highlighted
                    ? "border-[#82d5be] bg-[#173b32]"
                    : "border-[#29483f] bg-[#132b25]"
                }`}
                key={plan.name}
              >
                <div className="flex items-center justify-between gap-3">
                  <h3 className="text-xl font-semibold">{plan.name}</h3>
                  {plan.highlighted && (
                    <span className="rounded-full bg-[#f2b84b] px-3 py-1 text-xs font-bold text-[#2d1d04]">
                      Recommended
                    </span>
                  )}
                </div>
                <p className="mt-5 text-4xl font-semibold">{plan.price}</p>
                <p className="mt-3 min-h-12 text-sm leading-6 text-[#b6cbc3]">{plan.description}</p>
                <ul className="mt-6 grid gap-3 text-sm text-[#dbe9e4]">
                  {plan.items.map((item) => (
                    <li className="flex items-center gap-3" key={item}>
                      <Check className="text-[#82d5be]" size={17} aria-hidden="true" />
                      {item}
                    </li>
                  ))}
                </ul>
              </article>
            ))}
          </div>
        </div>
      </section>

      <section id="faq" className="bg-white py-16">
        <div className="mx-auto grid max-w-7xl gap-8 px-5 lg:grid-cols-[0.85fr_1.15fr] lg:px-8">
          <div>
            <p className="text-sm font-semibold uppercase tracking-[0.14em] text-[#2f7c66]">FAQ</p>
            <h2 className="mt-3 text-3xl font-semibold tracking-normal sm:text-4xl">
              Pertanyaan sebelum SaaS-nya tumbuh.
            </h2>
          </div>
          <div className="grid gap-4">
            <Faq title="Kenapa landing page dipisah dari dashboard?">
              Karena landing butuh SEO, campaign, copywriting, dan eksperimen pricing;
              dashboard butuh auth, data, dan workflow pengguna. Dipisah sebagai app
              membuat keduanya bisa deploy dan berkembang mandiri.
            </Faq>
            <Faq title="Apakah masih bisa share komponen nanti?">
              Bisa. Saat kebutuhan makin besar, komponen brand seperti button,
              typography, dan card bisa dipindah ke `packages/ui`.
            </Faq>
            <Faq title="Domain idealnya bagaimana?">
              Landing page cocok di `domain.com` atau `www.domain.com`, sedangkan
              dashboard SaaS cocok di `app.domain.com`.
            </Faq>
          </div>
        </div>
      </section>

      <footer className="border-t border-[#dfe8e3] bg-[#f7faf8] px-5 py-8">
        <div className="mx-auto flex max-w-7xl flex-col gap-4 text-sm text-[#5d6d66] sm:flex-row sm:items-center sm:justify-between">
          <span className="font-semibold text-[#16352d]">Finance Dashboard</span>
          <span>Built as `apps/landing` for SaaS-ready maintenance.</span>
        </div>
      </footer>
    </main>
  );
}

function Metric({ label, value }) {
  return (
    <div className="rounded-lg border border-[#dfe8e3] bg-white p-4">
      <div className="text-2xl font-semibold text-[#16352d]">{value}</div>
      <div className="mt-1 leading-5 text-[#64746d]">{label}</div>
    </div>
  );
}

function DashboardPreview() {
  const bars = [58, 82, 45, 70, 62, 88, 76, 94];

  return (
    <div className="absolute bottom-0 left-0 right-0 rounded-lg border border-[#c9d8d1] bg-white p-4 shadow-2xl shadow-[#24443a]/15 sm:p-5 lg:left-8">
      <div className="flex items-center justify-between border-b border-[#e5eee9] pb-4">
        <div>
          <p className="text-sm font-semibold text-[#2f7c66]">Monthly overview</p>
          <h2 className="mt-1 text-xl font-semibold">Cashflow command center</h2>
        </div>
        <span className="grid h-10 w-10 place-items-center rounded-lg bg-[#e6f3ee] text-[#1f6b57]">
          <WalletCards size={20} aria-hidden="true" />
        </span>
      </div>

      <div className="mt-5 grid gap-4 md:grid-cols-[1fr_0.8fr]">
        <div className="rounded-lg bg-[#f3f8f5] p-4">
          <div className="mb-4 flex items-center justify-between">
            <div>
              <p className="text-sm text-[#64746d]">Net savings</p>
              <p className="mt-1 text-3xl font-semibold text-[#173b32]">Rp18.4M</p>
            </div>
            <span className="inline-flex items-center gap-1 rounded-full bg-[#dff3eb] px-3 py-1 text-sm font-semibold text-[#1f6b57]">
              <TrendingUp size={15} aria-hidden="true" />
              14.8%
            </span>
          </div>
          <div className="flex h-44 items-end gap-2">
            {bars.map((height, index) => (
              <span
                className={`w-full rounded-t-md ${
                  index % 3 === 0 ? "bg-[#f2b84b]" : index % 2 === 0 ? "bg-[#43a582]" : "bg-[#1f6b57]"
                }`}
                style={{ height: `${height}%` }}
                key={height + index}
              />
            ))}
          </div>
        </div>

        <div className="grid gap-4">
          <MiniCard icon={PieChart} label="Top category" value="Operations" detail="32% of spend" />
          <MiniCard icon={BarChart3} label="Budget status" value="On track" detail="5 alerts cleared" />
          <MiniCard icon={LockKeyhole} label="Privacy mode" value="Active" detail="Sensitive values hidden" />
        </div>
      </div>
    </div>
  );
}

function MiniCard({ icon: Icon, label, value, detail }) {
  return (
    <div className="rounded-lg border border-[#e1ebe6] bg-white p-4">
      <div className="flex items-center gap-3">
        <span className="grid h-9 w-9 place-items-center rounded-lg bg-[#eef5f2] text-[#2f7c66]">
          <Icon size={18} aria-hidden="true" />
        </span>
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.12em] text-[#7c8b84]">{label}</p>
          <p className="mt-1 font-semibold text-[#173b32]">{value}</p>
        </div>
      </div>
      <p className="mt-3 text-sm text-[#64746d]">{detail}</p>
    </div>
  );
}

function Faq({ title, children }) {
  return (
    <article className="rounded-lg border border-[#dfe8e3] bg-[#fbfdfc] p-5">
      <h3 className="font-semibold text-[#173b32]">{title}</h3>
      <p className="mt-3 text-sm leading-6 text-[#5d6d66]">{children}</p>
    </article>
  );
}

export default App;
