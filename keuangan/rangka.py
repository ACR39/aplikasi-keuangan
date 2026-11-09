"""Rangka aplikasi: menyiapkan sesi, memilih halaman, menggambar sidebar dan kepala, lalu memanggil halaman yang dipilih."""
import html

import streamlit as st

from keuangan.akses import COOKIE_TEMA, _jam_sesi, cek_login, js_cookie, keluar
from keuangan.aktivitas import bersihkan_sampah, halaman_aktivitas, halaman_sampah
from keuangan.anggaran import halaman_anggaran
from keuangan.bantu import atur, pindah_halaman
from keuangan.barang import halaman_barang
from keuangan.toko import halaman_toko
from keuangan.belanja import halaman_belanja
from keuangan.beranda import halaman_beranda
from keuangan.cadangan import halaman_cadangan, halaman_pulih
from keuangan.ekspor import halaman_ekspor, halaman_impor
from keuangan.inti import CSS_GELAP, CSS_TAMBAH_GELAP, D, adalah_admin, cfg_github, data_kosong, hanya_lihat
from keuangan.laporan import halaman_laporan
from keuangan.master import halaman_dompet, halaman_kategori
from keuangan.penyimpanan import muat_ke_sesi
from keuangan.pwa import pasang_pwa
from keuangan.tabungan import halaman_tabungan
from keuangan.tagihan import halaman_tagihan
from keuangan.tampilan import halaman_tampilan
from keuangan.transaksi import halaman_catat, halaman_transaksi
from keuangan.utang import halaman_utang
from keuangan.inti import pasang_css

UTAMA = ["Catat transaksi", "Daftar belanja", "Daftar transaksi", "Riwayat aktivitas"]
PANTAU = ["Anggaran", "Tagihan berulang", "Target tabungan", "Utang-piutang", "Laporan"]
EDIT_SAJA = ("Catat transaksi",)
MASTER = ["Dompet", "Kategori", "Cadangan dan pulihkan"]
IKON = {"Beranda": "home", "Catat transaksi": "add_circle", "Daftar transaksi": "receipt_long", "Barang dan produk": "inventory_2", "Toko dan tempat beli": "storefront", "Daftar belanja": "shopping_cart", "Riwayat aktivitas": "history",
        "Tempat sampah": "delete", "Anggaran": "donut_small", "Tagihan berulang": "event_repeat", "Target tabungan": "savings",
        "Utang-piutang": "handshake", "Laporan": "bar_chart", "Tampilan": "tune", "Ekspor dan impor": "import_export",
        "Dompet": "account_balance_wallet", "Kategori": "sell", "Cadangan dan pulihkan": "backup"}
LOGO = ('<svg width="38" height="38" viewBox="0 0 38 38" xmlns="http://www.w3.org/2000/svg">'
        '<defs><linearGradient id="g" x1="0" y1="0" x2="1" y2="1">'
        '<stop offset="0" stop-color="#34a874"/><stop offset="1" stop-color="#1f6b49"/></linearGradient></defs>'
        '<rect width="38" height="38" rx="10" fill="url(#g)"/>'
        '<circle cx="19" cy="19" r="9" fill="none" stroke="#fff" stroke-width="2"/>'
        '<path d="M19 13.5v11M15.5 16.5c0-1.3 1.5-2 3.5-2s3.5.8 3.5 2.1c0 3.2-7 1.6-7 4.8 0 1.3 1.6 2.1 3.5 2.1s3.5-.8 3.5-2.1" '
        'fill="none" stroke="#fff" stroke-width="1.6" stroke-linecap="round"/></svg>')
