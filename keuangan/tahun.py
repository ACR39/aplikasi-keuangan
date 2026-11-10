"""Laporan akhir tahun: ringkasan, rekor, kebiasaan belanja, dan perbandingan dengan tahun sebelumnya; bisa diunduh sebagai HTML."""
import html

import streamlit as st

from keuangan.bantu import akar, barang_dari, info_diskon, nama_kat, ringkas_teks, toko_dari
from keuangan.inti import D, fmt_iso, hari_ini, nama_bulan, rp

BLN = ["Jan", "Feb", "Mar", "Apr", "Mei", "Jun", "Jul", "Agu", "Sep", "Okt", "Nov", "Des"]


def _keluar(t):
    return int(t["jumlah"]) if t["jenis"] == "keluar" else int(t.get("biaya", 0) or 0) if t["jenis"] == "transfer" else 0


def daftar_tahun() -> list:
    ys = sorted({int(t["tgl"][:4]) for t in D["transaksi"]}, reverse=True)
    return ys or [hari_ini().year]


def data_tahun(y: int) -> dict:
    ts = [t for t in D["transaksi"] if t["tgl"][:4] == str(y)]
    lalu = [t for t in D["transaksi"] if t["tgl"][:4] == str(y - 1)]
    masuk = sum(int(t["jumlah"]) for t in ts if t["jenis"] == "masuk")
    keluar = sum(_keluar(t) for t in ts)
    keluar_lalu = sum(_keluar(t) for t in lalu)
    masuk_lalu = sum(int(t["jumlah"]) for t in lalu if t["jenis"] == "masuk")
    per_bln = [(sum(int(t["jumlah"]) for t in ts if t["jenis"] == "masuk" and int(t["tgl"][5:7]) == m),
                sum(_keluar(t) for t in ts if int(t["tgl"][5:7]) == m)) for m in range(1, 13)]
    kat, toko, brg, hari = {}, {}, {}, {}
    hemat = 0.0
    for t in ts:
        v = _keluar(t)
        if not v:
            continue
        hari[t["tgl"]] = hari.get(t["tgl"], 0) + v
        if t["jenis"] != "keluar":
            continue
        if t.get("kategori"):
            k = akar(t["kategori"])
            kat[k] = kat.get(k, 0) + v
        if t.get("toko"):
            a = toko.setdefault(t["toko"], [0, 0])
            a[0] += v
            a[1] += 1
        if t.get("barang"):
            a = brg.setdefault(t["barang"], [0, 0])
            a[0] += v
            a[1] += 1
        d = info_diskon(t)
        if d:
            hemat += d[1] * float(t.get("qty") or 1)
    besar = max((t for t in ts if t["jenis"] == "keluar"), key=lambda t: int(t["jumlah"]), default=None)
    bln_aktif = [i for i, (m, k) in enumerate(per_bln) if m or k]
    return {"tahun": y, "n": len(ts), "masuk": masuk, "keluar": keluar, "selisih": masuk - keluar, "masuk_lalu": masuk_lalu,
            "keluar_lalu": keluar_lalu, "per_bln": per_bln, "kat": sorted(kat.items(), key=lambda x: -x[1])[:5],
            "toko": sorted(toko.items(), key=lambda x: -x[1][0])[:5], "barang_sering": sorted(brg.items(), key=lambda x: -x[1][1])[:5],
            "hari_boros": max(hari.items(), key=lambda x: x[1]) if hari else None, "terbesar": besar, "hemat": round(hemat),
            "bln_boros": max(bln_aktif, key=lambda i: per_bln[i][1]) if bln_aktif else None,
            "rata_bulan": round(keluar / len(bln_aktif)) if bln_aktif else 0,
            "tabung_persen": round((masuk - keluar) / masuk * 100) if masuk else None}


def _banding(skrg: int, lalu: int) -> str:
    if not lalu:
        return ""
    p = (skrg - lalu) / lalu * 100
    return f"{'naik' if p > 0 else 'turun'} {abs(p):.0f}% dari tahun lalu"


