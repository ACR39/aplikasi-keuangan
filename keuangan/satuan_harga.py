"""Perbandingan harga per satuan antar merek (per 100 g, per 100 ml, per buah, per bulan, atau per satuan lain) dari ukuran kemasan barang."""
import re

import streamlit as st

from keuangan.bantu import e, nama_kat
from keuangan.inti import D, rp

_SATUAN = {"mg": ("berat", 0.001), "g": ("berat", 1), "gr": ("berat", 1), "gram": ("berat", 1), "kg": ("berat", 1000), "ons": ("berat", 100),
           "ml": ("volume", 1), "cc": ("volume", 1), "l": ("volume", 1000), "lt": ("volume", 1000), "liter": ("volume", 1000),
           "hari": ("waktu", 1), "minggu": ("waktu", 7), "bulan": ("waktu", 30), "tahun": ("waktu", 365)}
# satuan hitung yang dianggap setara dengan satu buah
_HITUNG = {"pcs", "pc", "buah", "butir", "lembar", "sachet", "biji", "bungkus", "botol", "kaleng", "pak", "pack", "potong", "porsi", "kotak", "box",
           "paket", "rak", "tablet", "kapsul", "slice", "roll", "gulung", "ikat", "sisir", "ekor", "batang", "helai", "pasang", "set", "pouch",
           "cup", "gelas", "mangkuk", "siung", "tangkai", "tube", "sak", "karung", "kantong", "bal", "lembaran", "stick", "bks", "btl"}
_KALI = {"lusin": 12, "kodi": 20, "gros": 144}
PER = {"berat": ("100 g", 100), "volume": ("100 ml", 100), "jumlah": ("buah", 1), "waktu": ("bulan", 30)}


def per(dim: str):
    """(nama satuan pembanding, pembagi). Dimensi 'satuan:potong' berarti kata satuan yang tidak dikenal, dibandingkan per kata itu."""
    if dim.startswith("satuan:"):
        return dim[7:], 1
    return PER[dim]


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
    if not m:
        return None
    kata = m.group(2)
    if kata in _SATUAN:
        dim, f = _SATUAN[kata]
    elif kata in _HITUNG:
        dim, f = "jumlah", 1
    elif kata in _KALI:
        dim, f = "jumlah", _KALI[kata]
    else:
        dim, f = f"satuan:{kata}", 1   # satuan lain (mis. 'helm', 'pot'): dibandingkan per satuan itu sendiri
    v = float(m.group(1)) * f * kali
    return (dim, v) if v > 0 else None


def harga_per_satuan(b: dict):
    """(dimensi, harga per 100 g / 100 ml / buah) untuk barang, atau None."""
    p = parse_ukuran(b.get("ukuran"))
    if not p or not b.get("harga"):
        return None
    dim, v = p
    return dim, float(b["harga"]) / v * per(dim)[1]


def banding_merek() -> list:
    """[(id_kategori, dimensi, [(barang, harga_per_satuan)] termurah dulu)] untuk kelompok dengan minimal 2 barang bisa dibandingkan."""
    kel = {}
    for b in D["barang"]:
        h = harga_per_satuan(b)
        if h:
            kel.setdefault((b.get("kategori"), h[0]), []).append((b, h[1]))
    return [(k[0], k[1], sorted(v, key=lambda x: x[1])) for k, v in sorted(kel.items(), key=lambda x: nama_kat(x[0][0]).lower()) if len(v) >= 2]


def halaman_per_satuan():
    st.caption("Membandingkan harga per 100 g, per 100 ml, per buah, per bulan, atau per satuan lain untuk barang sekategori, dari harga terakhir dan ukuran kemasan. "
               "Isi 'Ukuran / isi kemasan' di Barang dan produk (contoh: 85 g, 1 liter, 2 x 250 ml, isi 12, 6 potong, 3 bulan, 1 lusin).")
    hasil = banding_merek()
    tanpa = [b for b in D["barang"] if not parse_ukuran(b.get("ukuran")) and b.get("harga")]
    if not hasil:
        st.info("Belum ada kelompok yang bisa dibandingkan. Perlu minimal dua barang sekategori dengan ukuran kemasan dan harga.")
    for kat, dim, daftar in hasil:
        with st.container(key=f"kartu_g_ps_{kat}_{dim}"):
            st.markdown(f"**{e(nama_kat(kat))}** · per {per(dim)[0]}")
            murah = daftar[0][1]
            for i, (b, h) in enumerate(daftar):
                rinci = " · ".join(e(x) for x in (b.get("merek"), b.get("ukuran")) if x)
                selisih = f' · +{(h / murah - 1) * 100:.0f}% dari termurah' if i else ' · termurah '
                st.markdown(f'<div class="perhatian"><b>{e(b["nama"])}</b> ({rinci}) · {rp(round(h))} per {per(dim)[0]}{selisih}</div>', unsafe_allow_html=True)
    if tanpa:
        st.caption(f"{len(tanpa)} barang belum bisa dibandingkan karena ukuran kemasannya kosong atau tidak terbaca.")
