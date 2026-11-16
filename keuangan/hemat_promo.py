"""Hemat promo: total diskon dan nilai barang gratis dari riwayat pembelian (tanpa AI)."""
import pandas as pd
import streamlit as st

from keuangan.bantu import barang_dari, daftar_bulan, deretan_stat, info_diskon, kartu_stat, toko_dari
from keuangan.inti import D, nama_bulan, rp


def nilai_gratis(t: dict) -> int:
    """Perkiraan nilai barang gratis: banyaknya x harga normal, atau harga terakhir barang itu, atau harga yang pernah dibayar."""
    qty = float(t.get("qty") or 1)
    h = int(t.get("harga_normal") or 0)
    if not h:
        b = barang_dari(t.get("barang"))
        h = int((b or {}).get("harga") or 0)
    return round(qty * h)


def hitung(bulan: str = "semua") -> dict:
    """{diskon, gratis, n_diskon, n_gratis, per_barang{nama:rp}, per_toko{nama:rp}} untuk satu bulan (YYYY-MM) atau semua."""
    r = {"diskon": 0, "gratis": 0, "n_diskon": 0, "n_gratis": 0, "per_barang": {}, "per_toko": {}}
    for t in D["transaksi"]:
        if t["jenis"] != "keluar" or (bulan != "semua" and t["tgl"][:7] != bulan):
            continue
        hemat = 0
        d = info_diskon(t)
        if d and not t.get("gratis"):
            hemat = round(d[1] * float(t.get("qty") or 1))
            r["diskon"] += hemat
            r["n_diskon"] += 1
        elif t.get("gratis"):
            hemat = nilai_gratis(t)
            r["gratis"] += hemat
            r["n_gratis"] += 1
        if hemat:
            nama = (barang_dari(t.get("barang")) or {}).get("nama") or t.get("catatan") or "(tanpa barang)"
            r["per_barang"][nama] = r["per_barang"].get(nama, 0) + hemat
            tk = (toko_dari(t.get("toko")) or {}).get("nama", "(tanpa toko)")
            r["per_toko"][tk] = r["per_toko"].get(tk, 0) + hemat
    return r


def halaman_hemat_promo():
    st.caption("Dihitung dari transaksi yang punya harga normal (diskon, voucher) dan barang yang ditandai gratis. "
               "Nilai barang gratis adalah perkiraan dari harga barang itu.")
    bulan_semua = daftar_bulan()
    if not bulan_semua:
        st.info("Belum ada transaksi.")
        return
    bulan = st.selectbox("Periode", ["semua"] + bulan_semua, key="hp_bulan", format_func=lambda b: "Semua waktu" if b == "semua" else nama_bulan(b))
    r = hitung(bulan)
    total = r["diskon"] + r["gratis"]
    if not total:
        st.info("Belum ada diskon atau barang gratis di periode ini. Isi Harga normal saat mencatat barang yang sedang diskon.")
        return
    deretan_stat(kartu_stat("Total hemat", rp(total), "", "g"),
                 kartu_stat("Dari diskon", rp(r["diskon"]), f"{r['n_diskon']} pembelian"),
                 kartu_stat("Barang gratis", rp(r["gratis"]), f"{r['n_gratis']} barang"))
    ada = [b for b in sorted(bulan_semua)[-6:]]
    deret = {nama_bulan(b): (lambda x: x["diskon"] + x["gratis"])(hitung(b)) for b in ada}
    if sum(deret.values()):
        st.markdown("**Hemat per bulan**")
        st.bar_chart(pd.Series(deret), color="#256b4a")
    c1, c2 = st.columns(2)
    for kol, judul, kunci in ((c1, "Barang paling banyak dihemat", "per_barang"), (c2, "Toko paling banyak promo", "per_toko")):
        with kol:
            st.markdown(f"**{judul}**")
            top = sorted(r[kunci].items(), key=lambda x: -x[1])[:8]
            st.dataframe(pd.DataFrame(top, columns=["Nama", "Hemat (Rp)"]).set_index("Nama").style.format("{:,.0f}".format), width="stretch")
