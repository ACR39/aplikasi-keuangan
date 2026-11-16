"""Banding harga: tabel barang x toko dari riwayat pembelian (tanpa AI). Sel termurah ditandai."""
from datetime import timedelta

import pandas as pd
import streamlit as st

from keuangan.bantu import f_kat, kategori_jenis, toko_dari, transaksi_barang, turunan
from keuangan.inti import D, hari_ini, rp

MIN_TOKO = 2


def harga_per_toko(barang_id: str, rata: bool, hari: int = 90) -> dict:
    """{id toko: harga satuan} untuk satu barang. rata=False: harga terakhir; rata=True: rata-rata `hari` hari terakhir (jatuh ke harga terakhir bila kosong)."""
    batas = (hari_ini() - timedelta(days=hari)).isoformat()
    terakhir, daftar = {}, {}
    for t in transaksi_barang(barang_id):  # terbaru dulu
        k = t.get("toko")
        if t["jenis"] != "keluar" or not k or not t.get("harga_satuan"):
            continue
        h = int(t["harga_satuan"])
        terakhir.setdefault(k, h)
        if t["tgl"] >= batas:
            daftar.setdefault(k, []).append(h)
    if not rata:
        return terakhir
    return {k: round(sum(daftar[k]) / len(daftar[k])) if k in daftar else v for k, v in terakhir.items()}


def susun(kat: str = "", rata: bool = False) -> list:
    """Barang yang punya harga di minimal MIN_TOKO toko. Tiap baris: {nama, harga{toko:h}, murah, murah_h, selisih{toko:h-murah}}."""
    ids = turunan(kat) if kat else None
    hasil = []
    for b in D["barang"]:
        if ids is not None and b["kategori"] not in ids:
            continue
        per = {k: v for k, v in harga_per_toko(b["id"], rata).items() if toko_dari(k)}
        if len(per) < MIN_TOKO:
            continue
        m = min(per, key=per.get)
        hasil.append({"nama": b["nama"], "harga": per, "murah": m, "murah_h": per[m], "selisih": {k: v - per[m] for k, v in per.items()}})
    return sorted(hasil, key=lambda r: r["nama"].lower())


def juara(baris: list) -> list:
    """[(nama toko, berapa barang termurah di sana, dari berapa barang yang dijual di sana)] terurut dari yang sering termurah."""
    menang, ikut = {}, {}
    for r in baris:
        for k in r["harga"]:
            ikut[k] = ikut.get(k, 0) + 1
        menang[r["murah"]] = menang.get(r["murah"], 0) + 1
    return sorted([(toko_dari(k)["nama"], menang.get(k, 0), n) for k, n in ikut.items()], key=lambda x: (-x[1], x[2]))


def halaman_banding_harga():
    st.caption("Harga satuan tiap barang di toko yang berbeda, dari riwayat pembelianmu. Hanya barang yang pernah dibeli di minimal dua toko.")
    c1, c2 = st.columns(2)
    opsi = [""] + [k["id"] for k in kategori_jenis("keluar") if not k.get("induk")]
    kat = c1.selectbox("Kategori", opsi, format_func=f_kat({"": "Semua kategori"}), key="bh_kat")
    mode = c2.radio("Harga yang dipakai", ["Terakhir", "Rata-rata 3 bulan"], key="bh_mode", horizontal=True)
    baris = susun(kat, mode != "Terakhir")
    if not baris:
        st.info("Belum ada barang yang dibeli di dua toko berbeda. Pilih toko dan isi harga satuan saat mencatat, nanti perbandingannya muncul di sini.")
        return
    jr = juara(baris)
    if len(jr) >= 2:
        n, m, ikut = jr[0]
        if m == jr[1][1]:
            st.info("Belum ada toko yang jelas paling murah: hasilnya seri.")
        else:
            st.success(f"{n} paling sering termurah: {m} dari {ikut} barang yang dijual di sana.")
    tokos = sorted({k for r in baris for k in r["harga"]}, key=lambda k: toko_dari(k)["nama"].lower())
    nama = {k: toko_dari(k)["nama"] for k in tokos}
    df = pd.DataFrame([{"Barang": r["nama"], **{nama[k]: r["harga"].get(k) for k in tokos}, "Termurah": nama[r["murah"]]} for r in baris]).set_index("Barang")

    def tandai(row):
        m = min(v for c, v in row.items() if c != "Termurah" and pd.notna(v))
        return ["background-color: rgba(46,160,107,.28); font-weight: 600" if c != "Termurah" and pd.notna(v) and v == m else "" for c, v in row.items()]
    st.dataframe(df.style.apply(tandai, axis=1).format("{:,.0f}".format, subset=list(nama.values()), na_rep="-"), width="stretch")
    st.markdown("**Selisih dari termurah**")
    for r in baris:
        lain = sorted([(nama[k], s) for k, s in r["selisih"].items() if k != r["murah"]], key=lambda x: x[1])
        hemat = max((s for _, s in lain), default=0)
        with st.container(border=True):
            st.markdown(f"**{r['nama']}** · termurah di {nama[r['murah']]} ({rp(r['murah_h'])})")
            st.caption("  ·  ".join(f"{n} +{rp(s)}" if s else f"{n} sama" for n, s in lain) + (f"  ·  selisih terbesar {rp(hemat)}" if hemat else ""))
