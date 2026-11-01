import streamlit as st
import pandas as pd
from github import Github, GithubException
from io import StringIO
from datetime import date

st.set_page_config(page_title="Pencatat Keuangan", page_icon="💰", layout="wide")
st.title("💰 Aplikasi Pencatat Keuangan Pribadi")

# Mengambil kredensial dari Streamlit Secrets
try:
    GITHUB_TOKEN = st.secrets["GITHUB_TOKEN"]
    DATA_REPO_NAME = st.secrets["DATA_REPO"]  # Format: "username/nama-repo-data"
except KeyError:
    st.error("⚠️ Konfigurasi Secrets belum lengkap! Pastikan GITHUB_TOKEN dan DATA_REPO sudah diatur di Streamlit Secrets.")
    st.stop()

FILE_PATH = "data_keuangan.csv"

@st.cache_resource
def get_repo():
    g = Github(GITHUB_TOKEN)
    return g.get_repo(DATA_REPO_NAME)

def load_data():
    repo = get_repo()
    try:
        file_content = repo.get_contents(FILE_PATH)
        csv_string = file_content.decoded_content.decode("utf-8")
        df = pd.read_csv(StringIO(csv_string))
        return df, file_content.sha
    except GithubException as e:
        if e.status == 404:
            # Jika file belum ada di repo private, buat DataFrame kosong
            df = pd.DataFrame(columns=["Tanggal", "Tipe", "Kategori", "Jumlah", "Keterangan"])
            return df, None
        else:
            st.error(f"Gagal mengambil data dari GitHub: {e}")
            st.stop()

def save_data(df, sha=None, pesan_commit="Update data keuangan"):
    repo = get_repo()
    csv_content = df.to_csv(index=False)
    if sha:
        repo.update_file(
            path=FILE_PATH,
            message=pesan_commit,
            content=csv_content,
            sha=sha
        )
    else:
        repo.create_file(
            path=FILE_PATH,
            message="Inisialisasi file data keuangan",
            content=csv_content
        )

# Muat data saat ini dari repo private
df, file_sha = load_data()

# Sidebar untuk Input Transaksi
st.sidebar.header("➕ Tambah Transaksi Baru")
with st.sidebar.form("form_transaksi", clear_on_submit=True):
    tanggal = st.date_input("Tanggal", date.today())
    tipe = st.selectbox("Tipe Transaksi", ["Pemasukan", "Pengeluaran"])
    kategori = st.selectbox(
        "Kategori", 
        ["Gaji", "Makanan & Minuman", "Transportasi", "Belanja", "Tagihan", "Hiburan", "Lainnya"]
    )
    jumlah = st.number_input("Jumlah (Rp)", min_value=0, step=1000)
    keterangan = st.text_input("Keterangan (Opsional)")
    submit = st.form_submit_button("Simpan ke GitHub")

    if submit:
        if jumlah > 0:
            new_row = pd.DataFrame({
                "Tanggal": [str(tanggal)],
                "Tipe": [tipe],
                "Kategori": [kategori],
                "Jumlah": [jumlah],
                "Keterangan": [keterangan]
            })
            df = pd.concat([df, new_row], ignore_index=True)
            with st.spinner("Menyimpan ke repositori private..."):
                save_data(df, file_sha, f"Tambah {tipe}: {kategori} - Rp{jumlah}")
            st.sidebar.success("Tersimpan permanen di GitHub Private Repo!")
            st.rerun()
        else:
            st.sidebar.warning("Masukkan jumlah lebih dari 0.")

# Ringkasan Keuangan
total_pemasukan = df[df["Tipe"] == "Pemasukan"]["Jumlah"].sum() if not df.empty else 0
total_pengeluaran = df[df["Tipe"] == "Pengeluaran"]["Jumlah"].sum() if not df.empty else 0
saldo_akhir = total_pemasukan - total_pengeluaran

col1, col2, col3 = st.columns(3)
col1.metric("Total Pemasukan", f"Rp {total_pemasukan:,.0f}")
col2.metric("Total Pengeluaran", f"Rp {total_pengeluaran:,.0f}")
col3.metric("Saldo Saat Ini", f"Rp {saldo_akhir:,.0f}")

st.divider()

# Tabel Riwayat & Visualisasi
col_kiri, col_kanan = st.columns([2, 1])

with col_kiri:
    st.subheader("📋 Riwayat Transaksi")
    if not df.empty:
        st.dataframe(df.sort_values(by="Tanggal", ascending=False), use_container_width=True)
    else:
        st.info("Belum ada data transaksi di repositori private.")

with col_kanan:
    st.subheader("📊 Pengeluaran per Kategori")
    df_out = df[df["Tipe"] == "Pengeluaran"]
    if not df_out.empty:
        kategori_sum = df_out.groupby("Kategori")["Jumlah"].sum()
        st.bar_chart(kategori_sum)
    else:
        st.info("Belum ada data pengeluaran untuk ditampilkan.")