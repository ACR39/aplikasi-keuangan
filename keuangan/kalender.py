"""Kalender tagihan: tagihan berulang, langganan, utang-piutang, gajian, pajak dan servis kendaraan dalam satu tampilan bulan."""
import calendar
from datetime import date, timedelta

import streamlit as st

from keuangan.bantu import e, maju_tgl
from keuangan.inti import D, fmt_iso, hari_ini, iso_ke_date, nama_bulan, rp

JENIS = {"tagihan": ("Tagihan", "#d9822b"), "langganan": ("Langganan", "#7a5fc7"), "utang": ("Utang dan piutang", "#c0463a"),
         "gajian": ("Gajian", "#2e9e6b"), "kendaraan": ("Kendaraan", "#3b7bbf")}
HARI = ["Sen", "Sel", "Rab", "Kam", "Jum", "Sab", "Min"]


def _ulang(awal: date | None, tiap: str, mulai: date, akhir: date) -> list:
    """Tanggal jatuh tempo dalam [mulai, akhir], diproyeksikan maju dari `awal`. Yang sudah lewat sebelum `mulai` dilompati."""
    if not awal:
        return []
    hasil, d, n = [], awal, 0
    while d <= akhir and n < 400:
        if d >= mulai:
            hasil.append(d)
        if tiap not in ("mingguan", "bulanan", "tiga_bulan", "tahunan"):
            break
        d, n = maju_tgl(d, tiap), n + 1
    return hasil


def _servis_jatuh(s: dict) -> date | None:
    d0 = iso_ke_date(s.get("tgl_terakhir"))
    if not d0 or not s.get("tiap_bulan"):
        return None
    y, b = divmod(d0.month - 1 + int(s["tiap_bulan"]), 12)
    y, b = d0.year + y, b + 1
    return date(y, b, min(d0.day, calendar.monthrange(y, b)[1]))


def kejadian(tahun: int, bulan: int) -> list:
    """Semua kejadian di bulan itu: [(tanggal, jenis, teks, jumlah)] terurut tanggal. jumlah 0 bila tidak berupa uang keluar."""
    mulai, akhir = date(tahun, bulan, 1), date(tahun, bulan, calendar.monthrange(tahun, bulan)[1])
    ev = []
    for t in D.get("tagihan", []):
        if t.get("aktif", True):
            for d in _ulang(iso_ke_date(t.get("berikut")), t.get("tiap", ""), mulai, akhir):
                ev.append((d, "tagihan", t["nama"], int(t["jumlah"]) if t.get("jenis", "keluar") == "keluar" else 0))
    for a in D.get("abonemen", []):
        if a.get("aktif", True):
            for d in _ulang(iso_ke_date(a.get("berikut")), a.get("tiap", ""), mulai, akhir):
                ev.append((d, "langganan", a["nama"] + (" (perpanjang)" if a.get("otomatis") else " (habis)"), int(a.get("jumlah") or 0)))
    from keuangan.utang import sisa
    for u in D.get("utang", []):
        d = iso_ke_date(u.get("tenggat"))
        if d and mulai <= d <= akhir and sisa(u) > 0:
            bayar = u["arah"] == "utang"
            ev.append((d, "utang", f"{'Bayar utang ke' if bayar else 'Tagih piutang dari'} {u['orang']}", sisa(u) if bayar else 0))
    from keuangan.gajian import hari_gajian
    hg = hari_gajian()
    if hg:
        ev.append((date(tahun, bulan, min(hg, akhir.day)), "gajian", "Gajian", 0))
    for k in D.get("kendaraan", []):
        d = iso_ke_date(k.get("pajak"))
        if d and mulai <= d <= akhir:
            ev.append((d, "kendaraan", f"Pajak {k['nama']}", 0))
        for s in k.get("servis", []):
            d = _servis_jatuh(s)
            if d and mulai <= d <= akhir:
                ev.append((d, "kendaraan", f"{s['nama']} {k['nama']}", 0))
    return sorted(ev, key=lambda x: (x[0], x[1]))


