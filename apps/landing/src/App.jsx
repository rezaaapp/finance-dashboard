import {
  ArrowRight,
  ArrowUp,
  BarChart3,
  CalendarClock,
  Check,
  ChevronDown,
  ChevronLeft,
  ChevronRight,
  CircleDollarSign,
  Eye,
  FileSpreadsheet,
  Grid3X3,
  HeartHandshake,
  Home,
  LayoutDashboard,
  LineChart,
  LockKeyhole,
  Mail,
  Menu,
  MessageCircle,
  PieChart,
  PiggyBank,
  RefreshCw,
  Smile,
  Sparkles,
  Target,
  TrendingUp,
  TriangleAlert,
  WalletCards,
  X,
} from "lucide-react";
import { useEffect, useRef, useState } from "react";
import omonLogo from "./assets/omon-icon.png";

const contactLinks = {
  email: "omon.dashboard@gmail.com",
  mailto: "mailto:omon.dashboard@gmail.com",
  whatsapp: "087822424274",
  whatsappUrl: "https://wa.me/6287822424274",
};

const navItems = [
  ["Fitur", "#features"],
  ["Cara Kerja", "#how-it-works"],
  ["Keamanan", "#trust"],
  ["FAQ", "#faq"],
];

const problems = [
  {
    icon: PiggyBank,
    title: "Uang terasa cepat habis",
    body: "Akhir bulan datang lebih cepat, tapi sulit tahu pengeluaran mana yang paling berpengaruh.",
  },
  {
    icon: BarChart3,
    title: "Data ada, keputusan belum jelas",
    body: "Catatan transaksi semakin panjang, tetapi belum membantu menentukan langkah berikutnya.",
  },
  {
    icon: Target,
    title: "Target sulit dipantau",
    body: "Ingin menabung, mengurangi pengeluaran, atau lebih disiplin, tetapi progresnya sering tidak terlihat.",
  },
];

const benefits = [
  {
    icon: Home,
    title: "Ringkasan Keuangan",
    body: "Lihat pemasukan, pengeluaran, dan tabungan tanpa membuka banyak sheet.",
  },
  {
    icon: WalletCards,
    title: "Analisis Pengeluaran",
    body: "Pahami kategori yang paling banyak memengaruhi kondisi keuangan keluarga.",
  },
  {
    icon: BarChart3,
    title: "Tren Bulanan",
    body: "Pantau perubahan kebiasaan finansial dari waktu ke waktu.",
  },
  {
    icon: Smile,
    title: "Insight yang Mudah Dibaca",
    body: "Temukan pola yang sering terlewat tanpa harus membaca tabel panjang.",
  },
];

const featureCards = [
  ["Monthly Spending", BarChart3, "Lihat perubahan pengeluaran dari bulan ke bulan."],
  ["Category Breakdown", PieChart, "Ketahui kategori yang paling banyak menyerap anggaran."],
  ["Grocery vs Food", WalletCards, "Bedakan kebutuhan rumah dan pengeluaran makan harian."],
  ["Category Heatmap", Grid3X3, "Lihat pola transaksi berdasarkan waktu dan kategori."],
  ["Top Spending", CircleDollarSign, "Temukan transaksi terbesar yang paling berdampak."],
  ["Anomaly Signals", TriangleAlert, "Kenali pengeluaran yang tidak biasa."],
  ["Import Review", Eye, "Tinjau transaksi sebelum disimpan ke Omon."],
];

const steps = [
  {
    icon: FileSpreadsheet,
    title: "Catat Transaksi",
    description: "Masukkan pemasukan dan pengeluaran ke Google Sheets seperti biasa.",
    source: "Google Sheets",
  },
  {
    icon: RefreshCw,
    title: "Sinkronisasi Terkontrol",
    description: "Omon membaca data yang Anda pilih dan menyimpannya sebagai data Omon.",
    source: "Omon Dashboard",
  },
  {
    icon: BarChart3,
    title: "Dashboard & Insight",
    description: "Lihat ringkasan keuangan, tren pengeluaran, dan tanda yang perlu diperhatikan.",
    source: "Insight & Analytics",
  },
  {
    icon: Target,
    title: "Ambil Keputusan",
    description: "Gunakan informasi yang lebih jelas untuk menentukan langkah berikutnya.",
    source: "Kontrol Tetap di Pengguna",
  },
];

const roadmapItems = [
  ["done", "Google Sheets Sync"],
  ["done", "Financial Dashboard"],
  ["done", "Analytics & Insight"],
  ["done", "Budget Foundation"],
  ["done", "Search & Import Review"],
  ["done", "Privacy Mode"],
  ["progress", "Mobile Refinement"],
];

const audiences = [
  ["Pasangan Baru Menikah", "Bangun kebiasaan finansial yang sehat sejak awal.", HeartHandshake],
  ["Keluarga Muda", "Pantau pengeluaran rumah tangga dan tabungan bersama.", Home],
  ["Personal Finance Enthusiast", "Lihat seluruh transaksi dan tren keuangan dalam satu tempat.", Target],
  ["Freelancer", "Kelola pemasukan yang tidak selalu tetap dengan lebih jelas.", CalendarClock],
];

const insightExamples = [
  "Pengeluaran makan naik 18% dibanding bulan lalu.",
  "Belanja online meningkat dalam 3 bulan terakhir.",
  "Grocery mulai melebihi rata-rata bulanan.",
  "Potensi tabungan bulan ini Rp1.200.000 jika pola belanja tetap dijaga.",
];

const pricingPlans = [
  {
    name: "Mulai",
    price: "Akun Omon",
    description: "Untuk masuk atau membuat akses Omon melalui metode yang tersedia.",
    features: ["Google sign-in", "Login akun yang sudah tersedia", "Workspace terpisah", "Pengaturan privasi nominal"],
    cta: "Mulai menggunakan Omon",
    highlighted: false,
  },
  {
    name: "Setelah Masuk",
    price: "Dashboard",
    description: "Lanjutkan ke pengalaman utama untuk mengelola data dan koneksi.",
    features: ["Dashboard", "Analytics", "Budget", "Search", "Import", "Settings"],
    cta: "Masuk ke Omon",
    highlighted: true,
  },
];

const faqs = [
  [
    "Apakah data saya aman?",
    "Omon menggunakan koneksi Google yang Anda izinkan. Data dipakai untuk menampilkan dashboard dan insight keuangan di Omon.",
  ],
  [
    "Apakah harus menggunakan Google Sheets?",
    "Untuk versi awal, Omon dirancang agar mudah digunakan bersama Google Sheets.",
  ],
  [
    "Apakah bisa digunakan bersama pasangan?",
    "Ya. Omon dibuat untuk membantu keluarga atau pasangan memahami kondisi keuangan bersama.",
  ],
  [
    "Apa yang terjadi setelah saya mulai?",
    "Anda akan masuk ke halaman autentikasi Omon. Setelah login berhasil, Omon membuka dashboard utama.",
  ],
  [
    "Apakah bisa dibuka dari HP?",
    "Ya. Landing page dan dashboard dirancang agar nyaman digunakan di desktop maupun mobile.",
  ],
  [
    "Bagaimana jika saya ingin bertanya atau memberi feedback?",
    "Anda bisa menghubungi kami melalui email omon.dashboard@gmail.com atau WhatsApp 087822424274.",
  ],
];

