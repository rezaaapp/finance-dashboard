from fpdf import FPDF
from datetime import datetime
import pandas as pd

class PDF(FPDF):
    def __init__(self, custom_date=None):
        super().__init__()
        if custom_date:
            self.current_date = pd.to_datetime(custom_date)  # Menggunakan tanggal yang diberikan
        else:
            self.current_date = datetime.now()  # Ambil tanggal saat ini jika tidak ada

    def header(self):
        if self.page_no() == 1:
            return  # Jangan tampilkan header di cover

        self.set_font('Arial', 'B', 16)
        self.cell(0, 10, 'Laporan Operasional Rumah Tangga', 0, 1, 'C')

        bulan = self.current_date.strftime('%B')
        tahun = self.current_date.year
        self.cell(0, 10, f'Periode: {bulan} {tahun}', 0, 1, 'C') # Gunakan bulan dan tahun dari current_date
        # self.cell(0, 10, f'Periode: December 2025', 0, 1, 'C')

        self.ln(5)

    def footer(self):
        waktu_laporan = datetime.now().strftime('%d-%m-%Y %H:%M:%S')
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        self.cell(0, 5, f'Dibuat pada: {waktu_laporan}', 0, 1, 'L')
        self.cell(0, 5, f'Halaman {self.page_no()}', 0, 0, 'R')

    def section_title(self, title):
        self.set_font('Arial', 'B', 16)
        self.set_text_color(40, 40, 120)
        self.cell(0, 12, title, 0, 1, 'L')
        self.ln(2)
        self.set_text_color(0, 0, 0)

    def subsection_title(self, title):
        self.set_font('Arial', 'B', 12)
        self.set_text_color(0, 0, 0)
        self.cell(0, 10, title, 0, 1, 'L')
        self.set_text_color(0, 0, 0)

    def add_cover_tahunan(self, tahun, nama_laporan="Laporan Keuangan Tahunan Rumah Tangga"):
        self.add_page()

        # ===== MATIKAN HEADER UNTUK COVER =====
        self.set_auto_page_break(False)

        # ===== JUDUL UTAMA =====
        self.set_y(60)
        self.set_font('Arial', 'B', 24)
        self.set_text_color(40, 40, 120)
        self.cell(0, 15, nama_laporan, 0, 1, 'C')

        # ===== SUBTITLE =====
        self.ln(5)
        self.set_font('Arial', 'B', 16)
        self.set_text_color(0, 0, 0)
        self.cell(0, 12, 'Reza & Divya Selalu Always Selamanya Bersama', 0, 1, 'C')

        # ===== PERIODE =====
        self.ln(10)
        self.set_font('Arial', 'B', 18)
        self.cell(0, 12, f'Tahun 2026', 0, 1, 'C')

        # ===== GARIS PEMBATAS =====
        self.ln(8)
        self.set_draw_color(150, 150, 150)
        self.line(40, self.get_y(), 170, self.get_y())

        # ===== INFO TAMBAHAN =====
        self.ln(20)
        self.set_font('Arial', 'I', 11)
        tanggal_generate = datetime.now().strftime('%d %B %Y')
        self.cell(0, 8, f'Diperbarui terakhir pada {tanggal_generate}', 0, 1, 'C')

        # ===== RESET STATE =====
        self.set_auto_page_break(True, margin=15)
        self.set_text_color(0, 0, 0)
