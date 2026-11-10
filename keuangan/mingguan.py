"""Ringkasan mingguan untuk Beranda: pengeluaran, kategori terbesar, hari terboros, barang naik harga, dan hemat diskon."""
from datetime import date, timedelta

import streamlit as st

from keuangan.bantu import akar, barang_dari, e, info_diskon, nama_kat, transaksi_barang
from keuangan.inti import D, fmt_iso, hari_ini, rp

HARI = ["Senin", "Selasa", "Rabu", "Kamis", "Jumat", "Sabtu", "Minggu"]


def _keluar(t: dict) -> int:
    return int(t["jumlah"]) if t["jenis"] == "keluar" else int(t.get("biaya", 0) or 0) if t["jenis"] == "transfer" else 0


def _dalam(a: date, b: date) -> list:
    x, y = a.isoformat(), b.isoformat()
    return [t for t in D["transaksi"] if x <= t["tgl"] <= y]


def ringkasan(a: date, b: date) -> dict:
    """Angka-angka ringkasan untuk rentang a..b dan pembandingnya (rentang yang sama 7 hari sebelumnya)."""
    ts = _dalam(a, b)
    keluar = sum(_keluar(t) for t in ts)
    masuk = sum(int(t["jumlah"]) for t in ts if t["jenis"] == "masuk")
    sebelum = sum(_keluar(t) for t in _dalam(a - timedelta(days=7), b - timedelta(days=7)))
    per_kat, per_hari = {}, {}
    for t in ts:
        v = _keluar(t)
        if not v:
            continue
        if t["jenis"] == "keluar" and t.get("kategori"):
            k = akar(t["kategori"])
            per_kat[k] = per_kat.get(k, 0) + v
        per_hari[t["tgl"]] = per_hari.get(t["tgl"], 0) + v
    hemat = sum(info_diskon(t)[1] * float(t.get("qty") or 1) for t in ts if t["jenis"] == "keluar" and info_diskon(t))
    # barang yang harganya naik dibanding median 5 pembelian sebelum rentang ini
    naik = []
    ada = {t["barang"] for t in ts if t["jenis"] == "keluar" and t.get("barang") and t.get("harga_satuan")}
    for id_ in ada:
        sekarang = [int(t["harga_satuan"]) for t in ts if t.get("barang") == id_ and t.get("harga_satuan")]
        lalu = sorted(int(t["harga_satuan"]) for t in transaksi_barang(id_) if t.get("harga_satuan") and t["tgl"] < a.isoformat())[:5]
        if not lalu:
            continue
        ref = sorted(lalu)[len(lalu) // 2]
        rata = sum(sekarang) / len(sekarang)
        if rata >= ref * 1.10:
            naik.append((id_, ref, round(rata), round((rata - ref) / ref * 100)))
    naik.sort(key=lambda x: -x[3])
    boros = max(per_hari.items(), key=lambda x: x[1]) if per_hari else None
    return {"n": len(ts), "struk": len({t["grup"] for t in ts if t.get("grup")}), "keluar": keluar, "masuk": masuk, "sebelum": sebelum,
            "kategori": sorted(per_kat.items(), key=lambda x: -x[1])[:3], "boros": boros, "hemat": round(hemat), "naik": naik[:3]}


def kartu_mingguan():
    kini = hari_ini()
    senin = kini - timedelta(days=kini.weekday())
    pilih = st.radio("Pekan", ["lalu", "ini"], horizontal=True, key="br_pekan", label_visibility="collapsed",
                     format_func=lambda x: "Pekan lalu" if x == "lalu" else "Pekan ini (berjalan)")
    if pilih == "lalu":
        a, b = senin - timedelta(days=7), senin - timedelta(days=1)
    else:
        a, b = senin, kini
    r = ringkasan(a, b)
    with st.container(key="kartu_g_br_mingguan"):
        st.markdown(f"**Ringkasan {'pekan lalu' if pilih == 'lalu' else 'pekan ini'}** · {fmt_iso(a.isoformat())} – {fmt_iso(b.isoformat())}")
        if not r["n"]:
            st.caption("Belum ada transaksi pada rentang ini.")
            return
        if r["sebelum"]:
            p = (r["keluar"] - r["sebelum"]) / r["sebelum"] * 100
            banding = f"{'naik' if p > 0 else 'turun'} {abs(p):.0f}% dari {'pekan sebelumnya' if pilih == 'lalu' else 'rentang yang sama pekan lalu'}" if abs(p) >= 0.5 else "sama seperti pembandingnya"
        else:
            banding = "belum ada pembanding"
        st.markdown(f'<div class="ag"><b>Pengeluaran</b><span>{rp(r["keluar"])}</span></div>', unsafe_allow_html=True)
        st.caption(f"{banding} · pemasukan {rp(r['masuk'])} · {r['n']} transaksi" + (f" · {r['struk']} struk" if r["struk"] else ""))
        if r["kategori"]:
            st.markdown("**Kategori terbesar**")
            for k, v in r["kategori"]:
                st.markdown(f'<div class="ag"><b>{e(nama_kat(k))}</b><span>{rp(v)} · {v / r["keluar"] * 100:.0f}%</span></div>', unsafe_allow_html=True)
        if r["boros"]:
            tg = date.fromisoformat(r["boros"][0])
            st.caption(f"Hari paling boros: {HARI[tg.weekday()]} {fmt_iso(r['boros'][0])} ({rp(r['boros'][1])}).")
        if r["hemat"]:
            st.caption(f"🏷️ Hemat dari diskon: {rp(r['hemat'])}.")
        if r["naik"]:
            st.markdown("**Barang yang harganya naik**")
            for id_, ref, rata, pct in r["naik"]:
                st.markdown(f'<div class="ag"><b>{e((barang_dari(id_) or {}).get("nama", "?"))}</b><span>{rp(ref)} → {rp(rata)} · +{pct}%</span></div>',
                            unsafe_allow_html=True)
            st.caption("Dibandingkan dengan harga biasanya (median 5 pembelian sebelumnya).")