const monthlyBars = [46, 68, 53, 82, 61, 74, 58, 91];
const heatmap = [40, 72, 55, 88, 62, 35, 77, 50, 93, 66, 45, 81, 57, 69, 38, 84];

function App() {
  const [menuOpen, setMenuOpen] = useState(false);
  const [openFaq, setOpenFaq] = useState(0);
  const [showBackToTop, setShowBackToTop] = useState(false);
  const dashboardUrl =
    import.meta.env.VITE_DASHBOARD_URL || "http://127.0.0.1:5173";

  useEffect(() => {
    const handleScroll = () => {
      setShowBackToTop(window.scrollY > 520);
    };

    handleScroll();
    window.addEventListener("scroll", handleScroll, { passive: true });

    return () => window.removeEventListener("scroll", handleScroll);
  }, []);

  return (
    <main className="min-h-screen overflow-hidden bg-[#f7faf8] text-[#0b1e36]">
      <Header
        dashboardUrl={dashboardUrl}
        menuOpen={menuOpen}
        setMenuOpen={setMenuOpen}
      />

      <Hero dashboardUrl={dashboardUrl} />
      <BrandStory />
      <ProblemSection />
      <SolutionSection />
      <FeatureShowcase />
      <HowItWorks />
      <TargetUsers />
      <InsightSection />
      <TrustStatement />
      <RoadmapSection />
      <PricingSection dashboardUrl={dashboardUrl} />
      <FaqSection openFaq={openFaq} setOpenFaq={setOpenFaq} />
      <FinalCta dashboardUrl={dashboardUrl} />
      <Footer dashboardUrl={dashboardUrl} />
      <BackToTopButton visible={showBackToTop} />
    </main>
  );
}

function Header({ dashboardUrl, menuOpen, setMenuOpen }) {
  return (
    <header className="sticky top-0 z-40 border-b border-[#dfe8e2] bg-[#f7faf8]/90 backdrop-blur-xl">
      <div className="mx-auto flex h-[72px] max-w-7xl items-center justify-between px-5 lg:px-8">
        <a className="flex items-center gap-3" href="#top" aria-label="Omon Dashboard">
          <BrandLogo size="sm" />
          <span className="text-base font-semibold">Omon Dashboard</span>
        </a>

        <nav className="hidden items-center gap-7 text-sm font-semibold text-[#53655f] md:flex">
          {navItems.map(([label, href]) => (
            <a className="transition hover:text-[#0b1e36]" href={href} key={label}>
              {label}
            </a>
          ))}
        </nav>

        <div className="hidden items-center gap-3 md:flex">
          <a
            className="inline-flex min-h-10 items-center justify-center rounded-lg px-4 text-sm font-semibold text-[#53655f] transition hover:text-[#0b1e36]"
            href={dashboardUrl}
          >
            Masuk
          </a>
          <a
            className="inline-flex min-h-10 items-center justify-center gap-2 rounded-lg bg-[#0b1e36] px-5 text-sm font-semibold text-white shadow-sm shadow-[#0b1e36]/20 transition hover:bg-[#123354]"
            href={dashboardUrl}
          >
            Mulai menggunakan Omon <ArrowRight size={16} aria-hidden="true" />
          </a>
        </div>

        <button
          className="grid h-10 w-10 place-items-center rounded-lg border border-[#d7e2dc] bg-white text-[#0b1e36] md:hidden"
          onClick={() => setMenuOpen((value) => !value)}
          type="button"
          aria-label={menuOpen ? "Tutup menu" : "Buka menu"}
        >
          {menuOpen ? <X size={20} /> : <Menu size={20} />}
        </button>
      </div>

      {menuOpen && (
        <nav className="border-t border-[#dfe8e2] bg-white px-5 py-4 md:hidden">
          <div className="mx-auto grid max-w-7xl gap-3 text-sm font-semibold text-[#53655f]">
            {navItems.map(([label, href]) => (
              <a className="py-2" href={href} key={label} onClick={() => setMenuOpen(false)}>
                {label}
              </a>
            ))}
            <a
              className="mt-2 inline-flex min-h-11 items-center justify-center gap-2 rounded-lg bg-[#0b1e36] px-5 text-white"
              href={dashboardUrl}
            >
              Mulai menggunakan Omon <ArrowRight size={16} aria-hidden="true" />
            </a>
          </div>
        </nav>
      )}
    </header>
  );
}

function Hero({ dashboardUrl }) {
  return (
    <section id="top" className="relative">
      <div className="absolute inset-x-0 top-0 h-[520px] bg-[radial-gradient(circle_at_50%_0%,rgba(84,157,103,0.22),transparent_58%)]" />
      <div className="pointer-events-none absolute left-[8%] top-32 hidden h-11 w-11 rounded-full border border-[#d7eadb] bg-white/80 shadow-sm md:block omon-drift-slow">
        <LockKeyhole className="m-2.5 text-[#2f7a4f]" size={22} aria-hidden="true" />
      </div>
      <div className="pointer-events-none absolute right-[10%] top-44 hidden h-9 w-9 rounded-full bg-[#fff4ed] shadow-sm lg:block omon-drift">
        <CircleDollarSign className="m-2 text-[#b96545]" size={20} aria-hidden="true" />
      </div>
      <div className="relative mx-auto max-w-7xl px-5 pb-16 pt-14 lg:px-8 lg:pb-24 lg:pt-20">
        <div className="mx-auto max-w-4xl text-center">
          <div className="mx-auto flex w-fit items-center gap-3 rounded-2xl border border-[#dfe8e2] bg-white px-4 py-3 shadow-sm omon-fade-in">
            <BrandLogo size="md" animated />
            <div className="text-left">
              <p className="text-sm font-bold text-[#0b1e36]">Omon</p>
              <p className="text-xs font-semibold text-[#2f7a4f]">Calm Financial Companion</p>
            </div>
          </div>
          <div className="mx-auto mt-5 inline-flex items-center gap-2 rounded-full border border-[#b8d6bf] bg-[#edf7ef] px-4 py-2 text-sm font-bold text-[#2f7a4f] shadow-sm omon-fade-in omon-delay-1">
            <HeartHandshake size={16} aria-hidden="true" />
            Kelola uang dengan lebih tenang.
          </div>
          <h1 className="mx-auto mt-6 max-w-4xl text-4xl font-semibold leading-[1.06] text-[#0b1e36] sm:text-5xl lg:text-7xl omon-fade-in omon-delay-2">
            Kelola uang dengan lebih tenang.
          </h1>
          <p className="mx-auto mt-6 max-w-2xl text-base leading-8 text-[#53655f] sm:text-lg omon-fade-in omon-delay-3">
            Omon membantu Anda memahami pemasukan, pengeluaran, anggaran, dan pola keuangan dalam satu pengalaman yang sederhana.
          </p>
          <p className="mx-auto mt-3 max-w-xl text-sm font-semibold leading-7 text-[#2f7a4f] sm:text-base">
            Data tetap bisa ditinjau, disinkronkan, dan dikelola dengan kontrol yang jelas.
          </p>
          <div className="mt-8 flex flex-col items-center justify-center gap-3 sm:flex-row">
            <a className="inline-flex min-h-12 w-full items-center justify-center gap-2 rounded-lg bg-[#0b1e36] px-6 font-semibold text-white shadow-lg shadow-[#0b1e36]/20 transition hover:bg-[#123354] sm:w-auto" href={dashboardUrl}>
              Mulai menggunakan Omon <ArrowRight size={18} aria-hidden="true" />
            </a>
            <a className="inline-flex min-h-12 w-full items-center justify-center gap-2 rounded-lg border border-[#cbd9d1] bg-white px-6 font-semibold text-[#0b1e36] shadow-sm transition hover:border-[#9fb8aa] sm:w-auto" href="#how-it-works">
              Lihat cara kerjanya <Eye size={18} aria-hidden="true" />
            </a>
          </div>
          <div className="mx-auto mt-6 flex max-w-2xl flex-wrap items-center justify-center gap-2 text-xs font-bold text-[#53655f]">
            {["Google Sheet sebagai sumber", "Review sebelum simpan", "Hide Amount tersedia"].map((item) => (
              <span className="inline-flex items-center gap-2 rounded-full border border-[#dfe8e2] bg-white px-3 py-2" key={item}>
                <Check className="text-[#2f7a4f]" size={14} aria-hidden="true" />
                {item}
              </span>
            ))}
          </div>
        </div>

        <div className="mt-12 lg:mt-16 omon-dashboard-float">
          <DashboardMockup />
        </div>
      </div>
    </section>
  );
}

