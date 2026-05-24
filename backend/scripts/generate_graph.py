import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import seaborn as sns
import pandas as pd
from matplotlib.ticker import StrMethodFormatter
from wordcloud import WordCloud


def save_bar_graph(data, filename, ylabel, title, color='skyblue', legend=None, stacked=False):
    plt.figure(figsize=(8, 4) if not stacked else (10, 6))
    if stacked:
        data.plot(kind='bar', stacked=True, legend=legend is not None)
    else:
        data.plot(kind='bar', color=color, legend=legend is not None)
    plt.ylabel(ylabel)
    plt.title(title)
    plt.gca().yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, p: f'Rp {int(x):,}'.replace(',', '.')))
    if legend:
        plt.legend(title=legend)
    plt.tight_layout()
    plt.savefig(filename)
    plt.close()
    
def save_heatmap(data, filename):
    plt.figure(figsize=(10, 8))

    # Membuat heatmap
    sns.heatmap(data, annot=False, fmt=".0f", cmap='YlGnBu', 
                cbar_kws={'label': 'Total Pengeluaran (Rp)', 
                           'format': mticker.FuncFormatter(lambda x, _: f'Rp {int(x):,}'.replace(',', '.'))})

    # plt.title('Heatmap Pengeluaran per Kategori per Bulan')
    plt.xlabel('Kategori',fontweight='bold',fontsize=12)
    plt.ylabel('Bulan',fontweight='bold',fontsize=12)

    # Menyimpan heatmap sebagai gambar
    plt.savefig(filename, bbox_inches='tight')
    plt.close()
    
def save_correlation_graph(data, filename):
    """Simpan grafik korelasi pengeluaran makanan dan grocery."""
    plt.figure(figsize=(10, 6))

    # Plotting pengeluaran makanan dan grocery
    plt.plot(data.index, data['Makanan'], label='Pengeluaran Makanan', marker='o')
    plt.plot(data.index, data['Grocery'], label='Pengeluaran Grocery', marker='o')

    plt.title('Korelasi Pengeluaran Makanan dan Grocery per Bulan')
    plt.xlabel('Bulan', fontweight='bold', fontsize=12)
    plt.ylabel('Total Pengeluaran (Rp)', fontweight='bold', fontsize=12)
    plt.legend()
    plt.grid()
    plt.xticks(rotation=45)  # Memutar label bulan agar lebih mudah dibaca

    # Simpan grafik sebagai file PNG
    plt.tight_layout()
    plt.savefig(filename)  # Menyimpan ke path yang diberikan
    plt.show()  # Tampilkan grafik
    plt.close()

def save_persentase_grocery_vs_makanan(df, output_path):
    if df.empty:
        return

    ax = df.plot(
        kind='bar',
        stacked=True,
        figsize=(10, 5)
    )

    ax.set_title('Persentase Grocery vs Makanan per Bulan')
    ax.set_xlabel('Bulan')
    ax.set_ylabel('Persentase (%)')
    ax.legend(title='Kategori')

    ax.set_ylim(0, 100)

    plt.tight_layout()
    plt.savefig(output_path)
    plt.close()

def save_top_spending_kategori_graph(
    df_top_spending: pd.DataFrame,
    output_path: str,
    title: str = "Distribusi Kategori Top Spending",
):
    """
    Grafik bar total pengeluaran per kategori
    (Top N transaksi bulan berjalan)
    """

    if df_top_spending.empty:
        raise ValueError("df_top_spending kosong, grafik tidak dapat dibuat")

    kategori_sum = (
        df_top_spending
        .groupby('Kategori')['Harga']
        .sum()
        .sort_values(ascending=False)
    )

    plt.figure(figsize=(8, 5))
    bars = plt.bar(kategori_sum.index, kategori_sum.values)

    plt.title(title)
    plt.ylabel("Total Pengeluaran (Rp)")
    plt.xticks(rotation=30, ha='right')

    # === Format sumbu Y ke Rupiah (tanpa custom formatter) ===
    plt.gca().yaxis.set_major_formatter(
        StrMethodFormatter("Rp {x:,.0f}")
    )

    # === Label nilai di atas bar ===
    for bar in bars:
        value = bar.get_height()
        plt.text(
            bar.get_x() + bar.get_width() / 2,
            value,
            f"Rp {value:,.0f}",
            ha='center',
            va='bottom',
            fontsize=9
        )

    plt.tight_layout()
    plt.savefig(output_path)
    plt.close()

