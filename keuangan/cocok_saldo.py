"""Cocokkan saldo dompet di aplikasi dengan saldo asli (rekening, e-wallet, dompet fisik) dan catat selisihnya."""
import streamlit as st

from keuangan.bantu import catat, dompet_aktif, kat_pertama, saldo_dompet, selesai_simpan, tambah_transaksi, versi
from keuangan.inti import D, TGL_MAX, TGL_MIN, fmt_iso, hanya_lihat, hari_ini, rp
from keuangan.tutup_buku import tolak


def selisih_catat(dompet_id: str, nyata: int, tgl) -> int:
    """Buat transaksi penyesuaian agar saldo dompet pada `tgl` sama dengan `nyata`. Kembalikan selisihnya (positif = uang lebih banyak dari catatan)."""
    d = next(x for x in D["dompet"] if x["id"] == dompet_id)
    tgl_s = tgl.isoformat() if hasattr(tgl, "isoformat") else str(tgl)
    beda = int(nyata) - saldo_dompet(dompet_id, tgl_s)
    if beda:
        jenis = "masuk" if beda > 0 else "keluar"
        tambah_transaksi(jenis, tgl, abs(beda), dompet_id, kat_pertama(jenis, "k_lain") or "", f"Penyesuaian saldo {d['nama']}", penyesuaian=True)
    d["cocok"] = {"tgl": tgl_s, "saldo": int(nyata), "selisih": beda}
    return beda


def dompet_belum_cocok(ym: str) -> list:
    """Dompet aktif yang belum pernah dicocokkan pada atau sesudah bulan ym."""
    return [d for d in dompet_aktif() if (d.get("cocok") or {}).get("tgl", "")[:7] < ym]


def halaman_cocok_saldo():
    st.caption("Isi saldo sebenarnya dari aplikasi bank, e-wallet, atau hitungan uang tunai. Bila beda dengan catatan, aplikasi membuat satu transaksi penyesuaian "
               "(pemasukan atau pengeluaran, kategori Lain-lain) supaya saldonya sama. Selisih yang besar biasanya tanda ada transaksi yang belum dicatat: cari dulu sebelum menyesuaikan.")
    ds = dompet_aktif()
    if not ds:
        st.info("Belum ada dompet aktif.")
        return
    tgl = st.date_input("Saldo sebenarnya per tanggal", value=hari_ini(), min_value=TGL_MIN, max_value=TGL_MAX, format="DD/MM/YYYY", key="cs_tgl")
    for d in ds:
        app = saldo_dompet(d["id"], tgl.isoformat())
        with st.container(key=f"kartu_g_cs_{d['id']}"):
            st.markdown(f"**{d['nama']}** · catatan aplikasi {rp(app)}")
            c = d.get("cocok")
            if c:
                st.caption(f"Terakhir dicocokkan {fmt_iso(c['tgl'])}" + (f", selisih {rp(c['selisih'])} disesuaikan" if c.get("selisih") else ", cocok"))
            nyata = st.number_input("Saldo sebenarnya (Rp)", value=int(app), step=1000, key=f"cs_n_{d['id']}_{versi()}", label_visibility="collapsed")
            beda = int(nyata) - app
            if beda:
                st.markdown(f"Selisih **{rp(abs(beda))}** · uang {'lebih banyak' if beda > 0 else 'lebih sedikit'} dari catatan")
            if st.button("Catat selisih" if beda else "Tandai cocok", key=f"cs_ok_{d['id']}_{versi()}", disabled=hanya_lihat(), type="primary" if beda else "secondary"):
                if tolak(tgl):
                    return
                b = selisih_catat(d["id"], int(nyata), tgl)
                catat("tambah", f"Cocokkan saldo {d['nama']}: " + (f"penyesuaian {rp(b)}" if b else "cocok"))
                selesai_simpan(f"{d['nama']}: " + (f"penyesuaian {rp(abs(b))} dicatat." if b else "saldo cocok."))