function ProblemSection() {
  return (
    <Section
      id="problem"
      eyebrow="Masalah sehari-hari"
      title="Mengelola keuangan seharusnya tidak serumit ini."
      description="Banyak keluarga sudah mencatat pengeluaran, tapi tetap sulit memahami kondisi keuangannya secara menyeluruh."
    >
      <div className="grid gap-4 md:grid-cols-3">
        {problems.map((item) => (
          <InfoCard {...item} key={item.title} tone="warm" />
        ))}
      </div>
    </Section>
  );
}

function SolutionSection() {
  return (
    <Section
      id="solution"
      eyebrow="Solusi Omon"
      title="Dari catatan transaksi menjadi gambaran yang jelas."
      description="Omon Dashboard mengubah data keuangan harian menjadi informasi yang mudah dibaca, dipahami, dan dibicarakan bersama keluarga."
    >
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {benefits.map((item) => (
          <InfoCard {...item} key={item.title} />
        ))}
      </div>
    </Section>
  );
}

function FeatureShowcase() {
  return (
    <section id="features" className="border-y border-[#dfe8e2] bg-white py-16 lg:py-24">
      <div className="mx-auto max-w-7xl px-5 lg:px-8">
        <div className="grid gap-10 lg:grid-cols-[0.85fr_1.15fr] lg:items-center">
          <div>
            <p className="text-sm font-semibold uppercase tracking-[0.14em] text-[#2f7a4f]">Fitur</p>
            <h2 className="mt-3 text-3xl font-semibold leading-tight text-[#0b1e36] sm:text-4xl">
              Bukan sekadar grafik.
            </h2>
            <p className="mt-4 max-w-xl text-base leading-8 text-[#53655f]">
              Omon membantu Anda membaca cerita di balik setiap transaksi.
            </p>
          </div>
          <FeaturePreview />
        </div>

        <div className="mt-10 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {featureCards.map(([title, Icon, body]) => (
            <article className="omon-card rounded-lg border border-[#dfe8e2] bg-[#f7faf8] p-5" key={title}>
              <span className="grid h-10 w-10 place-items-center rounded-lg bg-white text-[#2f7a4f] shadow-sm">
                <Icon size={20} aria-hidden="true" />
              </span>
              <h3 className="mt-5 text-base font-semibold text-[#0b1e36]">{title}</h3>
              <p className="mt-3 text-sm leading-6 text-[#53655f]">{body}</p>
            </article>
          ))}
        </div>
      </div>
    </section>
  );
}

function HowItWorks() {
  return (
    <Section
      id="how-it-works"
      eyebrow="Cara Kerja"
      title="Cara Kerja Omon"
      description="Tetap gunakan Google Sheets seperti biasa. Omon membantu mengubah data transaksi menjadi informasi yang lebih mudah dipahami."
    >
      <div className="rounded-2xl border border-[#dfe8e2] bg-white p-4 shadow-sm sm:p-6">
        <div className="grid gap-4 lg:grid-cols-4 lg:items-stretch">
          {steps.map(({ icon: Icon, title, description, source }, index) => (
            <article className="relative" key={title}>
              <div className="omon-card h-full rounded-xl border border-[#dfe8e2] bg-[#f7faf8] p-5">
                <div className="flex items-center justify-between gap-4">
                  <span className="grid h-12 w-12 place-items-center rounded-xl border border-[#cfe1d6] bg-white text-[#2f7a4f] shadow-sm">
                    <Icon size={23} aria-hidden="true" />
                  </span>
                  <span className="rounded-full bg-white px-3 py-1 text-xs font-bold text-[#2f7a4f]">
                    {source}
                  </span>
                </div>
                <h3 className="mt-6 text-lg font-semibold text-[#0b1e36]">{title}</h3>
                <p className="mt-3 text-sm leading-6 text-[#53655f]">{description}</p>
              </div>
              {index < steps.length - 1 && (
                <div className="flex justify-center py-3 text-[#2f7a4f] lg:absolute lg:-right-7 lg:top-1/2 lg:z-10 lg:-translate-y-1/2 lg:px-0 lg:py-0">
                  <ArrowRight className="hidden lg:block" size={26} aria-hidden="true" />
                  <ArrowRight className="rotate-90 lg:hidden" size={24} aria-hidden="true" />
                </div>
              )}
            </article>
          ))}
        </div>
      </div>
    </Section>
  );
}

