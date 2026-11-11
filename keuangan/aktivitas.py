"""Riwayat aktivitas dan tempat sampah transaksi."""
from datetime import timedelta

import streamlit as st

from keuangan.bantu import atur, baris_transaksi, catat, e, perbarui_harga_barang, ringkas_teks, selesai_simpan
from keuangan.inti import D, HARI_SAMPAH, fmt_iso, fmt_waktu, hanya_lihat, hari_ini, iso_ke_date

IKON = {"tambah": "➕", "ubah": "✏️", "hapus": "🗑️", "pulih": "♻️", "tagihan": "⏰", "anggaran": "🎯", "tabungan": "🐷",
        "utang": "🤝", "barang": "📦", "toko": "🏪", "platform": "🛵", "belanja": "🛒", "dompet": "👛", "kategori": "🏷️", "impor": "📥", "data": "💾", "pengaturan": "⚙️"}


def bersihkan_sampah():
    """Buang isi sampah yang lebih dari 30 hari (disimpan saat ada perubahan berikutnya)."""
    batas = hari_ini() - timedelta(days=HARI_SAMPAH)
    D["sampah"] = [s for s in D["sampah"] if (iso_ke_date(s.get("dihapus")) or hari_ini()) > batas]


def halaman_aktivitas():
    log = sorted(D["aktivitas"], key=lambda a: a["waktu"], reverse=True)
    jenis = st.multiselect("Jenis aktivitas", sorted(IKON), default=[], key="ak_jenis", placeholder="Semua jenis")
    if jenis:
        log = [a for a in log if a["jenis"] in jenis]
    if not log:
        st.info("Belum ada aktivitas tercatat.")
    for a in log[:150]:
        st.markdown(f'<div class="akt"><div class="ah">{IKON.get(a["jenis"], "•")} {e(a["jenis"].capitalize())}</div>'
                    f'<div class="ar">{e(a["rincian"])}</div><div class="am">{fmt_waktu(a["waktu"])} · {e(a["oleh"])}</div></div>',
                    unsafe_allow_html=True)
    if len(log) > 150:
        st.caption(f"Menampilkan 150 terbaru dari {len(log)}.")


def halaman_sampah():
    if not D["sampah"]:
        st.info("Tempat sampah kosong.")
        return
    st.caption(f"Transaksi yang dihapus disimpan {HARI_SAMPAH} hari, lalu hilang permanen.")
    for s in sorted(D["sampah"], key=lambda s: s["dihapus"], reverse=True):
        t = s["transaksi"]
        sisa = HARI_SAMPAH - (hari_ini() - (iso_ke_date(s["dihapus"]) or hari_ini())).days
        with st.container(key=f"tx_sp_{s['id']}"):
            st.markdown(baris_transaksi(t) + f'<div class="mt" style="margin-top:.3rem;color:#6b7280;font-size:.78rem">Dihapus {fmt_iso(s["dihapus"])} · hilang permanen {max(sisa, 0)} hari lagi</div>',
                        unsafe_allow_html=True)
            if not hanya_lihat():
                a, b, _ = st.columns([1, 1.3, 4])
                if a.button("Pulihkan", key=f"pulih_{s['id']}", type="primary"):
                    D["sampah"] = [x for x in D["sampah"] if x["id"] != s["id"]]
                    D["transaksi"].append(t)
                    if t.get("barang"):
                        perbarui_harga_barang(t["barang"])
                    catat("pulih", ringkas_teks(t))
                    selesai_simpan("Transaksi dipulihkan.")
                if b.button("Hapus permanen", key=f"permanen_{s['id']}"):
                    D["sampah"] = [x for x in D["sampah"] if x["id"] != s["id"]]
                    catat("hapus", f"Hapus permanen: {ringkas_teks(t)}")
                    selesai_simpan("Dihapus permanen.")