def html_tahun(d: dict) -> str:
    h = html.escape
    baris = lambda judul, isi: f"<h2>{h(judul)}</h2>{isi}"
    li = lambda xs: "<ul>" + "".join(f"<li>{x}</li>" for x in xs) + "</ul>"
    nm = lambda i: h((toko_dari(i) or {}).get("nama", "?"))
    bln = "".join(f"<tr><td>{BLN[i]}</td><td>{rp(m)}</td><td>{rp(k)}</td></tr>" for i, (m, k) in enumerate(d["per_bln"]))
    bagian = [f"<h1>Laporan keuangan {d['tahun']}</h1><p>{d['n']} transaksi tercatat.</p>",
              baris("Ringkasan", li([f"Pemasukan: <b>{rp(d['masuk'])}</b> {h(_banding(d['masuk'], d['masuk_lalu']))}",
                                     f"Pengeluaran: <b>{rp(d['keluar'])}</b> {h(_banding(d['keluar'], d['keluar_lalu']))}",
                                     f"Selisih: <b>{rp(d['selisih'])}</b>" + (f" ({d['tabung_persen']}% dari pemasukan)" if d['tabung_persen'] is not None else ""),
                                     f"Rata-rata pengeluaran per bulan: {rp(d['rata_bulan'])}"] + ([f"Hemat dari diskon: <b>{rp(d['hemat'])}</b>"] if d["hemat"] else []))),
              baris("Per bulan", f"<table><tr><th>Bulan</th><th>Masuk</th><th>Keluar</th></tr>{bln}</table>")]
    if d["kat"]:
        bagian.append(baris("Kategori terbesar", li([f"{h(nama_kat(k))}: {rp(v)}" for k, v in d["kat"]])))
    if d["toko"]:
        bagian.append(baris("Toko favorit", li([f"{nm(i)}: {rp(v[0])} dalam {v[1]} kunjungan" for i, v in d["toko"]])))
    if d["barang_sering"]:
        bagian.append(baris("Barang paling sering dibeli", li([f"{h((barang_dari(i) or {}).get('nama', '?'))}: {v[1]} kali, {rp(v[0])}" for i, v in d["barang_sering"]])))
    rekor = []
    if d["bln_boros"] is not None:
        rekor.append(f"Bulan paling boros: {BLN[d['bln_boros']]} ({rp(d['per_bln'][d['bln_boros']][1])})")
    if d["hari_boros"]:
        rekor.append(f"Hari paling boros: {fmt_iso(d['hari_boros'][0])} ({rp(d['hari_boros'][1])})")
    if d["terbesar"]:
        rekor.append(f"Pengeluaran tunggal terbesar: {h(ringkas_teks(d['terbesar']))}")
    if rekor:
        bagian.append(baris("Rekor", li(rekor)))
    css = ("body{font-family:system-ui,sans-serif;max-width:720px;margin:2rem auto;padding:0 1rem;color:#0b1220}h1{color:#1f6b49}"
           "h2{border-bottom:2px solid #34a874;padding-bottom:.2rem;margin-top:1.8rem}table{border-collapse:collapse;width:100%}"
           "td,th{border-bottom:1px solid #e2e8f0;padding:.3rem .5rem;text-align:right}td:first-child,th:first-child{text-align:left}")
    return f"<!doctype html><html lang='id'><meta charset='utf-8'><title>Laporan {d['tahun']}</title><style>{css}</style><body>{''.join(bagian)}</body></html>"


def halaman_tahun():
    y = st.selectbox("Tahun", daftar_tahun(), key="th_tahun")
    d = data_tahun(y)
    if not d["n"]:
        st.info("Belum ada transaksi di tahun ini.")
        return
    from keuangan.bantu import deretan_stat, kartu_stat
    deretan_stat(kartu_stat("Pemasukan", rp(d["masuk"]), _banding(d["masuk"], d["masuk_lalu"]), "g"),
                 kartu_stat("Pengeluaran", rp(d["keluar"]), _banding(d["keluar"], d["keluar_lalu"]), "m"),
                 kartu_stat("Selisih", rp(d["selisih"]), f"{d['tabung_persen']}% dari pemasukan" if d["tabung_persen"] is not None else "", "g" if d["selisih"] >= 0 else "m"),
                 kartu_stat("Hemat diskon", rp(d["hemat"]), "dari harga normal"))
    import pandas as pd
    st.bar_chart(pd.DataFrame({"Pemasukan": [m for m, _ in d["per_bln"]], "Pengeluaran": [k for _, k in d["per_bln"]]}, index=BLN))
    if d["kat"]:
        st.markdown("**Kategori terbesar**")
        for k, v in d["kat"]:
            st.caption(f"{nama_kat(k)} · {rp(v)}")
    if d["toko"]:
        st.markdown("**Toko favorit**")
        for i, v in d["toko"]:
            st.caption(f"{(toko_dari(i) or {}).get('nama', '?')} · {rp(v[0])} · {v[1]} kunjungan")
    if d["barang_sering"]:
        st.markdown("**Barang paling sering dibeli**")
        for i, v in d["barang_sering"]:
            st.caption(f"{(barang_dari(i) or {}).get('nama', '?')} · {v[1]} kali · {rp(v[0])}")
    if d["hari_boros"]:
        st.caption(f"Hari paling boros: {fmt_iso(d['hari_boros'][0])} ({rp(d['hari_boros'][1])})")
    if d["terbesar"]:
        st.caption(f"Pengeluaran tunggal terbesar: {ringkas_teks(d['terbesar'])}")
    st.download_button("Unduh laporan (HTML, bisa dicetak jadi PDF)", html_tahun(d).encode("utf-8"), file_name=f"laporan-{y}.html", mime="text/html", key="th_unduh")
