"""Tutup buku bulanan: daftar periksa akhir bulan, lalu bulan yang sudah ditutup dikunci dari perubahan transaksi."""
import calendar
from datetime import date

import streamlit as st

from keuangan.bantu import catat, kat_dari, selesai_simpan, versi
from keuangan.inti import D, adalah_admin, hanya_lihat, hari_ini, nama_bulan, pengguna_nama, sekarang


def tertutup() -> dict:
    return D["pengaturan"].setdefault("tutup", {})


def terkunci(tgl) -> bool:
    return str(tgl)[:7] in tertutup()


def tolak(*tgl) -> bool:
    """Tampilkan galat dan kembalikan True bila salah satu tanggal jatuh di bulan yang sudah ditutup."""
    kunci = sorted({str(t)[:7] for t in tgl if t} & set(tertutup()))
    if not kunci:
        return False
    st.error(f"{', '.join(nama_bulan(k) for k in kunci)} sudah ditutup, jadi transaksinya tidak bisa ditambah, diubah, atau dihapus. "
             "Buka kembali di Pengaturan > Perawatan data > Tutup buku bila memang perlu.")
    return True


def periksa_bulan(ym: str) -> list:
    """[(judul, jumlah, petunjuk)] hal yang sebaiknya dibereskan sebelum bulan ditutup. Jumlah 0 berarti beres."""
    from keuangan.periksa import temukan
    ts = [t for t in D["transaksi"] if t["tgl"][:7] == ym]
    tanpa = [t for t in ts if t["jenis"] != "transfer" and not kat_dari(t.get("kategori"))]
    masalah = [m for m in temukan() if m["tx"]["tgl"][:7] == ym]
    ganda = [m for m in masalah if m["jenis"] == "ganda"]
    lain = [m for m in masalah if m["jenis"] != "ganda"]
    akhir = date(int(ym[:4]), int(ym[5:]), calendar.monthrange(int(ym[:4]), int(ym[5:]))[1]).isoformat()
    tagihan = [t for t in D["tagihan"] if t.get("aktif", True) and t.get("berikut") and t["berikut"] <= akhir]
    return [("Transaksi tanpa kategori", len(tanpa), "Beri kategori lewat Daftar transaksi (ubah massal membantu)."),
            ("Kemungkinan transaksi ganda", len(ganda), "Periksa di Perawatan data > Pemeriksa data."),
            ("Masalah data lain", len(lain), "Periksa di Perawatan data > Pemeriksa data."),
            ("Tagihan jatuh tempo yang belum dicatat", len(tagihan), "Catat atau jadwalkan di Transaksi berulang.")]


def bulan_bisa_ditutup() -> list:
    ini = hari_ini().strftime("%Y-%m")
    return sorted({t["tgl"][:7] for t in D["transaksi"] if t["tgl"][:7] < ini} - set(tertutup()), reverse=True)


def halaman_tutup_buku():
    st.caption("Setelah ditutup, transaksi pada bulan itu tidak bisa ditambah, diubah, atau dihapus sampai dibuka kembali. Berlaku untuk catat, ubah, hapus, struk, ubah massal, dan impor mutasi. "
               "Transaksi otomatis dari tagihan, utang, dan patungan tidak ikut dikunci.")
    boleh = adalah_admin() and not hanya_lihat()
    pilihan = bulan_bisa_ditutup()
    if not pilihan:
        st.info("Belum ada bulan yang selesai dan masih terbuka.")
    else:
        ym = st.selectbox("Bulan yang mau ditutup", pilihan, format_func=nama_bulan, key="tb_bulan")
        hal = periksa_bulan(ym)
        for judul, n, petunjuk in hal:
            st.markdown(f"{'✅' if not n else '⚠️'} **{judul}**: {n if n else 'beres'}")
            if n:
                st.caption(petunjuk)
        belum = sum(n for _, n, _ in hal)
        if belum:
            st.caption("Masih ada yang belum beres. Bulan tetap boleh ditutup, tapi sebaiknya dibereskan dulu.")
        if st.button(f"🔒 Tutup {nama_bulan(ym)}", type="primary", key=f"tb_tutup_{ym}", disabled=not boleh):
            tertutup()[ym] = {"waktu": sekarang().strftime("%Y-%m-%d %H:%M"), "oleh": pengguna_nama(), "belum": belum}
            catat("data", f"Tutup buku {nama_bulan(ym)}")
            selesai_simpan(f"{nama_bulan(ym)} ditutup.")
        if not boleh:
            st.caption("Hanya admin yang bisa menutup bulan.")
    if tertutup():
        st.markdown("**Bulan yang sudah ditutup**")
        for ym in sorted(tertutup(), reverse=True):
            c1, c2 = st.columns([3, 1])
            info = tertutup()[ym]
            c1.markdown(f"🔒 **{nama_bulan(ym)}**  \n<small>ditutup {info.get('waktu', '')} oleh {info.get('oleh', '')}</small>", unsafe_allow_html=True)
            if c2.button("Buka", key=f"tb_buka_{ym}_{versi()}", disabled=not boleh):
                tertutup().pop(ym, None)
                catat("data", f"Buka kembali {nama_bulan(ym)}")
                selesai_simpan(f"{nama_bulan(ym)} dibuka kembali.")
