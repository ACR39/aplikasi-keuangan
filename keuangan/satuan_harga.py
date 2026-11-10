"""Perbandingan harga per satuan antar merek (per 100 g, per 100 ml, atau per buah) dari ukuran kemasan barang."""
import re

import streamlit as st

from keuangan.bantu import e, nama_kat
from keuangan.inti import D, rp

_SATUAN = {"mg": ("berat", 0.001), "g": ("berat", 1), "gr": ("berat", 1), "gram": ("berat", 1), "kg": ("berat", 1000),
           "ml": ("volume", 1), "cc": ("volume", 1), "l": ("volume", 1000), "lt": ("volume", 1000), "liter": ("volume", 1000),
           "pcs": ("jumlah", 1), "buah": ("jumlah", 1), "butir": ("jumlah", 1), "lembar": ("jumlah", 1), "sachet": ("jumlah", 1),
           "biji": ("jumlah", 1), "bungkus": ("jumlah", 1), "botol": ("jumlah", 1), "kaleng": ("jumlah", 1), "pak": ("jumlah", 1)}
PER = {"berat": ("100 g", 100), "volume": ("100 ml", 100), "jumlah": ("buah", 1)}


def parse_ukuran(teks: str):
    """'2 x 85 g', '1,5 L', '500ml', 'isi 12' -> (dimensi, jumlah dalam g/ml/buah) atau None bila tidak terbaca."""
    s = str(teks or "").lower().replace(",", ".").strip()
    if not s:
        return None
    kali = 1.0
    m = re.match(r"^\s*(\d+)\s*[x×]\s*(.+)$", s)
    if m:
        kali, s = float(m.group(1)), m.group(2)
    m = re.match(r"^\s*isi\s*(\d+(?:\.\d+)?)\s*([a-z]*)\s*$", s)
    if m:
        return "jumlah", float(m.group(1)) * kali
    m = re.match(r"^\s*(\d+(?:\.\d+)?)\s*([a-z]+)\s*$", s)
    if not m or m.group(2) not in _SATUAN:
        return None
    dim, f = _SATUAN[m.group(2)]
    v = float(m.group(1)) * f * kali
    return (dim, v) if v > 0 else None


def harga_per_satuan(b: dict):
    """(dimensi, harga per 100 g / 100 ml / buah) untuk barang, atau None."""
    p = parse_ukuran(b.get("ukuran"))
    if not p or not b.get("harga"):
        return None
    dim, v = p
    return dim, float(b["harga"]) / v * PER[dim][1]


def banding_merek() -> list:
    """[(id_kategori, dimensi, [(barang, harga_per_satuan)] termurah dulu)] untuk kelompok dengan minimal 2 barang bisa dibandingkan."""
    kel = {}
    for b in D["barang"]:
        h = harga_per_satuan(b)
        if h:
            kel.setdefault((b.get("kategori"), h[0]), []).append((b, h[1]))
    return [(k[0], k[1], sorted(v, key=lambda x: x[1])) for k, v in sorted(kel.items(), key=lambda x: nama_kat(x[0][0]).lower()) if len(v) >= 2]


def halaman_per_satuan():
    st.caption("Membandingkan harga per 100 g, per 100 ml, atau per buah untuk barang sekategori, dari harga terakhir dan ukuran kemasan. "
               "Isi 'Ukuran / isi kemasan' di Barang dan produk (contoh: 85 g, 1 liter, 2 x 250 ml, isi 12).")
    hasil = banding_merek()
    tanpa = [b for b in D["barang"] if not parse_ukuran(b.get("ukuran")) and b.get("harga")]
    if not hasil:
        st.info("Belum ada kelompok yang bisa dibandingkan. Perlu minimal dua barang sekategori dengan ukuran kemasan dan harga.")
    for kat, dim, daftar in hasil:
        with st.container(key=f"kartu_g_ps_{kat}_{dim}"):
            st.markdown(f"**{e(nama_kat(kat))}** · per {PER[dim][0]}")
            murah = daftar[0][1]
            for i, (b, h) in enumerate(daftar):
                rinci = " · ".join(e(x) for x in (b.get("merek"), b.get("ukuran")) if x)
                selisih = f' · +{(h / murah - 1) * 100:.0f}% dari termurah' if i else ' · termurah ✅'
                st.markdown(f'<div class="perhatian"><b>{e(b["nama"])}</b> ({rinci}) · {rp(round(h))} per {PER[dim][0]}{selisih}</div>', unsafe_allow_html=True)
    if tanpa:
        st.caption(f"{len(tanpa)} barang belum bisa dibandingkan karena ukuran kemasannya kosong atau tidak terbaca.")