function TrustStatement() {
  return (
    <section className="bg-[#f7faf8] py-14 lg:py-20">
      <div className="mx-auto max-w-5xl px-5 lg:px-8">
        <div className="rounded-2xl border border-[#dfe8e2] bg-white p-6 shadow-sm sm:p-8">
          <div className="flex flex-col gap-5 md:flex-row md:items-start">
            <span className="grid h-12 w-12 shrink-0 place-items-center rounded-xl border border-[#cfe1d6] bg-[#edf7ef] text-[#2f7a4f]">
              <HeartHandshake size={24} aria-hidden="true" />
            </span>
            <div>
              <p className="text-sm font-semibold uppercase tracking-[0.14em] text-[#2f7a4f]">
                Origin
              </p>
              <h2 className="mt-2 text-3xl font-semibold leading-tight text-[#0b1e36]">
                Dibangun dari kebutuhan keluarga sendiri.
              </h2>
              <div className="mt-4 grid gap-3 text-base leading-8 text-[#53655f]">
                <p>
                  Omon pertama kali dibuat untuk membantu memahami kondisi keuangan rumah tangga tanpa harus membuka spreadsheet yang rumit setiap hari.
                </p>
                <p>
                  Seiring waktu, dashboard ini berkembang menjadi alat yang membantu melihat pola pengeluaran, memantau tabungan, dan mengambil keputusan finansial dengan lebih percaya diri.
                </p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}

function RoadmapSection() {
  return (
    <section className="bg-white py-14 lg:py-20">
      <div className="mx-auto max-w-6xl px-5 lg:px-8">
        <div className="mb-8 max-w-3xl">
          <p className="text-sm font-semibold uppercase tracking-[0.14em] text-[#2f7a4f]">
            Prinsip produk
          </p>
          <h2 className="mt-3 text-3xl font-semibold leading-tight text-[#0b1e36] sm:text-4xl">
            Dirancang agar terasa aman dan terkendali.
          </h2>
          <p className="mt-4 text-base leading-8 text-[#53655f]">
            Omon membantu membaca data keuangan tanpa mengambil kontrol dari pengguna.
          </p>
        </div>

        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          {roadmapItems.map(([status, label]) => (
            <article className="rounded-lg border border-[#dfe8e2] bg-[#f7faf8] p-4" key={label}>
              <span
                className={`inline-flex items-center gap-2 rounded-full px-3 py-1 text-xs font-bold ${
                  status === "done"
                    ? "bg-[#edf7ef] text-[#2f7a4f]"
                    : "bg-[#fff4ed] text-[#9b563b]"
                }`}
              >
                {status === "done" ? (
                  <Check size={14} aria-hidden="true" />
                ) : (
                  <RefreshCw size={14} aria-hidden="true" />
                )}
                {status === "done" ? "Tersedia" : "Dirapikan"}
              </span>
              <h3 className="mt-4 text-base font-semibold text-[#0b1e36]">{label}</h3>
            </article>
          ))}
        </div>
      </div>
    </section>
  );
}
function TargetUsers() {
  const [activeAudience, setActiveAudience] = useState(0);
  const [hoverPaused, setHoverPaused] = useState(false);
  const [userPaused, setUserPaused] = useState(false);
  const [reducedMotion, setReducedMotion] = useState(false);
  const carouselRefs = useRef([]);
  const pauseTimeoutRef = useRef(null);
  const programmaticScrollRef = useRef(false);
  const touchStartRef = useRef(null);

  const pauseForInteraction = () => {
    setUserPaused(true);
    window.clearTimeout(pauseTimeoutRef.current);
    pauseTimeoutRef.current = window.setTimeout(() => {
      setUserPaused(false);
    }, 8000);
  };

  const goToAudience = (index, shouldPause = true) => {
    const nextIndex = (index + audiences.length) % audiences.length;

    if (shouldPause) {
      pauseForInteraction();
    }

    setActiveAudience(nextIndex);
  };

  useEffect(() => {
    const motionQuery = window.matchMedia("(prefers-reduced-motion: reduce)");
    const updateReducedMotion = () => setReducedMotion(motionQuery.matches);

    updateReducedMotion();
    motionQuery.addEventListener("change", updateReducedMotion);

    return () => {
      motionQuery.removeEventListener("change", updateReducedMotion);
      window.clearTimeout(pauseTimeoutRef.current);
    };
  }, []);

  useEffect(() => {
    const activeCard = carouselRefs.current[activeAudience];

    if (!activeCard) {
      return;
    }

    programmaticScrollRef.current = true;
    activeCard.scrollIntoView({
      behavior: reducedMotion ? "auto" : "smooth",
      block: "nearest",
      inline: "start",
    });

    const resetProgrammaticScroll = window.setTimeout(() => {
      programmaticScrollRef.current = false;
    }, 450);

    return () => window.clearTimeout(resetProgrammaticScroll);
  }, [activeAudience, reducedMotion]);

  useEffect(() => {
    if (reducedMotion || hoverPaused || userPaused) {
      return undefined;
    }

    const interval = window.setInterval(() => {
      setActiveAudience((current) => (current + 1) % audiences.length);
    }, 5000);

    return () => window.clearInterval(interval);
  }, [hoverPaused, reducedMotion, userPaused]);

  const handleTouchEnd = (event) => {
    if (touchStartRef.current === null) {
      return;
    }

    const deltaX = touchStartRef.current - event.changedTouches[0].clientX;
    touchStartRef.current = null;

    if (Math.abs(deltaX) < 40) {
      pauseForInteraction();
      return;
    }

    goToAudience(activeAudience + (deltaX > 0 ? 1 : -1));
  };

  return (
    <section className="bg-white py-16 lg:py-24">
      <div className="mx-auto max-w-7xl px-5 lg:px-8">
        <div className="relative overflow-hidden rounded-[1.75rem] border border-[#d7eadb] bg-[linear-gradient(135deg,#f3fbf5_0%,#ffffff_55%,#edf7ef_100%)] p-6 shadow-xl shadow-[#0b1e36]/6 sm:p-8 lg:p-10">
          <div className="pointer-events-none absolute right-6 top-6 hidden h-16 w-16 rounded-full border border-[#d7eadb] bg-white/70 text-[#2f7a4f] sm:grid sm:place-items-center omon-drift-slow">
            <HeartHandshake size={30} aria-hidden="true" />
          </div>
          <div className="pointer-events-none absolute -bottom-10 -right-8 hidden opacity-10 lg:block">
            <img className="h-40 w-40 object-contain" src={omonLogo} alt="" loading="lazy" />
          </div>

          <div className="max-w-3xl">
            <p className="text-sm font-semibold uppercase tracking-[0.14em] text-[#2f7a4f]">Untuk siapa</p>
            <h2 className="mt-3 text-3xl font-semibold leading-tight text-[#0b1e36] sm:text-4xl">
              Dibuat untuk keluarga yang ingin lebih tenang mengatur keuangan.
            </h2>
            <p className="mt-4 text-base leading-8 text-[#53655f]">
              Omon cocok untuk siapa saja yang ingin memahami kondisi finansial tanpa harus menjadi ahli spreadsheet.
            </p>
            <p className="mt-5 max-w-2xl rounded-xl border border-[#cfe1d6] bg-white/75 px-4 py-3 text-sm font-semibold leading-7 text-[#2f7a4f] shadow-sm">
              Keuangan yang lebih jelas membantu keluarga mengambil keputusan yang lebih baik.
            </p>
          </div>

          <div className="mt-10 hidden gap-4 lg:grid lg:grid-cols-4">
            {audiences.map(([title, body, Icon]) => (
              <AudienceCard body={body} icon={Icon} key={title} title={title} />
            ))}
          </div>

          <div
            className="mt-10 lg:hidden"
            onMouseEnter={() => setHoverPaused(true)}
            onMouseLeave={() => setHoverPaused(false)}
            onFocus={() => setHoverPaused(true)}
            onBlur={() => setHoverPaused(false)}
          >
            <div
              className="flex snap-x snap-mandatory gap-4 overflow-x-auto pb-3 [scrollbar-width:none] [&::-webkit-scrollbar]:hidden"
              onScroll={() => {
                if (!programmaticScrollRef.current) {
                  pauseForInteraction();
                }
              }}
              onTouchStart={(event) => {
                touchStartRef.current = event.touches[0].clientX;
                pauseForInteraction();
              }}
              onTouchEnd={handleTouchEnd}
            >
              {audiences.map(([title, body, Icon], index) => (
                <div
                  className="min-w-full snap-start md:min-w-[calc(50%-0.5rem)]"
                  key={title}
                  ref={(node) => {
                    carouselRefs.current[index] = node;
                  }}
                >
                  <AudienceCard
                    active={activeAudience === index}
                    body={body}
                    icon={Icon}
                    title={title}
                  />
                </div>
              ))}
            </div>

            <div className="mt-5 flex items-center justify-between gap-4">
              <div className="flex gap-2">
                {audiences.map(([title], index) => (
                  <button
                    aria-label={`Lihat target user ${title}`}
                    className={`h-2.5 rounded-full transition ${
                      activeAudience === index ? "w-8 bg-[#2f7a4f]" : "w-2.5 bg-[#cfe1d6]"
                    }`}
                    key={title}
                    onClick={() => goToAudience(index)}
                    type="button"
                  />
                ))}
              </div>

              <div className="flex gap-2">
                <button
                  aria-label="Target user sebelumnya"
                  className="grid h-11 w-11 place-items-center rounded-full bg-white text-[#0b1e36] shadow-sm ring-1 ring-[#dfe8e2] transition hover:-translate-y-0.5 hover:bg-[#edf7ef] hover:text-[#2f7a4f]"
                  onClick={() => goToAudience(activeAudience - 1)}
                  type="button"
                >
                  <ChevronLeft size={20} aria-hidden="true" />
                </button>
                <button
                  aria-label="Target user berikutnya"
                  className="grid h-11 w-11 place-items-center rounded-full bg-[#0b1e36] text-white shadow-sm transition hover:-translate-y-0.5 hover:bg-[#2f7a4f]"
                  onClick={() => goToAudience(activeAudience + 1)}
                  type="button"
                >
                  <ChevronRight size={20} aria-hidden="true" />
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}

function AudienceCard({ active = false, body, icon: Icon, title }) {
  return (
    <article
      className={`omon-card group h-full rounded-xl border bg-white/85 p-6 shadow-sm ${
        active ? "border-[#9fcfab] shadow-[#2f7a4f]/12" : "border-[#dfe8e2]"
      }`}
    >
      <span className="grid h-11 w-11 place-items-center rounded-xl border border-[#cfe1d6] bg-[#edf7ef] text-[#2f7a4f] transition duration-300 group-hover:scale-105">
        <Icon size={21} aria-hidden="true" />
      </span>
      <h3 className="mt-6 text-lg font-semibold text-[#0b1e36]">{title}</h3>
      <p className="mt-3 text-sm leading-6 text-[#53655f]">{body}</p>
    </article>
  );
}

function BrandStory() {
  return (
    <section id="story" className="bg-[#f7faf8] py-16 lg:py-24">
      <div className="mx-auto grid max-w-7xl gap-10 px-5 lg:grid-cols-[0.9fr_1.1fr] lg:items-center lg:px-8">
        <div className="mx-auto max-w-sm rounded-[1.5rem] border border-[#dfe8e2] bg-white p-6 shadow-xl shadow-[#0b1e36]/8 lg:order-2 omon-drift-slow">
          <img
            className="mx-auto h-auto w-full max-w-[280px]"
            src={omonLogo}
            alt="Maskot Omon Dashboard"
            loading="lazy"
          />
        </div>
        <div>
          <p className="text-sm font-semibold uppercase tracking-[0.14em] text-[#2f7a4f]">Cerita brand</p>
          <h2 className="mt-3 text-3xl font-semibold leading-tight text-[#0b1e36] sm:text-4xl">
            Kenapa namanya Omon?
          </h2>
          <div className="mt-5 grid gap-4 text-base leading-8 text-[#53655f]">
            <p>
              Omon adalah singkatan dari <strong className="text-[#0b1e36]">Operational Monitoring</strong>.
            </p>
            <p>
              Awalnya, nama ini lahir dari kebiasaan sederhana: banyak orang ingin lebih rapi mengatur uang, tapi sering menunda mencatat, mengevaluasi, atau melihat kembali kondisi keuangannya.
            </p>
            <p>
              Omon mempertahankan semangat itu: membantu percakapan tentang uang menjadi lebih jelas dan lebih tenang.
            </p>
            <p>
              Karena itu Omon Dashboard dibuat untuk membantu mengubah catatan transaksi menjadi visualisasi yang mudah dipahami, supaya keluarga bisa mengambil keputusan finansial dengan lebih jelas.
            </p>
          </div>
          <div className="mt-8 rounded-2xl border border-[#b8d6bf] bg-[#edf7ef] p-6 shadow-sm">
            <div className="flex items-center gap-3">
              <span className="grid h-10 w-10 place-items-center rounded-xl border border-[#cfe1d6] bg-white text-[#2f7a4f]">
                <HeartHandshake size={21} aria-hidden="true" />
              </span>
              <p className="text-sm font-bold uppercase tracking-[0.12em] text-[#2f7a4f]">
                Cara Omon membantu
              </p>
            </div>
            <blockquote className="mt-5 text-3xl font-semibold leading-tight text-[#0b1e36] sm:text-4xl">
              Kelola uang dengan lebih tenang.
            </blockquote>
            <p className="mt-4 text-sm font-semibold leading-7 text-[#53655f]">
              Karena keputusan keuangan yang baik dimulai dari data yang jelas dan mudah dipahami.
            </p>
          </div>
          <p className="mt-5 rounded-lg border border-[#dfe8e2] bg-white px-5 py-4 text-sm font-semibold leading-7 text-[#53655f] shadow-sm">
            Berawal dari kebutuhan keluarga sendiri, Omon dibuat untuk membantu memahami kondisi keuangan tanpa harus membuka spreadsheet yang rumit setiap hari.
          </p>
        </div>
      </div>
    </section>
  );
}

function InsightSection() {
  return (
    <section className="bg-white py-16 lg:py-24">
      <div className="mx-auto grid max-w-7xl gap-10 px-5 lg:grid-cols-[0.9fr_1.1fr] lg:items-center lg:px-8">
        <div>
          <p className="text-sm font-semibold uppercase tracking-[0.14em] text-[#2f7a4f]">Insight otomatis</p>
          <h2 className="mt-3 text-3xl font-semibold leading-tight text-[#0b1e36] sm:text-4xl">
            Temukan pola yang sering terlewat.
          </h2>
          <p className="mt-4 max-w-xl text-base leading-8 text-[#53655f]">
            Omon membantu melihat perubahan kebiasaan pengeluaran sebelum menjadi masalah.
          </p>
        </div>
        <div className="rounded-lg border border-[#dfe8e2] bg-[#f7faf8] p-4 shadow-xl shadow-[#0b1e36]/8 sm:p-6">
          <div className="rounded-lg border border-[#dfe8e2] bg-white p-5">
            <div className="flex items-center gap-3">
              <span className="grid h-11 w-11 place-items-center rounded-lg bg-[#2f7a4f] text-white">
                <Sparkles size={22} aria-hidden="true" />
              </span>
              <div>
                <p className="text-sm font-semibold text-[#2f7a4f]">Ringkasan pola</p>
                <h3 className="text-xl font-semibold text-[#0b1e36]">Yang perlu diperhatikan bulan ini</h3>
              </div>
            </div>
            <div className="mt-6 grid gap-3">
              {insightExamples.map((insight) => (
                <div className="flex gap-3 rounded-lg border border-[#e4ece7] bg-[#f7faf8] p-4" key={insight}>
                  <Check className="mt-0.5 shrink-0 text-[#2f7a4f]" size={18} aria-hidden="true" />
                  <p className="text-sm leading-6 text-[#334640]">{insight}</p>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}

function PricingSection({ dashboardUrl }) {
  return (
    <Section
      id="access"
      eyebrow="Mulai"
      title="Masuk dengan cara yang tersedia."
      description="Omon akan membawa Anda ke halaman autentikasi. Jika akun belum tersedia, gunakan metode yang disediakan oleh lingkungan Omon saat ini."
    >
      <div className="mx-auto grid max-w-5xl gap-5 lg:grid-cols-2">
        {pricingPlans.map((plan) => (
          <article
            className={`omon-card rounded-lg border p-6 shadow-sm ${
              plan.highlighted
                ? "border-[#0b1e36] bg-[#0b1e36] text-white shadow-[#0b1e36]/16"
                : "border-[#dfe8e2] bg-white text-[#0b1e36]"
            }`}
            key={plan.name}
          >
            <div className="flex items-start justify-between gap-4">
              <div>
                <h3 className="text-2xl font-semibold">{plan.name}</h3>
                <p className={`mt-3 text-sm leading-6 ${plan.highlighted ? "text-[#c8d7d2]" : "text-[#53655f]"}`}>
                  {plan.description}
                </p>
              </div>
              {plan.highlighted && (
                <span className="rounded-full bg-[#9fd4a8] px-3 py-1 text-xs font-bold text-[#0b1e36]">
                  Setelah login
                </span>
              )}
            </div>
            <div className="mt-8 flex items-end gap-2">
              <span className="text-3xl font-semibold">{plan.price}</span>
            </div>
            <ul className="mt-8 grid gap-3">
              {plan.features.map((feature) => (
                <li className="flex items-center gap-3 text-sm font-medium" key={feature}>
                  <Check className={plan.highlighted ? "text-[#9fd4a8]" : "text-[#2f7a4f]"} size={18} aria-hidden="true" />
                  {feature}
                </li>
              ))}
            </ul>
            <a
              className={`mt-8 inline-flex min-h-12 w-full items-center justify-center gap-2 rounded-lg px-5 font-semibold ${
                plan.highlighted
                  ? "bg-white text-[#0b1e36] hover:bg-[#eef6f2]"
                  : "bg-[#0b1e36] text-white hover:bg-[#123354]"
              }`}
              href={dashboardUrl}
            >
              {plan.cta} <ArrowRight size={18} aria-hidden="true" />
            </a>
          </article>
        ))}
      </div>
    </Section>
  );
}

function FaqSection({ openFaq, setOpenFaq }) {
  return (
    <section id="faq" className="border-y border-[#dfe8e2] bg-white py-16 lg:py-24">
      <div className="mx-auto grid max-w-7xl gap-10 px-5 lg:grid-cols-[0.75fr_1.25fr] lg:px-8">
        <div>
          <p className="text-sm font-semibold uppercase tracking-[0.14em] text-[#2f7a4f]">FAQ</p>
          <h2 className="mt-3 text-3xl font-semibold leading-tight text-[#0b1e36] sm:text-4xl">
            Pertanyaan umum
          </h2>
          <p className="mt-4 text-base leading-8 text-[#53655f]">
            Jawaban singkat untuk hal-hal yang biasanya perlu dipastikan sebelum mulai.
          </p>
        </div>
        <div className="grid gap-3">
          {faqs.map(([question, answer], index) => {
            const isOpen = openFaq === index;
            return (
            <article className="rounded-lg border border-[#dfe8e2] bg-[#f7faf8]" key={question}>
                <button
                  className="flex w-full items-center justify-between gap-4 px-5 py-4 text-left font-semibold text-[#0b1e36]"
                  onClick={() => setOpenFaq(isOpen ? -1 : index)}
                  type="button"
                  aria-expanded={isOpen}
                >
                  {question}
                  <ChevronDown className={`shrink-0 transition ${isOpen ? "rotate-180" : ""}`} size={19} aria-hidden="true" />
                </button>
                {isOpen && (
                  <p className="px-5 pb-5 text-sm leading-7 text-[#53655f]">
                    {question === "Bagaimana jika saya ingin bertanya atau memberi feedback?" ? (
                      <>
                        Anda bisa menghubungi kami melalui email{" "}
                        <a className="font-semibold text-[#2f7a4f] underline-offset-4 hover:underline" href={contactLinks.mailto}>
                          {contactLinks.email}
                        </a>{" "}
                        atau WhatsApp{" "}
                        <a className="font-semibold text-[#2f7a4f] underline-offset-4 hover:underline" href={contactLinks.whatsappUrl}>
                          {contactLinks.whatsapp}
                        </a>
                        .
                      </>
                    ) : (
                      answer
                    )}
                  </p>
                )}
              </article>
            );
          })}
        </div>
      </div>
    </section>
  );
}

function FinalCta({ dashboardUrl }) {
  return (
    <section className="bg-[#f7faf8] py-16 lg:py-24">
      <div className="mx-auto max-w-5xl px-5 text-center lg:px-8">
        <div className="mx-auto grid h-16 w-16 place-items-center overflow-hidden rounded-2xl border border-[#dfe8e2] bg-white shadow-sm">
          <img className="h-14 w-14 object-contain" src={omonLogo} alt="" loading="lazy" />
        </div>
        <h2 className="mx-auto mt-6 max-w-3xl text-3xl font-semibold leading-tight text-[#0b1e36] sm:text-5xl">
          Keuangan keluarga jadi lebih mudah dipahami.
        </h2>
        <p className="mx-auto mt-5 max-w-2xl text-base leading-8 text-[#53655f]">
          Mulai dari halaman autentikasi, lalu lanjutkan ke dashboard utama setelah login berhasil.
        </p>
        <div className="mt-8 flex flex-col items-center justify-center gap-3 sm:flex-row">
          <a className="inline-flex min-h-12 w-full items-center justify-center gap-2 rounded-lg bg-[#0b1e36] px-6 font-semibold text-white shadow-lg shadow-[#0b1e36]/20 transition hover:bg-[#123354] sm:w-auto" href={dashboardUrl}>
            Mulai menggunakan Omon <ArrowRight size={18} aria-hidden="true" />
          </a>
          <a className="inline-flex min-h-12 w-full items-center justify-center gap-2 rounded-lg border border-[#cbd9d1] bg-white px-6 font-semibold text-[#0b1e36] shadow-sm transition hover:border-[#9fb8aa] sm:w-auto" href="#how-it-works">
            Lihat cara kerjanya <Eye size={18} aria-hidden="true" />
          </a>
        </div>
        <p className="mx-auto mt-5 max-w-xl text-sm font-semibold leading-7 text-[#53655f]">
          Butuh bantuan atau ingin memberi feedback? Hubungi Omon melalui{" "}
          <a className="text-[#2f7a4f] underline-offset-4 hover:underline" href={contactLinks.mailto}>
            email
          </a>{" "}
          atau{" "}
          <a className="text-[#2f7a4f] underline-offset-4 hover:underline" href={contactLinks.whatsappUrl}>
            WhatsApp
          </a>
          .
        </p>
      </div>
    </section>
  );
}

function Footer({ dashboardUrl }) {
  return (
    <footer className="border-t border-[#dfe8e2] bg-white">
      <div className="mx-auto grid max-w-7xl gap-8 px-5 py-8 lg:grid-cols-[1fr_auto_auto] lg:items-start lg:px-8">
        <div>
          <a className="inline-flex items-center gap-3" href="#top" aria-label="Omon Dashboard">
            <BrandLogo size="sm" />
            <span className="text-base font-semibold text-[#0b1e36]">Omon Dashboard</span>
          </a>
          <p className="mt-3 text-sm font-semibold text-[#2f7a4f]">
            Calm Financial Companion.
          </p>
        </div>

        <div>
          <h2 className="text-sm font-bold text-[#0b1e36]">Hubungi Kami</h2>
          <div className="mt-3 grid gap-2 text-sm font-semibold text-[#53655f]">
            <a className="inline-flex items-center gap-2 transition hover:text-[#2f7a4f]" href={contactLinks.mailto}>
              <Mail size={16} aria-hidden="true" />
              {contactLinks.email}
            </a>
            <a className="inline-flex items-center gap-2 transition hover:text-[#2f7a4f]" href={contactLinks.whatsappUrl}>
              <MessageCircle size={16} aria-hidden="true" />
              WhatsApp {contactLinks.whatsapp}
            </a>
          </div>
        </div>

        <div className="flex flex-col gap-5">
          <nav className="flex flex-wrap gap-x-5 gap-y-2 text-sm font-semibold text-[#53655f]">
            {navItems.map(([label, href]) => (
              <a className="transition hover:text-[#0b1e36]" href={href} key={label}>
                {label}
              </a>
            ))}
            <a className="transition hover:text-[#0b1e36]" href={dashboardUrl}>
              Masuk
            </a>
          </nav>
          <p className="text-sm text-[#6b7d76]">
            (c) 2026 Omon. Built with care for Indonesian families.
          </p>
        </div>
      </div>
    </footer>
  );
}

function BackToTopButton({ visible }) {
  const scrollToTop = () => {
    window.scrollTo({ top: 0, behavior: "smooth" });
  };

  return (
    <button
      className={`fixed bottom-5 right-5 z-50 grid h-12 w-12 place-items-center rounded-full bg-[#0b1e36] text-white shadow-xl shadow-[#0b1e36]/20 transition duration-300 hover:-translate-y-0.5 hover:bg-[#2f7a4f] focus:outline-none focus:ring-4 focus:ring-[#9fd4a8]/50 sm:bottom-6 sm:right-6 ${
        visible ? "translate-y-0 opacity-100" : "pointer-events-none translate-y-3 opacity-0"
      }`}
      type="button"
      aria-label="Kembali ke atas"
      onClick={scrollToTop}
    >
      <ArrowUp size={21} aria-hidden="true" />
    </button>
  );
}

function Section({ id, eyebrow, title, description, children }) {
  return (
    <section id={id} className="bg-[#f7faf8] py-16 lg:py-24">
      <div className="mx-auto max-w-7xl px-5 lg:px-8">
        <div className="mx-auto mb-10 max-w-3xl text-center">
          <p className="text-sm font-semibold uppercase tracking-[0.14em] text-[#2f7a4f]">{eyebrow}</p>
          <h2 className="mt-3 text-3xl font-semibold leading-tight text-[#0b1e36] sm:text-4xl">{title}</h2>
          <p className="mx-auto mt-4 max-w-2xl text-base leading-8 text-[#53655f]">{description}</p>
        </div>
        {children}
      </div>
    </section>
  );
}

function InfoCard({ icon: Icon, title, body, tone = "cool" }) {
  return (
    <article className="omon-card rounded-lg border border-[#dfe8e2] bg-white p-6 shadow-sm">
      <span className={`grid h-12 w-12 place-items-center rounded-lg ${tone === "warm" ? "bg-[#fff4ed] text-[#b96545]" : "bg-[#edf7ef] text-[#2f7a4f]"}`}>
        <Icon size={23} aria-hidden="true" />
      </span>
      <h3 className="mt-6 text-xl font-semibold text-[#0b1e36]">{title}</h3>
      <p className="mt-4 text-sm leading-7 text-[#53655f]">{body}</p>
    </article>
  );
}

function DashboardMockup() {
  return (
    <div className="mx-auto max-w-6xl rounded-[1.5rem] border border-[#cfe0d7] bg-[#0b1e36] p-2 shadow-2xl shadow-[#0b1e36]/20 sm:p-3">
      <div className="overflow-hidden rounded-[1.15rem] bg-[#f7faf8]">
        <div className="flex items-center justify-between gap-3 border-b border-[#dfe8e2] bg-white px-4 py-3">
          <div className="flex items-center gap-2">
            <span className="h-3 w-3 rounded-full bg-[#ff8b6b]" />
            <span className="h-3 w-3 rounded-full bg-[#f8c24e]" />
            <span className="h-3 w-3 rounded-full bg-[#78b87b]" />
          </div>
          <span className="hidden text-xs font-semibold uppercase tracking-[0.14em] text-[#6b7d76] sm:inline">
            Omon household dashboard
          </span>
          <span className="inline-flex items-center gap-2 rounded-lg bg-[#edf7ef] px-3 py-1.5 text-xs font-bold text-[#2f7a4f]">
            <LockKeyhole size={13} aria-hidden="true" />
            Synced
          </span>
        </div>

        <div className="grid min-h-[560px] lg:grid-cols-[220px_1fr]">
          <aside className="hidden border-r border-[#dfe8e2] bg-white p-5 lg:block">
            <div className="flex items-center gap-3">
              <BrandLogo size="sm" />
              <div>
                <p className="text-sm font-semibold text-[#0b1e36]">Keluarga Aruna</p>
                <p className="text-xs text-[#6b7d76]">June workspace</p>
              </div>
            </div>
            <nav className="mt-8 grid gap-2">
              {["Overview", "Analytics", "Categories", "Insight"].map((item, index) => (
                <div className={`rounded-lg px-3 py-2 text-sm font-semibold ${index === 0 ? "bg-[#edf7ef] text-[#2f7a4f]" : "text-[#6b7d76]"}`} key={item}>
                  {item}
                </div>
              ))}
            </nav>
          </aside>

          <div className="min-w-0 p-4 sm:p-6">
            <div className="flex flex-col justify-between gap-4 sm:flex-row sm:items-start">
              <div>
                <p className="text-sm font-semibold text-[#2f7a4f]">Omon Dashboard</p>
                <h2 className="mt-1 text-2xl font-semibold text-[#0b1e36]">Ringkasan Keuangan Keluarga</h2>
              </div>
              <span className="inline-flex w-fit items-center gap-2 rounded-lg border border-[#dfe8e2] bg-white px-3 py-2 text-sm font-semibold text-[#53655f]">
                <FileSpreadsheet size={16} aria-hidden="true" />
                Google Sheets
              </span>
            </div>

            <div className="mt-6 grid gap-4 md:grid-cols-3">
              <MetricCard label="Pengeluaran Bulan Ini" value="Rp11.7M" trend="-4.1%" />
              <MetricCard label="Tabungan Bulan Ini" value="Rp6.7M" trend="+18.9%" />
              <MetricCard label="Dana Darurat" value="Rp24.5M" trend="+6.3%" />
            </div>

            <div className="mt-4 grid gap-4 xl:grid-cols-[1.25fr_0.75fr]">
              <div className="rounded-lg border border-[#dfe8e2] bg-white p-5">
                <div className="mb-6 flex items-center justify-between gap-4">
                  <div>
                    <p className="text-xs font-bold uppercase tracking-[0.12em] text-[#2f7a4f]">Pengeluaran bulanan</p>
                    <h3 className="mt-1 text-lg font-semibold text-[#0b1e36]">Ritme belanja keluarga</h3>
                  </div>
                  <LineChart className="text-[#2f7a4f]" size={22} aria-hidden="true" />
                </div>
                <div className="flex h-48 items-end gap-2 border-b border-l border-[#dfe8e2] px-2 pb-2">
                  {monthlyBars.map((value, index) => (
                    <div className="flex flex-1 items-end" key={`${value}-${index}`}>
                      <div
                        className="w-full rounded-t-md bg-[#2f7a4f]"
                        style={{
                          height: `${value}%`,
                          opacity: index === monthlyBars.length - 1 ? 1 : 0.45 + index * 0.05,
                        }}
                      />
                    </div>
                  ))}
                </div>
              </div>

              <div className="rounded-lg border border-[#dfe8e2] bg-white p-5">
                <p className="text-xs font-bold uppercase tracking-[0.12em] text-[#2f7a4f]">Kategori keluarga</p>
                <div className="mt-5 grid gap-4">
                  <CategoryBar label="Grocery" value="72" amount="Rp3.2M" />
                  <CategoryBar label="Makan" value="58" amount="Rp2.4M" />
                  <CategoryBar label="Transportasi" value="44" amount="Rp1.1M" />
                  <CategoryBar label="Rumah Tangga" value="36" amount="Rp820k" />
                </div>
              </div>
            </div>

            <div className="mt-4 grid gap-4 xl:grid-cols-[0.75fr_1.25fr]">
              <div className="rounded-lg border border-[#dfe8e2] bg-white p-5">
                <p className="text-xs font-bold uppercase tracking-[0.12em] text-[#2f7a4f]">Pola transaksi</p>
                <div className="mt-5 grid grid-cols-4 gap-2">
                  {heatmap.map((value, index) => (
                    <span
                      className="aspect-square rounded-md bg-[#2f7a4f]"
                      style={{ opacity: value / 100 }}
                      key={`${value}-${index}`}
                    />
                  ))}
                </div>
              </div>

              <div className="rounded-lg border border-[#dfe8e2] bg-white p-5">
                <div className="flex gap-3">
                  <span className="grid h-11 w-11 shrink-0 place-items-center rounded-lg bg-[#edf7ef] text-[#2f7a4f]">
                    <Sparkles size={22} aria-hidden="true" />
                  </span>
                  <div>
                    <p className="text-sm font-semibold text-[#0b1e36]">Insight Keluarga</p>
                    <p className="mt-2 text-sm leading-6 text-[#53655f]">
                      Pengeluaran makan naik 18%. Coba cek pola food delivery minggu ini sebelum budget makan makin melebar.
                    </p>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

function FeaturePreview() {
  return (
    <div className="rounded-lg border border-[#dfe8e2] bg-[#f7faf8] p-4 shadow-xl shadow-[#0b1e36]/8">
      <div className="grid gap-4 md:grid-cols-[1.1fr_0.9fr]">
        <div className="rounded-lg border border-[#dfe8e2] bg-white p-5">
          <p className="text-xs font-bold uppercase tracking-[0.12em] text-[#2f7a4f]">Grocery vs Food</p>
          <div className="mt-6 grid gap-4">
            <CategoryBar label="Groceries" value="64" amount="Rp2.8M" />
            <CategoryBar label="Food Delivery" value="82" amount="Rp3.6M" accent />
          </div>
          <div className="mt-6 rounded-lg bg-[#fff4ed] p-4 text-sm font-semibold leading-6 text-[#9b563b]">
            Food delivery melewati grocery selama 3 minggu berturut-turut.
          </div>
        </div>
        <div className="rounded-lg border border-[#dfe8e2] bg-white p-5">
          <p className="text-xs font-bold uppercase tracking-[0.12em] text-[#2f7a4f]">Top Spending</p>
          <div className="mt-5 grid gap-3">
            {["Dining out", "Monthly groceries", "Ride hailing", "Electricity"].map((item, index) => (
              <div className="flex items-center justify-between gap-4 rounded-lg bg-[#f7faf8] px-3 py-3 text-sm" key={item}>
                <span className="font-semibold text-[#0b1e36]">{index + 1}. {item}</span>
                <span className="font-bold text-[#2f7a4f]">Rp{[920, 780, 420, 310][index]}k</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

function MetricCard({ label, value, trend }) {
  return (
    <article className="rounded-lg border border-[#dfe8e2] bg-white p-4">
      <p className="text-sm font-semibold text-[#6b7d76]">{label}</p>
      <div className="mt-3 flex items-end justify-between gap-3">
        <p className="text-2xl font-semibold text-[#0b1e36]">{value}</p>
        <span className="inline-flex items-center gap-1 text-sm font-bold text-[#2f7a4f]">
          <TrendingUp size={15} aria-hidden="true" />
          {trend}
        </span>
      </div>
    </article>
  );
}

function CategoryBar({ label, value, amount, accent = false }) {
  return (
    <div>
      <div className="mb-2 flex items-center justify-between gap-3 text-sm">
        <span className="font-semibold text-[#334640]">{label}</span>
        <span className="font-bold text-[#0b1e36]">{amount}</span>
      </div>
      <div className="h-3 overflow-hidden rounded-full bg-[#edf3ef]">
        <div
          className={`h-full rounded-full ${accent ? "bg-[#ff8b6b]" : "bg-[#2f7a4f]"}`}
          style={{ width: `${value}%` }}
        />
      </div>
    </div>
  );
}

function BrandLogo({ size = "md", animated = false }) {
  const dimensions = size === "sm" ? "h-10 w-10" : "h-16 w-16";

  return (
    <span className={`grid ${dimensions} shrink-0 place-items-center overflow-hidden rounded-xl border border-[#dfe8e2] bg-white shadow-sm ${animated ? "omon-mascot-float" : ""}`}>
      <img className="h-full w-full object-contain p-1" src={omonLogo} alt="" />
    </span>
  );
}

export default App;