DESKRIPSI = {
    "Beranda": "Ringkasan saldo, pemasukan dan pengeluaran per minggu, bulan, tahun, atau tanggal custom, plus hal yang perlu perhatian dan grafik.",
    "Catat transaksi": "Catat pemasukan, pengeluaran, atau transfer antar dompet dalam beberapa ketukan.",
    "Daftar transaksi": "Cari dan saring semua transaksi, lalu ubah atau hapus kalau ada yang salah.",
    "Daftar belanja": "Rencanakan belanja, lihat toko termurah, centang saat membeli, lalu catat jadi satu struk.",
    "Toko dan tempat beli": "Daftar toko atau tempat beli beserta lokasinya. Saat mencatat, toko bisa dipilih.",
    "Barang dan produk": "Daftar barang per kategori atau sub kategori. Saat mencatat, barang bisa dipilih sesuai kategorinya.",
    "Riwayat aktivitas": "Semua perubahan data yang tercatat otomatis, lengkap dengan siapa dan kapan.",
    "Tempat sampah": "Transaksi yang dihapus disimpan 30 hari di sini, bisa dipulihkan sebelum hilang permanen.",
    "Anggaran": "Batas pengeluaran per kategori tiap bulan, dengan peringatan saat hampir atau sudah terlewati.",
    "Tagihan berulang": "Listrik, internet, langganan: pantau jatuh tempo dan catat pembayaran jadi pengeluaran.",
    "Target tabungan": "Tabungan dengan target dan tenggat, lengkap dengan perkiraan setoran per bulan.",
    "Utang-piutang": "Catat utang dan piutang beserta cicilannya. Bisa ikut tercatat di saldo dompet.",
    "Laporan": "Statistik bulanan, tren 12 bulan, arus tiap dompet, serta belanja per barang dan per toko.",
    "Tampilan": "Pilih bagian Beranda yang ditampilkan.",
    "Ekspor dan impor": "Unduh data ke Excel atau CSV, atau tambah banyak transaksi sekaligus dari file.",
    "Dompet": "Tempat uang disimpan beserta saldo awalnya. Saldo sekarang dihitung otomatis.",
    "Kategori": "Kelompok pemasukan dan pengeluaran. Ubah nama atau gabungkan yang ganda.",
    "Cadangan dan pulihkan": "Unduh cadangan data, muat dari berkas, atau pulihkan ke versi sebelumnya.",
}


def menu_utama() -> list:
    return [h for h in UTAMA if not (hanya_lihat() and h in EDIT_SAJA)]


def siapkan_sesi():
    """Login, muat data ke sesi, dan tema."""
    cek_login()
    if st.session_state.get("pasang_cookie"):
        js_cookie(st.session_state.pop("pasang_cookie"), int(_jam_sesi() * 3600))
    if "data" not in st.session_state:
        try:
            muat_ke_sesi()
        except Exception as ex:
            st.error(f"Data tidak bisa dimuat: {ex}")
            st.stop()
        bersihkan_sampah()
    for kunci, awal in data_kosong().items():
        D.setdefault(kunci, awal)
    if "gelap" not in st.session_state:
        try:
            st.session_state.gelap = st.context.cookies.get(COOKIE_TEMA, "") == "gelap"
        except Exception:
            st.session_state.gelap = False
    if st.session_state.gelap:
        st.markdown(CSS_GELAP + CSS_TAMBAH_GELAP, unsafe_allow_html=True)


def peringatan_uji():
    if not cfg_github():
        st.warning("Mode uji coba: data disimpan di file lokal dan bisa hilang saat aplikasi dimulai ulang. "
                   "Isi pengaturan GitHub (lihat README) agar data permanen.")


def pilih_halaman():
    PENGATURAN = ["Tampilan", "Barang dan produk", "Toko dan tempat beli", "Tempat sampah", "Ekspor dan impor"] + (MASTER if adalah_admin() else [])
    HALAMAN = ["Beranda"] + menu_utama() + PANTAU + PENGATURAN
    if st.session_state.get("halaman") not in HALAMAN:
        st.session_state.halaman = "Beranda"
    return PENGATURAN, st.session_state.halaman


