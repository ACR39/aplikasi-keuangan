"""Rangka aplikasi: menyiapkan sesi, memilih halaman, menggambar sidebar dan kepala, lalu memanggil halaman yang dipilih."""
import html

import streamlit as st

from keuangan.akses import COOKIE_TEMA, _jam_sesi, cek_login, js_cookie, keluar
from keuangan.aktivitas import bersihkan_sampah, halaman_aktivitas, halaman_sampah
from keuangan.anggaran import halaman_anggaran
from keuangan.bantu import atur, pindah_halaman
from keuangan.barang import halaman_barang
from keuangan.toko import halaman_toko
from keuangan.daring import halaman_platform
from keuangan.belanja import halaman_belanja
from keuangan.beranda import halaman_beranda
from keuangan.cari import halaman_cari
from keuangan.cadangan import cadangan_otomatis, halaman_cadangan, halaman_pulih
from keuangan.aplikasi_lama import halaman_aplikasi_lama
from keuangan.ekspor import halaman_ekspor, halaman_impor
from keuangan.inti import CSS_GELAP, CSS_RAPI, CSS_RAPI_GELAP, CSS_RAPI_TERANG, CSS_TAMBAH_GELAP, D, adalah_admin, cfg_github, data_kosong, hanya_lihat
from keuangan.laporan import halaman_laporan
from keuangan.ocr import halaman_mesin
from keuangan.master import halaman_dompet, halaman_kategori
from keuangan.penyimpanan import muat_ke_sesi
from keuangan.pwa import pasang_pwa, pasang_sambung_ulang
from keuangan.tabungan import halaman_tabungan
from keuangan.tagihan import catat_otomatis, halaman_tagihan
from keuangan.tampilan import halaman_tampilan
from keuangan.transaksi import halaman_catat, halaman_transaksi
from keuangan.utang import halaman_utang
from keuangan.inti import pasang_css

UTAMA = ["Pencarian", "Catat transaksi", "Daftar belanja", "Daftar transaksi"]
PANTAU = ["Anggaran", "Transaksi berulang", "Target tabungan", "Utang-piutang", "Laporan"]
PENGATURAN_MENU = ["Tampilan", "Data master", "AI dan baca struk", "Perawatan data", "Data dan cadangan"]
EDIT_SAJA = ("Catat transaksi",)
# Halaman gabungan: nama halaman -> [(label bagian, nama halaman lama, hanya admin)]. Nama lama tetap dikenali sebagai pintasan (lihat ALIAS).
GABUNGAN = {
    "Data master": [("Barang dan produk", "Barang dan produk", False), ("Toko dan tempat beli", "Toko dan tempat beli", False), ("Jenis toko", "Jenis toko", False),
                    ("Platform beli online", "Platform beli online", False), ("Dompet", "Dompet", True), ("Kategori", "Kategori", True)],
    "AI dan baca struk": [("Privasi AI", "Privasi AI", False), ("Mesin baca struk", "Mesin baca struk", False)],
    "Laporan": [("Statistik", "Laporan", False), ("Tanya dan ringkasan AI", "Asisten AI", False)],
    "Perawatan data": [("Riwayat aktivitas", "Riwayat aktivitas", False), ("Tempat sampah", "Tempat sampah", False), ("Pemeriksa data", "Pemeriksa data", False)],
    "Data dan cadangan": [("Ekspor dan impor", "Ekspor dan impor", False), ("Cadangan dan pulihkan", "Cadangan dan pulihkan", True)],
}
ALIAS = {lama: (hal, label) for hal, bagian in GABUNGAN.items() for label, lama, _ in bagian if lama != hal}
IKON = {"Beranda": "home", "Pencarian": "search", "Catat transaksi": "add_circle", "Daftar transaksi": "receipt_long", "Barang dan produk": "inventory_2", "Toko dan tempat beli": "storefront", "Platform beli online": "delivery_dining", "Asisten AI": "auto_awesome", "Privasi AI": "shield", "Daftar belanja": "shopping_cart", "Riwayat aktivitas": "history",
        "Data master": "database", "Jenis toko": "category", "AI dan baca struk": "document_scanner", "Perawatan data": "build", "Data dan cadangan": "backup",
        "Tempat sampah": "delete", "Anggaran": "donut_small", "Transaksi berulang": "event_repeat", "Target tabungan": "savings",
        "Utang-piutang": "handshake", "Laporan": "bar_chart", "Tampilan": "tune", "Ekspor dan impor": "import_export", "Mesin baca struk": "document_scanner", "Pemeriksa data": "fact_check",
        "Dompet": "account_balance_wallet", "Kategori": "sell", "Cadangan dan pulihkan": "backup"}
