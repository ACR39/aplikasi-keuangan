"""Deteksi harga barang yang naik, dihitung dari riwayat pembelian (tanpa AI), beserta toko yang lebih murah."""
from datetime import date, timedelta
from statistics import median

import streamlit as st

from keuangan.bantu import barang_dari, e, toko_dari, transaksi_barang
from keuangan.inti import D, fmt_iso, hari_ini, rp

AMBANG = 10  # persen
JENDELA_BANDING = 180  # hari sebelum pembelian terbaru
MAKS_USIA = 120  # pembelian terbaru harus dalam sekian hari terakhir


def _harga(t: dict) -> int:
    return int(t.get("harga_satuan") or 0)


def kenaikan(ambang: float = AMBANG, h: date | None = None) -> list:
    """Barang yang harga beli terbarunya naik minimal `ambang` persen dibanding median pembelian sebelumnya.
    Hasil: [{barang, nama, baru, tgl, toko, lalu, persen, n, murah}] terurut dari kenaikan terbesar.
    murah = (nama toko, harga) bila toko lain punya harga terakhir lebih rendah dari harga terbaru, kalau tidak None."""
    h = h or hari_ini()
    hasil = []
    for b in D["barang"]:
        ts = [t for t in transaksi_barang(b["id"]) if t["jenis"] == "keluar" and _harga(t) > 0]
        if len(ts) < 2:
            continue
        baru = ts[0]
        try:
            d_baru = date.fromisoformat(baru["tgl"])
        except ValueError:
            continue
        if (h - d_baru).days > MAKS_USIA:
            continue
        mulai = (d_baru - timedelta(days=JENDELA_BANDING)).isoformat()
        lalu = [_harga(t) for t in ts[1:] if mulai <= t["tgl"] <= baru["tgl"]] or [_harga(ts[1])]
        acuan = median(lalu)
        persen = (_harga(baru) - acuan) / acuan * 100
        if persen < ambang:
            continue
        per_toko = {}
        for t in ts:  # terbaru dulu: harga terakhir tiap toko
            if t.get("toko") and t["toko"] not in per_toko:
                per_toko[t["toko"]] = _harga(t)
        murah = None
        lain = {k: v for k, v in per_toko.items() if k != baru.get("toko") and v < _harga(baru)}
        if lain:
            k = min(lain, key=lain.get)
            murah = ((toko_dari(k) or {}).get("nama", "?"), lain[k])
        hasil.append({"barang": b["id"], "nama": b["nama"], "baru": _harga(baru), "tgl": baru["tgl"], "toko": (toko_dari(baru.get("toko")) or {}).get("nama", ""),
                      "lalu": round(acuan), "persen": persen, "n": len(lalu), "murah": murah})
    return sorted(hasil, key=lambda x: -x["persen"])


def baris_perhatian() -> list:
    """Satu baris ringkas untuk 'Perlu perhatian' di Beranda; kosong bila tidak ada kenaikan berarti."""
    k = kenaikan(15)
    if not k:
        return []
    t = k[0]
    lain = f" dan {len(k) - 1} barang lain" if len(k) > 1 else ""
    return [f'📈 Harga <b>{e(t["nama"])}</b> naik {t["persen"]:.0f}% ({rp(t["lalu"])} ke {rp(t["baru"])}){lain} (lihat Laporan > Harga naik)']


def halaman_harga_naik():
    st.caption(f"Membandingkan harga beli terbaru tiap barang dengan median pembelian sebelumnya (maks {JENDELA_BANDING} hari sebelumnya). "
               f"Hanya barang yang dibeli dalam {MAKS_USIA} hari terakhir dan sudah punya minimal dua catatan harga.")
    ambang = st.slider("Tampilkan kenaikan minimal (%)", 5, 50, AMBANG, step=5, key="hn_ambang")
    k = kenaikan(ambang)
    if not k:
        st.success("Tidak ada barang yang harganya naik di atas batas itu.")
        return
    st.markdown(f"**{len(k)} barang naik harga**")
    for x in k:
        with st.container(border=True):
            st.markdown(f"**{e(x['nama'])}** · naik {x['persen']:.0f}%")
            st.markdown(f"{rp(x['lalu'])} → **{rp(x['baru'])}** per satuan"
                        + (f" di {e(x['toko'])}" if x["toko"] else "") + f" ({fmt_iso(x['tgl'])}; acuan dari {x['n']} pembelian sebelumnya)")
            if x["murah"]:
                st.caption(f"Pernah lebih murah di {x['murah'][0]}: {rp(x['murah'][1])} (hemat {rp(x['baru'] - x['murah'][1])} per satuan).")