def save_wordcloud_kategori_weighted(
    df_pengeluaran,
    output_path,
    title="Word Cloud Kategori (Bobot Rupiah)"
):
    """
    Membuat word cloud kategori berbobot total rupiah (Harga).
    Semakin besar total rupiah suatu kategori, semakin besar teksnya.
    """

    # Validasi kolom wajib
    required_cols = {'Kategori', 'Harga'}
    if not required_cols.issubset(df_pengeluaran.columns):
        raise ValueError("DataFrame harus memiliki kolom 'Kategori' dan 'Harga'")

    # Group by kategori → total rupiah
    kategori_weight = (
        df_pengeluaran
        .dropna(subset=['Kategori', 'Harga'])
        .groupby('Kategori')['Harga']
        .sum()
        .to_dict()
    )

    # Jika tidak ada data, skip
    if not kategori_weight:
        return

    wordcloud = WordCloud(
        width=1200,
        height=600,
        background_color="white",
        colormap="viridis",
        max_words=50,
        prefer_horizontal=0.9
    ).generate_from_frequencies(kategori_weight)

    plt.figure(figsize=(12, 6))
    plt.imshow(wordcloud, interpolation="bilinear")
    plt.axis("off")
    plt.title(title)
    plt.tight_layout()
    plt.savefig(output_path, dpi=300)
    plt.close()

def save_wordcloud_kategori_spending_vs_saving(
    df_pengeluaran,
    df_saving,
    output_path,
    title="Word Cloud Kategori (Spending vs Saving)"
):
    """
    Word cloud kategori berbobot rupiah:
    - Menggabungkan Spending & Saving
    - Ukuran kata = total nominal
    - Dengan border/frame agar rapi di PDF
    """

    # =========================
    # PREPARE SPENDING
    # =========================
    spending = (
        df_pengeluaran
        .dropna(subset=['Kategori', 'Harga'])
        .groupby('Kategori')['Harga']
        .sum()
        .rename(lambda x: f"SPENDING_{x}")
    )

    # =========================
    # PREPARE SAVING
    # =========================
    saving = (
        df_saving
        .dropna(subset=['Kategori', 'Harga'])
        .groupby('Kategori')['Harga']
        .sum()
        .rename(lambda x: f"SAVING_{x}")
    )

    # =========================
    # COMBINE
    # =========================
    combined_series = pd.concat([spending, saving])

    if combined_series.empty:
        return

    kategori_weight = combined_series.to_dict()

    # =========================
    # WORD CLOUD
    # =========================
    wordcloud = WordCloud(
        width=1400,
        height=700,
        background_color="white",
        colormap="tab10",
        max_words=60,
        prefer_horizontal=0.9,
        random_state=42
    ).generate_from_frequencies(kategori_weight)

    # =========================
    # PLOT + BORDER
    # =========================
    fig, ax = plt.subplots(figsize=(14, 7))

    ax.imshow(wordcloud, interpolation="bilinear")
    ax.set_title(title, fontsize=14, pad=12)
    ax.axis("off")

    # Border / Frame
    for spine in ax.spines.values():
        spine.set_visible(True)
        spine.set_linewidth(50)
        spine.set_edgecolor("black")

    plt.tight_layout()
    plt.savefig(output_path, dpi=300)
    plt.close()

def save_pie_chart_spending(
    df_pengeluaran,
    output_path,
    title="Distribusi Pengeluaran per Kategori (%)"
):
    """
    Simpan pie chart persentase pengeluaran per kategori.
    """

    # Validasi kolom wajib
    required_cols = {'Kategori', 'Harga'}
    if not required_cols.issubset(df_pengeluaran.columns):
        raise ValueError("DataFrame harus memiliki kolom 'Kategori' dan 'Harga'")

    # Group by kategori → total rupiah
    kategori_sum = (
        df_pengeluaran
        .dropna(subset=['Kategori', 'Harga'])
        .groupby('Kategori')['Harga']
        .sum()
    )

    if kategori_sum.empty:
        return

    plt.figure(figsize=(8, 8))
    plt.pie(
        kategori_sum.values,
        labels=kategori_sum.index,
        autopct='%1.1f%%',     # ✅ tampilkan persentase
        startangle=140,
        wedgeprops={'edgecolor': 'white'}  # biar lebih jelas
    )

    plt.title(title)
    plt.axis('equal')  # pie jadi bulat sempurna
    plt.tight_layout()
    plt.savefig(output_path)
    plt.close()
