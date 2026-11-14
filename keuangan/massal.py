"""Ubah banyak transaksi sekaligus (kategori, dompet, toko) dari hasil filter di Daftar transaksi."""
import streamlit as st

from keuangan.bantu import catat, f_dompet, f_kat, f_toko, kategori_jenis, ringkas_teks, selesai_simpan, versi
from keuangan.inti import D, fmt_iso


def ubah_banyak(ids: set, kategori: str = "", dompet: str = "", toko: str = "") -> dict:
    """Terapkan ke transaksi berid ids. Kategori hanya untuk transaksi sejenis; transfer dilewati untuk kategori dan toko.
    Kembalikan {'diubah': n, 'dilewati': n}."""
    from keuangan.bantu import kat_dari
    kj = (kat_dari(kategori) or {}).get("jenis") if kategori else None
    diubah = lewat = 0
    for t in D["transaksi"]:
        if t["id"] not in ids:
            continue
        berubah = False
        if kategori:
            if t["jenis"] != "transfer" and t["jenis"] == kj:
                t["kategori"], berubah = kategori, True
            else:
                lewat += 1
        if dompet and t["dompet"] != dompet:
            t["dompet"], berubah = dompet, True
        if toko and t["jenis"] != "transfer":
            t["toko"], berubah = (None if toko == "-" else toko), True
            if t["toko"] is None:
                t.pop("toko")
        diubah += berubah
    return {"diubah": diubah, "dilewati": lewat}


def hapus_banyak(ids: set) -> int:
    """Pindahkan transaksi berid ids ke Tempat sampah (bisa dipulihkan). Kembalikan jumlah yang dipindah."""
    from keuangan.bantu import baru_id, perbarui_harga_barang
    from keuangan.inti import hari_ini
    ada = [t for t in D["transaksi"] if t["id"] in ids]
    if not ada:
        return 0
    D["transaksi"] = [t for t in D["transaksi"] if t["id"] not in ids]
    for t in ada:
        D["sampah"].append({"id": baru_id(), "transaksi": t, "dihapus": hari_ini().isoformat()})
    for b in {t["barang"] for t in ada if t.get("barang")}:
        perbarui_harga_barang(b)
    return len(ada)


def panel_massal(hasil: list):
    with st.expander("✏️ Ubah banyak sekaligus", expanded=False):
        st.caption("Pilih transaksi dari hasil filter di atas, lalu tentukan yang ingin diganti. Kolom yang dibiarkan 'tidak diubah' tidak disentuh.")
        semua = st.checkbox(f"Pilih semua {len(hasil)} hasil filter", key="tb_semua")
        pilihan = {t["id"]: f"{fmt_iso(t['tgl'])} · {ringkas_teks(t)}"[:90] for t in hasil[:300]}
        ids = list(pilihan) if semua else st.multiselect("Transaksi", list(pilihan), format_func=pilihan.get, key=f"tb_pilih_{versi()}")
        c1, c2, c3 = st.columns(3)
        jenis_k = sorted({t["jenis"] for t in hasil if t["id"] in ids and t["jenis"] != "transfer"})
        kat_opsi = [""] + [k["id"] for j in (jenis_k or ["keluar"]) for k in kategori_jenis(j)]
        kat = c1.selectbox("Kategori", kat_opsi, format_func=f_kat({"": "(tidak diubah)"}), key=f"tb_kat_{versi()}")
        dom = c2.selectbox("Dompet", [""] + [d["id"] for d in D["dompet"] if not d.get("arsip")], format_func=f_dompet({"": "(tidak diubah)"}), key=f"tb_dom_{versi()}")
        tk = c3.selectbox("Toko", ["", "-"] + [x["id"] for x in D["toko"]], format_func=f_toko({"": "(tidak diubah)", "-": "(kosongkan toko)"}), key=f"tb_tk_{versi()}")
        if st.button("Terapkan", key="tb_terapkan", type="primary", disabled=not ids or not (kat or dom or tk)):
            r = ubah_banyak(set(ids), kat, dom, tk)
            catat("ubah", f"Ubah banyak: {r['diubah']} transaksi")
            selesai_simpan(f"{r['diubah']} transaksi diubah" + (f", {r['dilewati']} dilewati (jenis kategori tidak cocok)." if r["dilewati"] else "."))
        st.divider()
        konfirm = st.session_state.get("tb_konfirm_hapus")
        if konfirm and set(konfirm) == set(ids) and ids:
            st.warning(f"Hapus {len(ids)} transaksi terpilih? Semuanya masuk Tempat sampah dan bisa dipulihkan selama 30 hari.")
            a, b, _ = st.columns([2, 1, 2])
            if a.button("Ya, hapus semua", key="tb_ya_hapus", type="primary"):
                n = hapus_banyak(set(ids))
                catat("hapus", f"Hapus banyak: {n} transaksi")
                selesai_simpan(f"{n} transaksi dihapus (ada di Tempat sampah).", tb_konfirm_hapus=None)
            if b.button("Batal", key="tb_batal_hapus"):
                st.session_state.pop("tb_konfirm_hapus", None)
                st.rerun()
        elif st.button(f"🗑 Hapus {len(ids)} terpilih" if ids else "🗑 Hapus terpilih", key="tb_hapus", disabled=not ids):
            st.session_state["tb_konfirm_hapus"] = list(ids)
            st.rerun()