def tampilkan_sidebar(halaman, PENGATURAN):
    with st.sidebar:
        st.markdown(f'<div class="brand">{LOGO}<div><div class="b1">Pelacak Keuangan</div>'
                    '<div class="b2">Ke mana uangku?</div></div></div>', unsafe_allow_html=True)

        def tombol_nav(h):
            st.button(h, key=f"nav_{h}", width="stretch", icon=f":material/{IKON[h]}:",
                      type="primary" if h == halaman else "secondary", on_click=pindah_halaman, args=(h,))

        st.markdown('<div class="grup">UTAMA</div>', unsafe_allow_html=True)
        tombol_nav("Beranda")
        st.markdown('<div class="grup">MENU</div>', unsafe_allow_html=True)
        with st.expander("Transaksi", icon=":material/payments:", expanded=halaman in menu_utama()):
            for h in menu_utama():
                tombol_nav(h)
        with st.expander("Pantau", icon=":material/monitoring:", expanded=halaman in PANTAU):
            for h in PANTAU:
                tombol_nav(h)
        with st.expander("Pengaturan", icon=":material/settings:", expanded=halaman in PENGATURAN):
            for h in PENGATURAN:
                tombol_nav(h)
        st.markdown('<div class="sp"></div>', unsafe_allow_html=True)
        st.toggle("Mode gelap", key="gelap", on_change=atur, args=("tema_ubah", True))
        if st.session_state.pop("tema_ubah", False):
            js_cookie("gelap" if st.session_state.gelap else "terang", 31536000, COOKIE_TEMA)
        if st.button("Muat ulang", key="nav_muat", width="stretch", icon=":material/refresh:",
                     help="Ambil data terbaru dari penyimpanan"):
            muat_ke_sesi()
            st.rerun()
        if cfg_github():
            st.caption(f"Data: {cfg_github()['repo']}")
        if hanya_lihat():
            st.caption("🔒 Akun ini hanya bisa melihat.")
        us = st.session_state.get("user")
        if us:
            st.markdown(f'<div class="pengguna sb"><div class="av">{html.escape(us["nama"][:1].upper())}</div><div>'
                        f'<div class="nm">{html.escape(us["nama"])}</div>'
                        f'<div class="pr">{html.escape(us["peran"])}</div></div></div>', unsafe_allow_html=True)
            st.button("Keluar", key="nav_keluar", width="stretch", icon=":material/logout:", on_click=keluar)


def tampilkan_kepala(halaman, PENGATURAN):
    grup = ("PENGATURAN" if halaman in PENGATURAN else "RINGKASAN" if halaman == "Beranda"
            else "PANTAU" if halaman in PANTAU else "TRANSAKSI")
    st.markdown(f'<div class="kepala"><div><div class="eyebrow">{grup}</div>'
                f'<div class="judul-hal">{html.escape(halaman)}</div>'
                f'<div class="desk">{html.escape(DESKRIPSI.get(halaman, ""))}</div></div></div>', unsafe_allow_html=True)


def tampilkan_halaman(halaman):
    if halaman == "Beranda":
        halaman_beranda()
    elif halaman == "Catat transaksi":
        halaman_catat()
    elif halaman == "Daftar transaksi":
        halaman_transaksi()
    elif halaman == "Barang dan produk":
        halaman_barang()
    elif halaman == "Toko dan tempat beli":
        halaman_toko()
    elif halaman == "Daftar belanja":
        halaman_belanja()
    elif halaman == "Riwayat aktivitas":
        halaman_aktivitas()
    elif halaman == "Tempat sampah":
        halaman_sampah()
    elif halaman == "Anggaran":
        halaman_anggaran()
    elif halaman == "Tagihan berulang":
        halaman_tagihan()
    elif halaman == "Target tabungan":
        halaman_tabungan()
    elif halaman == "Utang-piutang":
        halaman_utang()
    elif halaman == "Laporan":
        halaman_laporan()
    elif halaman == "Tampilan":
        halaman_tampilan()
    elif halaman == "Ekspor dan impor":
        if hanya_lihat():
            halaman_ekspor()
        else:
            t1, t2 = st.tabs(["Ekspor", "Impor"])
            with t1:
                halaman_ekspor()
            with t2:
                halaman_impor()
    elif adalah_admin() and halaman == "Dompet":
        halaman_dompet()
    elif adalah_admin() and halaman == "Kategori":
        halaman_kategori()
    elif adalah_admin() and halaman == "Cadangan dan pulihkan":
        t1, t2 = st.tabs(["Cadangan", "Titik pulih"])
        with t1:
            halaman_cadangan()
        with t2:
            halaman_pulih()


def jalankan():
    pasang_css()
    pasang_pwa()
    siapkan_sesi()
    peringatan_uji()
    PENGATURAN, halaman = pilih_halaman()
    tampilkan_sidebar(halaman, PENGATURAN)
    tampilkan_kepala(halaman, PENGATURAN)
    tampilkan_halaman(halaman)
