"""Laporan tambahan: perbandingan kuartal/tahun per kategori, laporan bulanan yang bisa diunduh, dan saran anggaran dari riwayat."""
import html
import math
from datetime import date

import pandas as pd
import streamlit as st

from keuangan.bantu import akar, baru_id, catat, kat_dari, nama_kat, per_kategori, ringkas_bulan, selesai_simpan, toko_dari, transaksi_bulan, versi
from keuangan.inti import D, fmt_iso, hari_ini, nama_bulan, rp

NAMA_KUARTAL = {1: "Jan–Mar", 2: "Apr–Jun", 3: "Jul–Sep", 4: "Okt–Des"}


def _bulan_periode(tahun: int, kuartal: int | None) -> list:
    bln = range(1, 13) if not kuartal else range(3 * kuartal - 2, 3 * kuartal + 1)
    return [f"{tahun}-{m:02d}" for m in bln]


def total_periode(bulan: list) -> dict:
    """{'masuk', 'keluar', 'kat': {id kategori utama: total keluar}} untuk beberapa bulan."""
    kat, masuk, keluar = {}, 0, 0
    for ym in bulan:
        m, k = ringkas_bulan(ym)
        masuk += m
        keluar += k
        for i, v in per_kategori(ym, "keluar", gabung=True).items():
            kat[i] = kat.get(i, 0) + v
    return {"masuk": masuk, "keluar": keluar, "kat": kat}


def _pct(skrg: int, lalu: int) -> str:
    return f"{(skrg - lalu) / lalu * 100:+.0f}%" if lalu else "-"