def terlambat() -> list:
    """Tagihan, langganan, dan utang yang jatuh temponya sudah lewat dan belum diurus."""
    h, hasil = hari_ini(), []
    for t in D.get("tagihan", []):
        d = iso_ke_date(t.get("berikut"))
        if t.get("aktif", True) and d and d < h:
            hasil.append((d, "tagihan", t["nama"], int(t["jumlah"])))
    for a in D.get("abonemen", []):
        d = iso_ke_date(a.get("berikut"))
        if a.get("aktif", True) and d and d < h:
            hasil.append((d, "langganan", a["nama"], int(a.get("jumlah") or 0)))
    return sorted(hasil)


def _grid(tahun: int, bulan: int, per_hari: dict) -> str:
    h = hari_ini()
    sel = ["<tr>" + "".join(f"<th>{x}</th>" for x in HARI) + "</tr>"]
    for minggu in calendar.Calendar(0).monthdayscalendar(tahun, bulan):
        baris = []
        for hr in minggu:
            if not hr:
                baris.append('<td class="kd kosong"></td>')
                continue
            d = date(tahun, bulan, hr)
            titik = "".join(f'<i style="background:{JENIS[j][1]}"></i>' for j in dict.fromkeys(x[1] for x in per_hari.get(d, [])))
            baris.append(f'<td class="kd{" kini" if d == h else ""}"><b>{hr}</b><div>{titik}</div></td>')
        sel.append("<tr>" + "".join(baris) + "</tr>")
    css = ("<style>.kal{width:100%;border-collapse:separate;border-spacing:3px;table-layout:fixed}.kal th{font-size:.72rem;font-weight:600;opacity:.6;padding:2px 0}"
           ".kal td.kd{height:3.1rem;vertical-align:top;border:1px solid rgba(128,128,128,.25);border-radius:8px;padding:3px 4px;font-size:.8rem}"
           ".kal td.kosong{border:none}.kal td.kini{border:2px solid #256b4a}.kal td.kd b{font-weight:600}"
           ".kal td.kd div{display:flex;gap:3px;flex-wrap:wrap;margin-top:3px}.kal td.kd i{width:7px;height:7px;border-radius:50%;display:inline-block}</style>")
    return css + f'<table class="kal">{"".join(sel)}</table>'


def halaman_kalender():
    h = hari_ini()
    opsi = []
    for i in range(-6, 13):
        t, m = divmod(h.year * 12 + h.month - 1 + i, 12)
        opsi.append((t, m + 1))
    ym = st.selectbox("Bulan", opsi, index=6, key="kal_ym", format_func=lambda x: nama_bulan(f"{x[0]}-{x[1]:02d}"))
    ev = kejadian(*ym)
    per_hari = {}
    for x in ev:
        per_hari.setdefault(x[0], []).append(x)
    st.markdown(_grid(*ym, per_hari), unsafe_allow_html=True)
    st.markdown(" ".join(f'<span style="font-size:.78rem;margin-right:.6rem"><i style="background:{w};width:8px;height:8px;border-radius:50%;display:inline-block"></i> {n}</span>'
                         for n, w in JENIS.values()), unsafe_allow_html=True)
    total = sum(x[3] for x in ev)
    if total:
        st.markdown(f"**Perkiraan keluar untuk tagihan bulan ini: {rp(total)}**")
    tl = terlambat() if ym == (h.year, h.month) else []
    if tl:
        st.warning("Terlambat: " + " · ".join(f"{x[2]} ({fmt_iso(x[0].isoformat())})" for x in tl))
    if not ev:
        st.info("Belum ada jadwal di bulan ini. Tambah tagihan berulang, langganan, tanggal gajian, atau tenggat utang, nanti muncul di sini.")
        return
    for d in sorted(per_hari):
        sisa_h = (d - h).days
        ket = "hari ini" if sisa_h == 0 else f"{sisa_h} hari lagi" if sisa_h > 0 else f"lewat {-sisa_h} hari"
        with st.container(border=True):
            st.markdown(f"**{fmt_iso(d.isoformat())}** · {ket}")
            for _, j, teks, jml in per_hari[d]:
                st.markdown(f'<span style="color:{JENIS[j][1]}">●</span> {e(teks)}' + (f" · {rp(jml)}" if jml else ""), unsafe_allow_html=True)