DESKRIPSI = {
    "Jenis toko": "Tambah, ubah, atau hapus jenis toko (Minimarket, SPBU, Bengkel, dan lain-lain) untuk mengelompokkan daftar toko.",
    "Data master": "Daftar yang diatur sekali lalu dipakai terus: barang, toko, platform beli online, dompet, dan kategori.",
    "AI dan baca struk": "Semua pengaturan AI di satu tempat: fitur dan privasi, serta mesin pembaca foto struk.",
    "Perawatan data": "Riwayat perubahan, transaksi terhapus yang bisa dipulihkan, dan pemeriksa data yang janggal.",
    "Data dan cadangan": "Unduh atau impor data, simpan cadangan, dan pulihkan ke versi sebelumnya.",
    "Pencarian": "Satu kotak untuk mencari transaksi, barang, toko, daftar belanja, utang-piutang, dan tagihan.",
    "Beranda": "Ringkasan saldo, pemasukan dan pengeluaran per minggu, bulan, tahun, atau tanggal custom, plus hal yang perlu perhatian dan grafik.",
    "Catat transaksi": "Catat pemasukan, pengeluaran, atau transfer antar dompet dalam beberapa ketukan.",
    "Daftar transaksi": "Cari dan saring semua transaksi, lalu ubah atau hapus kalau ada yang salah.",
    "Daftar belanja": "Rencanakan belanja, lihat toko termurah, centang saat membeli, lalu catat jadi satu struk.",
    "Toko dan tempat beli": "Daftar toko atau tempat beli beserta lokasinya. Saat mencatat, toko bisa dipilih.",
    "Platform beli online": "Daftar aplikasi tempat beli online (GoFood, ShopeeFood, dan lainnya) yang bisa Anda atur sendiri. Saat mencatat, platform bisa dipilih.",
    "Asisten AI": "Tanya data dengan bahasa biasa dan minta ringkasan bulanan tertulis. Perhitungan dikerjakan di server ini; AI tidak melihat transaksimu.",
    "Privasi AI": "Nyalakan fitur AI satu per satu, lihat apa yang dikirim dan tidak dikirim ke penyedia, dan riwayat kiriman. Semua mati secara bawaan.",
    "Barang dan produk": "Daftar barang per kategori atau sub kategori. Saat mencatat, barang bisa dipilih sesuai kategorinya.",
    "Riwayat aktivitas": "Semua perubahan data yang tercatat otomatis, lengkap dengan siapa dan kapan.",
    "Tempat sampah": "Transaksi yang dihapus disimpan 30 hari di sini, bisa dipulihkan sebelum hilang permanen.",
    "Anggaran": "Batas pengeluaran per kategori tiap bulan, dengan peringatan saat hampir atau sudah terlewati.",
    "Transaksi berulang": "Listrik, internet, langganan, gaji: pantau jatuh tempo, catat dengan satu ketukan, atau catat otomatis.",
    "Target tabungan": "Tabungan dengan target dan tenggat, lengkap dengan perkiraan setoran per bulan.",
    "Utang-piutang": "Catat utang dan piutang beserta cicilannya. Bisa ikut tercatat di saldo dompet.",
    "Laporan": "Statistik bulanan, tren 12 bulan, arus tiap dompet, belanja per barang dan toko, serta tanya data dan ringkasan bulanan dengan AI.",
    "Tampilan": "Pilih bagian Beranda yang ditampilkan.",
    "Pemeriksa data": "Cari transaksi yang janggal (barang kosong, kategori tak cocok, jumlah tak sinkron) dan perbaiki dengan satu ketukan.",
    "Mesin baca struk": "Lihat mesin pembaca foto struk yang aktif, atur urutan percobaannya, dan uji apakah tiap mesin berfungsi.",
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
            pilihan = st.context.cookies.get(COOKIE_TEMA, "")
            # belum pernah memilih: ikuti tema perangkat
            st.session_state.gelap = (pilihan == "gelap") if pilihan else (st.context.theme.type == "dark")
        except Exception:
            st.session_state.gelap = False
    from keuangan.pin import cek_pin
    cek_pin()
    if st.session_state.gelap:
        st.markdown(CSS_GELAP + CSS_TAMBAH_GELAP + CSS_RAPI + CSS_RAPI_GELAP, unsafe_allow_html=True)
    else:
        st.markdown(CSS_RAPI + CSS_RAPI_TERANG, unsafe_allow_html=True)


def peringatan_uji():
    if not cfg_github():
        st.warning("Mode uji coba: data disimpan di file lokal dan bisa hilang saat aplikasi dimulai ulang. "
                   "Isi pengaturan GitHub (lihat README) agar data permanen.")


def pilih_halaman():
    PENGATURAN = list(PENGATURAN_MENU)
    HALAMAN = ["Beranda"] + menu_utama() + PANTAU + PENGATURAN
    if "halaman" not in st.session_state:  # sesi baru (misalnya setelah muat ulang): kembali ke halaman terakhir dari alamat
        try:
            h, sb = st.query_params.get("h", ""), st.query_params.get("s", "")
            if h in HALAMAN:
                st.session_state.halaman = h
                if sb and h in GABUNGAN:
                    st.session_state[f"sub_{h}"] = sb
        except Exception:
            pass
    lama = st.session_state.get("halaman")
    if lama in ALIAS:  # nama halaman lama (pintasan dari tombol atau tautan): buka halaman gabungannya pada bagian yang sesuai
        hal, label = ALIAS[lama]
        st.session_state.halaman = hal
        st.session_state[f"sub_{hal}"] = label
    if st.session_state.get("halaman") not in HALAMAN:
        st.session_state.halaman = "Beranda"
    return PENGATURAN, st.session_state.halaman


def tampilkan_sidebar(halaman, PENGATURAN):
    with st.sidebar:
        st.markdown(f'<div class="brand"><div><div class="b1">Pelacak Keuangan</div>'
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
        from keuangan.pin import kunci_sekarang, punya_pin
        if punya_pin():
            st.button("Kunci", key="nav_kunci", width="stretch", icon=":material/lock:", on_click=kunci_sekarang)
        if st.button("Muat ulang", key="nav_muat", width="stretch", icon=":material/refresh:",
                     help="Ambil data terbaru dari penyimpanan"):
            muat_ke_sesi()
            st.rerun()
        if cfg_github():
            st.caption(f"Data: {cfg_github()['repo']}")
        if hanya_lihat():
            st.caption("Akun ini hanya bisa melihat.")
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


def tampilkan_isi(halaman):
    if halaman == "Beranda":
        halaman_beranda()
    elif halaman == "Pencarian":
        halaman_cari()
    elif halaman == "Catat transaksi":
        halaman_catat()
    elif halaman == "Daftar transaksi":
        halaman_transaksi()
    elif halaman == "Barang dan produk":
        halaman_barang()
    elif halaman == "Toko dan tempat beli":
        halaman_toko()
    elif halaman == "Jenis toko":
        from keuangan.toko import halaman_jenis_toko
        halaman_jenis_toko()
    elif halaman == "Platform beli online":
        halaman_platform()
    elif halaman == "Asisten AI":
        from keuangan.ai_fitur import halaman_asisten
        halaman_asisten()
    elif halaman == "Privasi AI":
        from keuangan.ai import halaman_privasi_ai
        halaman_privasi_ai()
    elif halaman == "Daftar belanja":
        halaman_belanja()
    elif halaman == "Riwayat aktivitas":
        halaman_aktivitas()
    elif halaman == "Tempat sampah":
        halaman_sampah()
    elif halaman == "Anggaran":
        halaman_anggaran()
    elif halaman == "Transaksi berulang":
        halaman_tagihan()
    elif halaman == "Target tabungan":
        halaman_tabungan()
    elif halaman == "Utang-piutang":
        halaman_utang()
    elif halaman == "Laporan":
        halaman_laporan()
    elif halaman == "Tampilan":
        halaman_tampilan()
    elif halaman == "Pemeriksa data":
        from keuangan.periksa import halaman_periksa
        halaman_periksa()
    elif halaman == "Mesin baca struk":
        halaman_mesin()
    elif halaman == "Ekspor dan impor":
        if hanya_lihat():
            halaman_ekspor()
        else:
            t1, t2, t3, t4 = st.tabs(["Ekspor", "Impor", "Mutasi rekening", "Aplikasi lama"])
            with t1:
                halaman_ekspor()
            with t2:
                halaman_impor()
            with t3:
                from keuangan.mutasi import halaman_mutasi
                halaman_mutasi()
            with t4:
                halaman_aplikasi_lama()
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


def tampilkan_halaman(halaman):
    """Halaman biasa langsung digambar; halaman gabungan menampilkan pilihan bagian (pil) lalu isi bagian terpilih."""
    bagian = [(lb, lama) for lb, lama, admin in GABUNGAN.get(halaman, []) if not admin or adalah_admin()]
    if not bagian:
        tampilkan_isi(halaman)
        return
    if len(bagian) > 1:
        label = [b[0] for b in bagian]
        kunci = f"sub_{halaman}"
        if st.session_state.get(kunci) not in label:
            st.session_state[kunci] = label[0]
        st.pills("Bagian", label, selection_mode="single", key=kunci, label_visibility="collapsed")
        pilih = st.session_state.get(kunci) or label[0]
    else:
        pilih = bagian[0][0]
    lama = dict(bagian)[pilih]
    if DESKRIPSI.get(lama) and lama != halaman:
        st.caption(DESKRIPSI[lama])
    tampilkan_isi(lama)


def jalankan():
    pasang_css()
    pasang_pwa()
    pasang_sambung_ulang()
    siapkan_sesi()
    peringatan_uji()
    catat_otomatis()
    cadangan_otomatis()
    PENGATURAN, halaman = pilih_halaman()
    tampilkan_sidebar(halaman, PENGATURAN)
    tampilkan_kepala(halaman, PENGATURAN)
    tampilkan_halaman(halaman)
    simpan_alamat(halaman)


def simpan_alamat(halaman):
    """Catat halaman (dan bagiannya) di alamat, supaya muat ulang atau sambung ulang kembali ke halaman yang sama."""
    try:
        if st.query_params.get("h") != halaman:
            st.query_params["h"] = halaman
        sb = st.session_state.get(f"sub_{halaman}") if halaman in GABUNGAN else None
        if sb and st.query_params.get("s") != sb:
            st.query_params["s"] = sb
        elif not sb and "s" in st.query_params:
            del st.query_params["s"]
    except Exception:
        pass