def halaman_periode():
    ys = sorted({int(t["tgl"][:4]) for t in D["transaksi"]}, reverse=True) or [hari_ini().year]
    c1, c2, c3 = st.columns(3)
    mode = c1.radio("Periode", ["Kuartal", "Tahun"], horizontal=True, key="lp_per_mode")
    y = c2.selectbox("Tahun", ys, key="lp_per_tahun")
    kw = None
    if mode == "Kuartal":
        kw = c3.selectbox("Kuartal", [1, 2, 3, 4], index=(hari_ini().month - 1) // 3, format_func=lambda q: f"K{q} ({NAMA_KUARTAL[q]})", key="lp_per_kw")
    pilihan = ["Periode yang sama tahun lalu"] + (["Kuartal sebelumnya"] if kw else [])
    banding = st.radio("Bandingkan dengan", pilihan, horizontal=True, key="lp_per_banding")
    if kw and banding == "Kuartal sebelumnya":
        yl, kl = (y, kw - 1) if kw > 1 else (y - 1, 4)
    else:
        yl, kl = y - 1, kw
    nama_ini = f"K{kw} {y}" if kw else str(y)
    nama_lalu = f"K{kl} {yl}" if kl else str(yl)
    a, b = total_periode(_bulan_periode(y, kw)), total_periode(_bulan_periode(yl, kl))
    if not a["masuk"] and not a["keluar"]:
        st.info("Belum ada transaksi di periode ini.")
        return
    from keuangan.bantu import deretan_stat, kartu_stat
    deretan_stat(kartu_stat("Pemasukan", rp(a["masuk"]), f"{_pct(a['masuk'], b['masuk'])} vs {nama_lalu}", "g"),
                 kartu_stat("Pengeluaran", rp(a["keluar"]), f"{_pct(a['keluar'], b['keluar'])} vs {nama_lalu}", "m"),
                 kartu_stat("Selisih", rp(a["masuk"] - a["keluar"]), nama_ini, "g" if a["masuk"] >= a["keluar"] else "m"))
    ids = sorted(set(a["kat"]) | set(b["kat"]), key=lambda i: -(a["kat"].get(i, 0)))
    baris = [{"Kategori": nama_kat(i), nama_ini: a["kat"].get(i, 0), nama_lalu: b["kat"].get(i, 0), "Selisih": a["kat"].get(i, 0) - b["kat"].get(i, 0),
              "Perubahan": _pct(a["kat"].get(i, 0), b["kat"].get(i, 0))} for i in ids]
    st.markdown("**Pengeluaran per kategori utama**")
    st.dataframe(pd.DataFrame(baris), hide_index=True, use_container_width=True,
                 column_config={x: st.column_config.NumberColumn(format="Rp %d") for x in (nama_ini, nama_lalu, "Selisih")})
    naik = [r for r in baris if r["Selisih"] > 0]
    if naik:
        t = max(naik, key=lambda r: r["Selisih"])
        st.caption(f"Kenaikan terbesar: {t['Kategori']} ({rp(t['Selisih'])} lebih banyak dari {nama_lalu}).")
    st.caption("Pengeluaran per kategori utama sudah mencakup semua sub kategorinya; transfer tidak dihitung kecuali biayanya.")


# ---------------------------------------------------------------- laporan bulanan yang bisa dibagikan
def html_bulan(ym: str) -> str:
    h = html.escape
    y, m = int(ym[:4]), int(ym[5:])
    prev = f"{y - 1}-12" if m == 1 else f"{y}-{m - 1:02d}"
    masuk, keluar = ringkas_bulan(ym)
    masuk_l, keluar_l = ringkas_bulan(prev)
    kat, kat_l = per_kategori(ym, "keluar", gabung=True), per_kategori(prev, "keluar", gabung=True)
    tampil = lambda s, l: f" ({_pct(s, l)} vs {h(nama_bulan(prev))})" if l else ""
    maks = max(kat.values(), default=1)
    baris_kat = "".join(f"<tr><td>{h(nama_kat(i))}</td><td class=b><div style='width:{v / maks * 100:.0f}%'></div></td><td>{rp(v)}</td><td>{_pct(v, kat_l.get(i, 0))}</td></tr>"
                        for i, v in sorted(kat.items(), key=lambda x: -x[1])[:12])
    toko = {}
    for t in transaksi_bulan(ym):
        if t["jenis"] == "keluar" and t.get("toko"):
            a = toko.setdefault(t["toko"], [0, set()])
            a[0] += int(t["jumlah"])
            a[1].add(t.get("grup") or t["id"])
    li_toko = "".join(f"<li>{h((toko_dari(i) or {}).get('nama', '?'))}: {rp(v[0])} ({len(v[1])} kunjungan)</li>" for i, v in sorted(toko.items(), key=lambda x: -x[1][0])[:5])
    besar = sorted((t for t in transaksi_bulan(ym) if t["jenis"] == "keluar"), key=lambda t: -int(t["jumlah"]))[:5]
    from keuangan.bantu import ringkas_teks
    li_besar = "".join(f"<li>{h(fmt_iso(t['tgl']))} · {h(ringkas_teks(t))}</li>" for t in besar)
    from keuangan.harga_naik import kenaikan
    try:
        naik = [x for x in kenaikan(10, date(y, m, 28) if m != 2 else date(y, m, 28)) if x["tgl"][:7] == ym][:5]
    except Exception:
        naik = []
    li_naik = "".join(f"<li>{h(x['nama'])}: {rp(x['lalu'])} → {rp(x['baru'])} (+{x['persen']:.0f}%)</li>" for x in naik)
    bag = [f"<h1>Laporan keuangan {h(nama_bulan(ym))}</h1>",
           "<h2>Ringkasan</h2><ul>"
           f"<li>Pemasukan: <b>{rp(masuk)}</b>{tampil(masuk, masuk_l)}</li>"
           f"<li>Pengeluaran: <b>{rp(keluar)}</b>{tampil(keluar, keluar_l)}</li>"
           f"<li>Selisih: <b>{rp(masuk - keluar)}</b>" + (f" ({(masuk - keluar) / masuk * 100:.0f}% dari pemasukan)" if masuk else "") + "</li></ul>"]
    if baris_kat:
        bag.append(f"<h2>Pengeluaran per kategori</h2><table>{baris_kat}</table>")
    if li_toko:
        bag.append(f"<h2>Toko teratas</h2><ul>{li_toko}</ul>")
    if li_besar:
        bag.append(f"<h2>Pengeluaran terbesar</h2><ul>{li_besar}</ul>")
    if li_naik:
        bag.append(f"<h2>Harga yang naik</h2><ul>{li_naik}</ul>")
    css = ("body{font-family:system-ui,sans-serif;max-width:720px;margin:2rem auto;padding:0 1rem;color:#0b1220}h1{color:#1f6b49}"
           "h2{border-bottom:2px solid #34a874;padding-bottom:.2rem;margin-top:1.8rem}table{border-collapse:collapse;width:100%}"
           "td{border-bottom:1px solid #e2e8f0;padding:.3rem .5rem;text-align:right}td:first-child{text-align:left}"
           "td.b{width:30%}td.b div{height:.6rem;background:#34a874;border-radius:3px}@media print{body{margin:0}}")
    return f"<!doctype html><html lang='id'><meta charset='utf-8'><title>Laporan {h(nama_bulan(ym))}</title><style>{css}</style><body>{''.join(bag)}</body></html>"


def tombol_unduh_bulan(ym: str):
    from keuangan.pdf import html_ke_pdf
    a, b = st.columns(2)
    a.download_button("Unduh PDF", html_ke_pdf(html_bulan(ym), f"Laporan {ym}"), file_name=f"laporan-{ym}.pdf", mime="application/pdf", key=f"unduh_pdf_bln_{ym}")
    b.download_button("Unduh HTML", html_bulan(ym).encode("utf-8"), file_name=f"laporan-{ym}.html", mime="text/html", key=f"unduh_bln_{ym}")


# ---------------------------------------------------------------- saran anggaran dari riwayat
def saran_anggaran(n_bulan: int = 3) -> list:
    """[(id kategori utama, rata-rata per bulan, saran batas)] untuk kategori utama pengeluaran yang belum punya anggaran.
    Memakai n_bulan bulan penuh terakhir yang ada transaksinya; kosong bila datanya kurang dari dua bulan."""
    h = hari_ini()
    ini = h.strftime("%Y-%m")
    ada = sorted({t["tgl"][:7] for t in D["transaksi"] if t["jenis"] == "keluar" and t["tgl"][:7] < ini}, reverse=True)[:n_bulan]
    if len(ada) < 2:
        return []
    total = {}
    for ym in ada:
        for i, v in per_kategori(ym, "keluar", gabung=True).items():
            total[i] = total.get(i, 0) + v
    punya = {a["kategori"] for a in D["anggaran"] if a.get("tipe", "kategori") == "kategori"}
    punya |= {akar(x) for x in punya}
    hasil = []
    for i, v in total.items():
        if not i or not kat_dari(i) or i in punya:
            continue
        rata = v / len(ada)
        if rata < 20000:
            continue
        hasil.append((i, round(rata), int(math.ceil(rata / 10000) * 10000)))
    return sorted(hasil, key=lambda x: -x[1])


def panel_saran_anggaran():
    saran = saran_anggaran()
    with st.expander("💡 Saran batas dari riwayat"):
        if not saran:
            st.caption("Belum ada saran: perlu pengeluaran dari minimal dua bulan sebelum bulan ini, atau semua kategori besar sudah punya anggaran.")
            return
        st.caption("Rata-rata pengeluaran per bulan dari bulan-bulan penuh terakhir (maks 3), dibulatkan ke atas ke Rp 10.000. Ubah angkanya bila perlu, centang yang mau dibuat.")
        df = pd.DataFrame([{"Pakai": True, "Kategori": nama_kat(i), "Rata-rata": r, "Batas": s} for i, r, s in saran])
        ed = st.data_editor(df, hide_index=True, use_container_width=True, disabled=["Kategori", "Rata-rata"], key=f"saran_ag_{versi()}",
                            column_config={"Rata-rata": st.column_config.NumberColumn(format="Rp %d"), "Batas": st.column_config.NumberColumn(format="Rp %d", min_value=0, step=10000)})
        pilih = [(saran[i][0], int(r["Batas"])) for i, r in ed.iterrows() if r["Pakai"] and int(r["Batas"]) > 0]
        if st.button(f"Buat {len(pilih)} anggaran", type="primary", key="saran_ag_buat", disabled=not pilih):
            for kid, batas in pilih:
                D["anggaran"].append({"id": baru_id(), "tipe": "kategori", "target": "", "kategori": kid, "batas": batas})
            catat("anggaran", f"Buat {len(pilih)} anggaran dari saran riwayat")
            selesai_simpan(f"{len(pilih)} anggaran dibuat.")


# ---------------------------------------------------------------- kekayaan bersih
def utang_pada(tgl: str) -> tuple:
    """(utang saya, piutang) yang masih tersisa pada tanggal tgl (ISO), dari tanggal utang dan tanggal tiap pembayaran."""
    utang = piutang = 0
    for u in D["utang"]:
        if u["tgl"] > tgl:
            continue
        sisa = int(u["jumlah"]) - sum(int(b["jumlah"]) for b in u.get("bayar", []) if b["tgl"] <= tgl)
        if u["arah"] == "utang":
            utang += max(sisa, 0)
        else:
            piutang += max(sisa, 0)
    return utang, piutang


def grafik_kekayaan(bulan: list, label: list):
    """Kekayaan bersih di akhir tiap bulan: total saldo dompet aktif + piutang - utang."""
    from keuangan.bantu import geser_bulan, saldo_dompet
    saldo, bersih = [], []
    for b in bulan:
        akhir = (pd.Timestamp(geser_bulan(b, 1) + "-01") - pd.Timedelta(days=1)).strftime("%Y-%m-%d")
        s = sum(saldo_dompet(d["id"], akhir) for d in D["dompet"] if not d.get("arsip"))
        u, p = utang_pada(akhir)
        saldo.append(s)
        bersih.append(s + p - u)
    with st.container(key="kartu_g_tren3"):
        st.markdown("**Kekayaan bersih di akhir tiap bulan**")
        st.line_chart(pd.DataFrame({"Bulan": label, "Total saldo": saldo, "Kekayaan bersih": bersih}).set_index("Bulan"), color=["#9aa7b8", "#34a874"])
        u, p = utang_pada("9999-12-31")
        st.caption(f"Kekayaan bersih = total saldo dompet aktif + piutang ({rp(p)}) - utang ({rp(u)}). Aset lain seperti emas, kendaraan, atau investasi tidak dihitung.")


# ---------------------------------------------------------------- biaya per pemakaian
def halaman_biaya_pakai():
    ada = [b for b in D["barang"] if b.get("umur_bulan") and b.get("harga")]
    if not ada:
        st.info("Belum ada barang dengan perkiraan umur pakai. Isi di Pengaturan > Data master > Barang dan produk, bagian Rincian lain.")
        return
    baris = [{"Barang": b["nama"], "Harga": int(b["harga"]), "Umur (bulan)": int(b["umur_bulan"]), "Per bulan": round(b["harga"] / b["umur_bulan"]),
              "Per hari": round(b["harga"] / (b["umur_bulan"] * 30.4))} for b in ada]
    baris.sort(key=lambda r: -r["Per bulan"])
    total = sum(r["Per bulan"] for r in baris)
    st.markdown(f"**Total biaya barang awet: {rp(total)} per bulan** ({rp(round(total / 30.4))} per hari)")
    st.dataframe(pd.DataFrame(baris), hide_index=True, use_container_width=True,
                 column_config={x: st.column_config.NumberColumn(format="Rp %d") for x in ("Harga", "Per bulan", "Per hari")})
    st.caption("Harga memakai harga beli terakhir barang. Umur pakai adalah perkiraan Anda sendiri.")
