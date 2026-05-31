## Method

### Target Architecture Overview

Target production architecture memisahkan sistem menjadi 6 bounded contexts:

1. **Web Dashboard**
   - React + Vite dashboard untuk analytics, chart, configuration, dan AI insight.
   - Tetap deploy di Vercel.

2. **Backend API**
   - FastAPI sebagai public API layer.
   - Menangani auth, workspace, dashboard query, configuration, classification status, dan admin endpoint.
   - FastAPI project saat ini sudah menjadi backend utama dan deploy diarahkan via Docker di Render.  [oai_citation:0‡GitHub](https://raw.githubusercontent.com/rezaaapp/finance-dashboard/main/PROJECT_OPERATIONS_GUIDE.md)

3. **Data Ingestion Service**
   - Membaca Google Sheets tahunan.
   - Normalisasi transaksi.
   - Menyimpan hasil normalized transaction ke PostgreSQL.
   - Google Sheets tetap menjadi input source, tapi bukan lagi sumber query analytics langsung.

4. **AI Classification Service**
   - Mengklasifikasikan transaksi ke `Needs`, `Wants`, `Savings`.
   - Menghasilkan structured JSON output dari Gemini.
   - Memakai schema validation agar output model konsisten.
   - Gemini API mendukung structured output berbasis JSON Schema untuk classification dan ekstraksi data terstruktur.  [oai_citation:1‡Google AI for Developers](https://ai.google.dev/gemini-api/docs/structured-output?utm_source=chatgpt.com)

5. **Analytics Service**
   - Membaca transaksi yang sudah tersimpan di PostgreSQL.
   - Menghasilkan aggregate: monthly allocation, source dana analytics, category trend, budget forecast, anomaly, dan smart alerts.
   - Menghindari kalkulasi berat langsung dari frontend.

6. **Background Worker**
   - Menjalankan sync Google Sheets, classification batch, refresh materialized analytics, dan retry job.
   - Untuk MVP production, gunakan worker process terpisah.
   - FastAPI BackgroundTasks cocok untuk pekerjaan ringan setelah response dikirim, tetapi job classification/sync yang butuh retry, status, dan durability sebaiknya dipisahkan ke worker queue.  [oai_citation:2‡FastAPI](https://fastapi.tiangolo.com/tutorial/background-tasks/?utm_source=chatgpt.com)

### Proposed Production Data Flow

```plantuml
@startuml
actor User

rectangle "Vercel" {
  component "React Dashboard" as Web
}

rectangle "Render / Cloud Runtime" {
  component "FastAPI API" as API
  component "Background Worker" as Worker
  component "AI Classification Service" as AI
  component "Analytics Service" as Analytics
}

database "PostgreSQL" as DB
cloud "Google Sheets" as Sheets
cloud "Gemini API" as Gemini

User --> Web
Web --> API : REST API + JWT
API --> DB : query dashboard/config/auth
API --> Worker : enqueue sync/classify job
Worker --> Sheets : read spreadsheet rows
Worker --> DB : upsert raw + normalized transactions
Worker --> AI : classify unclassified rows
AI --> Gemini : structured classification request
AI --> DB : save labels + confidence + model metadata
Analytics --> DB : aggregate classified transactions
API --> Analytics : get dashboard metrics
Web <-- API : analytics response
@enduml