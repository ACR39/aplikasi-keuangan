"""Beranda: ringkasan bulan, hal yang perlu perhatian, saldo dompet, anggaran, tabungan, dan grafik."""
import calendar
from datetime import date, timedelta

import pandas as pd
import streamlit as st

from keuangan.anggaran import hari_melewati, ikon_ag, jatah_hari_ini, label_ag, status_anggaran
from keuangan.bantu import (
    atur, sisa_hari_teks, baris_transaksi, batang, ikon_kat, kat_dari, kunci_urut, deretan_stat, dompet_aktif, e, geser_bulan, kartu_stat, nama_kat, per_kategori,
    pindah_halaman, saldo_dompet, total_saldo, ym_ini, akar, barang_dari, toko_dari,
)
from keuangan.inti import D, TGL_MAX, TGL_MIN, sisa_hari, fmt_iso, hanya_lihat, hari_ini, nama_bulan, rp
from keuangan.mingguan import kartu_mingguan
from keuangan.prakiraan import kartu_prakiraan, teks_ringkas
from keuangan.stok import baris_perhatian
from keuangan.tabungan import terkumpul
from keuangan.tagihan import status_tagihan, tagihan_mendekat
from keuangan.utang import jatuh_tempo_dekat, sisa

SEKSI_BERANDA = [("ringkasan", "Ringkasan angka"), ("harian", "Jatah pengeluaran hari ini"), ("perhatian", "Perlu perhatian"), ("mingguan", "Ringkasan mingguan"), ("prakiraan", "Prakiraan akhir bulan"), ("dompet", "Saldo per dompet"),
                 ("anggaran", "Anggaran periode ini"), ("tabungan", "Target tabungan"), ("g_kategori", "Grafik pengeluaran per kategori"),
                 ("g_tren", "Grafik pemasukan dan pengeluaran"), ("teratas", "Toko dan barang teratas"), ("terakhir", "Transaksi terakhir")]


def disembunyikan() -> list:
    return D.get("pengaturan", {}).get("beranda", [])


def _perhatian() -> list:
    baris = []
    for t in tagihan_mendekat(7):
        teks, _ = status_tagihan(t)
        baris.append(f'⏰ Tagihan <b>{e(t["nama"])}</b> {rp(t["jumlah"])}: {teks.lower()} ({fmt_iso(t["berikut"])})')
    j = jatah_hari_ini()
    if j and j[2] >= 100:
        baris.append(f'🔴 Pengeluaran hari ini {rp(j[0])} sudah melewati batas harian {rp(j[1])}')
    elif j and j[2] >= 80:
        baris.append(f'🟡 Pengeluaran hari ini {rp(j[0])}, sudah {j[2]:.0f}% dari batas harian {rp(j[1])}')
    for u in jatuh_tempo_dekat(7):
        arah = "bayar utang ke" if u["arah"] == "utang" else "tagih piutang dari"
        baris.append(f'🤝 Waktunya {arah} <b>{e(u["orang"])}</b>: sisa {rp(sisa(u))} (tenggat {fmt_iso(u["tenggat"])})')
    for a, pakai, persen in status_anggaran(ym_ini()):
        if persen >= 100:
            baris.append(f'🔴 Anggaran <b>{e(label_ag(a))}</b> terlewati: {rp(pakai)} dari {rp(a["batas"])}')
        elif persen >= 80:
            baris.append(f'🟡 Anggaran <b>{e(label_ag(a))}</b> sudah {persen:.0f}% ({rp(pakai)} dari {rp(a["batas"])})')
    for b_ in D["barang"]:
        n_ = sisa_hari(b_.get("kedaluwarsa"))
        if n_ is not None and n_ <= 14:
            baris.append(f'⏳ <b>{e(b_["nama"])}</b> {e(sisa_hari_teks(b_["kedaluwarsa"]))}')
    baris += baris_perhatian()
    if teks_ringkas():
        baris.append(teks_ringkas())
    from keuangan.langganan import jumlah_belum_dijadwalkan
    nl = jumlah_belum_dijadwalkan()
    if nl:
        baris.append(f"🔎 {nl} pengeluaran rutin belum dijadwalkan (lihat Transaksi berulang)")
    for d in dompet_aktif():
        if saldo_dompet(d["id"]) < 0 and d.get("jenis") != "Kartu kredit":
            baris.append(f'⚠️ Saldo dompet <b>{e(d["nama"])}</b> negatif: {rp(saldo_dompet(d["id"]))}. Cek transaksi atau saldo awalnya.')
    return baris


MODE = {"minggu": "Minggu", "bulan": "Bulan", "tahun": "Tahun", "custom": "Tanggal custom"}
BLN3 = ["Jan", "Feb", "Mar", "Apr", "Mei", "Jun", "Jul", "Agu", "Sep", "Okt", "Nov", "Des"]


def _senin(d: date) -> date:
    return d - timedelta(days=d.weekday())


def _teks_rentang(a: date, b: date) -> str:
    if a == b:
        return f"{a.day} {BLN3[a.month - 1]} {a.year}"
    if a.year == b.year:
        pertama = f"{a.day}" if a.month == b.month else f"{a.day} {BLN3[a.month - 1]}"
        return f"{pertama} – {b.day} {BLN3[b.month - 1]} {b.year}"
    return f"{a.day} {BLN3[a.month - 1]} {a.year} – {b.day} {BLN3[b.month - 1]} {b.year}"


def _tgl_awal() -> date:
    ada = [t["tgl"] for t in D["transaksi"]]
    return min([date.fromisoformat(x) for x in ada] + [hari_ini()]) if ada else hari_ini()


def pilih_periode():
    """Kembalikan (mode, awal, akhir, label, sebelumnya) untuk periode yang dipilih di Beranda."""
    kini = hari_ini()
    mode = st.radio("Periode", list(MODE), format_func=MODE.get, horizontal=True, key="br_mode", index=1, label_visibility="collapsed")
    if mode == "minggu":
        w, mulai = [], _senin(kini)
        while mulai >= _senin(_tgl_awal()):
            w.append(mulai.isoformat())
            mulai -= timedelta(days=7)
        if st.session_state.get("br_minggu") not in w:
            st.session_state["br_minggu"] = w[0]
        pil = st.selectbox("Minggu", w, key="br_minggu",
                           format_func=lambda s: _teks_rentang(date.fromisoformat(s), date.fromisoformat(s) + timedelta(days=6))
                           + (" (minggu ini)" if s == w[0] else ""))
        a = date.fromisoformat(pil)
        b = a + timedelta(days=6)
        prev = (a - timedelta(days=7), a - timedelta(days=1))
        label = "minggu ini" if pil == w[0] else _teks_rentang(a, b)
    elif mode == "bulan":
        ym = pilih_bulan_beranda()
        th, bl = int(ym[:4]), int(ym[5:7])
        a, b = date(th, bl, 1), date(th, bl, calendar.monthrange(th, bl)[1])
        pt, pb = (th, bl - 1) if bl > 1 else (th - 1, 12)
        prev = (date(pt, pb, 1), date(pt, pb, calendar.monthrange(pt, pb)[1]))
        label = nama_bulan(ym)
    elif mode == "tahun":
        tahun = list(range(kini.year, _tgl_awal().year - 1, -1))
        if st.session_state.get("br_tahun") not in tahun:
            st.session_state["br_tahun"] = kini.year
        th = st.selectbox("Tahun", tahun, key="br_tahun")
        a, b = date(th, 1, 1), date(th, 12, 31)
        prev = (date(th - 1, 1, 1), date(th - 1, 12, 31))
        label = str(th)
    else:
        if "br_custom" not in st.session_state:
            st.session_state["br_custom"] = (kini - timedelta(days=29), kini)
        r = st.date_input("Rentang tanggal", key="br_custom", min_value=TGL_MIN, max_value=TGL_MAX, format="DD/MM/YYYY",
                          help="Pilih tanggal awal lalu tanggal akhir.")
        if not isinstance(r, (tuple, list)) or len(r) < 2:
            st.caption("Pilih tanggal akhir untuk melihat ringkasan.")
            st.stop()
        a, b = r[0], r[1]
        n = (b - a).days + 1
        prev = (a - timedelta(days=n), a - timedelta(days=1))
        label = _teks_rentang(a, b)
    return mode, a, b, label, prev


def pilih_bulan_beranda() -> str:
    from keuangan.bantu import daftar_bulan
    bl = daftar_bulan()
    if st.session_state.get("br_bulan") not in bl:
        st.session_state["br_bulan"] = ym_ini()
    return st.selectbox("Bulan", bl, key="br_bulan", format_func=nama_bulan)


def _dalam(a: date, b: date) -> list:
    x, y = a.isoformat(), b.isoformat()
    return [t for t in D["transaksi"] if x <= t["tgl"] <= y]


def _ringkas(ts: list):
    masuk = sum(int(t["jumlah"]) for t in ts if t["jenis"] == "masuk")
    keluar = sum(int(t["jumlah"]) for t in ts if t["jenis"] == "keluar")
    biaya = sum(int(t.get("biaya", 0) or 0) for t in ts if t["jenis"] == "transfer")
    return masuk, keluar + biaya


def _banding(sekarang: int, lalu: int, naik_baik: bool) -> str:
    if not lalu:
        return "belum ada pembanding"
    p = (sekarang - lalu) / lalu * 100
    if abs(p) < 0.5:
        return "sama seperti periode lalu"
    return f"{'naik' if p > 0 else 'turun'} {abs(p):.0f}% dari periode lalu"


def _teratas(ts: list, kunci, n: int = 5):
    h = {}
    for t in ts:
        if t["jenis"] == "keluar":
            k = kunci(t)
            if k:
                h[k] = h.get(k, 0) + int(t["jumlah"])
    return sorted(h.items(), key=lambda x: -x[1])[:n]


def halaman_beranda():
    mode, a, b, label, prev = pilih_periode()
    ts = _dalam(a, b)
    sembunyi = disembunyikan()
    masuk, keluar = _ringkas(ts)
    pm, pk = _ringkas(_dalam(*prev))
    hari = (b - a).days + 1
    hari_lalu = max(1, (min(b, hari_ini()) - a).days + 1)  # periode berjalan: hitung sampai hari ini saja
    if "ringkasan" not in sembunyi:
        deretan_stat(kartu_stat("Total saldo", rp(total_saldo()), "semua dompet aktif", "g" if total_saldo() >= 0 else "m"),
                     kartu_stat("Pemasukan", rp(masuk), _banding(masuk, pm, True), "g"),
                     kartu_stat("Pengeluaran", rp(keluar), _banding(keluar, pk, False), "m"),
                     kartu_stat("Selisih", rp(masuk - keluar), "ditabung" if masuk >= keluar else "defisit",
                                "g" if masuk >= keluar else "m"))
        st.caption(f"{label} · {hari} hari · {len(ts)} transaksi · rata-rata pengeluaran {rp(round(keluar / hari_lalu))} per hari")
    j = jatah_hari_ini()
    if j and "harian" not in sembunyi:
        with st.container(key="kartu_g_br_harian"):
            terpakai, batas, persen = j
            st.markdown(f'<div class="ag"><b>📅 Jatah hari ini</b><span>{rp(terpakai)} / {rp(batas)}</span></div>'
                        f'{batang(terpakai, batas)}', unsafe_allow_html=True)
            st.caption(f"Sisa {rp(batas - terpakai)} hari ini." if terpakai <= batas else f"Melewati jatah {rp(terpakai - batas)} hari ini.")
            lewat = hari_melewati(hari_ini().strftime("%Y-%m"))
            if lewat:
                st.caption(f"Bulan ini {lewat} hari melewati batas harian.")
    if "perhatian" not in sembunyi:
        with st.container(key="kartu_perhatian"):
            st.markdown("**Perlu perhatian**")
            hal = _perhatian()
            if not hal:
                st.caption("Tidak ada yang mendesak. Tagihan, utang, dan anggaran aman.")
            for h in hal:
                st.markdown(f'<div class="perhatian">{h}</div>', unsafe_allow_html=True)
    if "mingguan" not in sembunyi:
        kartu_mingguan()
    if "prakiraan" not in sembunyi:
        kartu_prakiraan()
    if "dompet" not in sembunyi:
        st.markdown("**Saldo per dompet**")
        if not dompet_aktif():
            st.info("Belum ada dompet aktif. Tambahkan di Pengaturan > Dompet.")
        IKON_D = {"tunai": "💵", "bank": "🏦", "e-wallet": "📱", "ewallet": "📱", "kartu kredit": "💳", "investasi": "📈"}
        WARNA_D = {"tunai": "#34a874", "bank": "#3b82c4", "e-wallet": "#8b5cf6", "ewallet": "#8b5cf6", "kartu kredit": "#e0a63a", "investasi": "#0ea5a4"}
        total_pos = sum(max(0, saldo_dompet(d["id"])) for d in dompet_aktif()) or 1
        kartu = ""
        for d in dompet_aktif():
            sd, jn = saldo_dompet(d["id"]), (d.get("jenis") or "").lower()
            warna = WARNA_D.get(jn, "#64748b")
            sub = "" if (d.get("jenis") or "").lower() == d["nama"].lower() or not d.get("jenis") else f'<div class="j">{e(d["jenis"])}</div>'
            kartu += (f'<div class="dk2" style="--aksen:{warna};--aksen-lemah:{warna}22"><div class="h"><div class="i">{IKON_D.get(jn, "👛")}</div>'
                      f'<div><div class="n">{e(d["nama"])}</div>{sub}</div></div>'
                      f'<div class="s{" neg" if sd < 0 else ""}">{rp(sd)}</div>'
                      f'<div class="p">{round(max(0, sd) / total_pos * 100)}% dari total saldo</div></div>')
        st.markdown(f'<div class="dompet-k">{kartu}</div>', unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    with c1:
        if "anggaran" not in sembunyi:
            with st.container(key="kartu_g_br_anggaran"):
                ym = b.strftime("%Y-%m")
                st.markdown(f"**Anggaran, {nama_bulan(ym)}**")
                dt = status_anggaran(ym)[:6]
                if not dt:
                    st.caption("Belum ada anggaran.")
                for ag, pakai, persen in dt:
                    sisa = ag["batas"] - pakai
                    kls = "b" if persen > 100 else "w" if persen >= 80 else ""
                    ket = f"{rp(pakai)} dari {rp(ag['batas'])} · " + (f"sisa {rp(sisa)}" if sisa >= 0 else f"lewat {rp(-sisa)}")
                    st.markdown(f'<div class="kem"><div class="a">{ikon_ag(ag)}<span class="nm">{e(label_ag(ag))}</span>'
                                f'<span class="pc {kls}">{persen:.0f}%</span></div>{batang(pakai, ag["batas"])}<div class="kt">{ket}</div></div>',
                                unsafe_allow_html=True)
                if not hanya_lihat() or dt:
                    st.button("Kelola anggaran", key="lompat_ag", on_click=pindah_halaman, args=("Anggaran",))
    with c2:
        if "tabungan" not in sembunyi:
            with st.container(key="kartu_g_br_tabungan"):
                st.markdown("**Target tabungan**")
                if not D["tabungan"]:
                    st.caption("Belum ada target.")
                for g in D["tabungan"][:5]:
                    kum = terkumpul(g)
                    pers = kum / g["target"] * 100 if g["target"] else 0
                    kurang = max(0, g["target"] - kum)
                    ket = f"{rp(kum)} dari {rp(g['target'])} · " + ("tercapai 🎉" if kurang == 0 else f"kurang {rp(kurang)}")
                    st.markdown(f'<div class="kem"><div class="a"><span class="kc" style="background:#3b82c4">🎯</span><span class="nm">{e(g["nama"])}</span>'
                                f'<span class="pc {"" if kurang == 0 else "bl"}">{pers:.0f}%</span></div>'
                                f'{batang(kum, g["target"], "bl" if kurang else "")}<div class="kt">{ket}</div></div>', unsafe_allow_html=True)
                st.button("Kelola target", key="lompat_tab", on_click=pindah_halaman, args=("Target tabungan",))
    d1, d2 = st.columns(2)
    with d1:
        if "g_kategori" not in sembunyi:
            with st.container(key="kartu_g_br_kat"):
                st.markdown(f"**Pengeluaran per kategori, {label}**")
                data = dict(_teratas(ts, lambda t: akar(t.get("kategori", "")), 8))
                if data:
                    total_k = sum(j for _, j in _teratas(ts, lambda t: akar(t.get("kategori", "")), 999)) or 1
                    puncak = max(data.values()) or 1
                    html = ""
                    for n, (k, jml) in enumerate(data.items(), 1):
                        warna = (kat_dari(k) or {}).get("warna", "#9aa0a6")
                        html += (f'<div class="top-r">{ikon_kat(k)}<div class="tm"><div class="tn">{e(nama_kat(k))}</div>'
                                 f'<div class="ts">{jml / total_k * 100:.0f}% dari pengeluaran</div>'
                                 f'<div class="bar"><i style="width:{jml / puncak * 100:.0f}%;background:{e(warna)}"></i></div></div>'
                                 f'<div class="tj">{rp(jml)}</div></div>')
                    st.markdown(html, unsafe_allow_html=True)
                else:
                    st.caption("Belum ada pengeluaran pada periode ini.")
    with d2:
        if "g_tren" not in sembunyi:
            with st.container(key="kartu_g_br_tren"):
                bulanan = mode == "tahun" or hari > 62
                masuk_juga = st.toggle("Tampilkan pemasukan", key="br_tren_masuk", help="Pemasukan (misalnya gaji) biasanya jauh lebih besar dan membuat batang pengeluaran sulit terlihat.")
                st.markdown(f"**{'Pemasukan dan pengeluaran' if masuk_juga else 'Pengeluaran'} {'per bulan' if bulanan else 'per hari'}**")
                if bulanan:
                    kunci_g = {}
                    y, m = a.year, a.month
                    while (y, m) <= (b.year, b.month):
                        kunci_g[f"{y:04d}-{m:02d}"] = f"{BLN3[m - 1]} {str(y)[2:]}"
                        y, m = (y + 1, 1) if m == 12 else (y, m + 1)
                    pot = 7
                else:
                    kunci_g = {(a + timedelta(days=i)).isoformat(): (a + timedelta(days=i)).strftime("%d/%m") for i in range(hari)}
                    pot = 10
                mm, kk = dict.fromkeys(kunci_g, 0), dict.fromkeys(kunci_g, 0)
                for tt in ts:
                    g = tt["tgl"][:pot]
                    if g in mm:
                        if tt["jenis"] == "masuk":
                            mm[g] += int(tt["jumlah"])
                        elif tt["jenis"] == "keluar":
                            kk[g] += int(tt["jumlah"])
                        elif tt["jenis"] == "transfer":
                            kk[g] += int(tt.get("biaya", 0) or 0)
                if masuk_juga:
                    st.bar_chart(pd.DataFrame({"Waktu": list(kunci_g.values()), "Pemasukan": list(mm.values()),
                                               "Pengeluaran": list(kk.values())}).set_index("Waktu"),
                                 color=["#34a874", "#d64545"], stack=False)
                else:
                    st.bar_chart(pd.DataFrame({"Waktu": list(kunci_g.values()), "Pengeluaran": list(kk.values())}).set_index("Waktu"),
                                 color="#d64545")
                    if any(kk.values()):
                        puncak = max(kk, key=kk.get)
                        st.caption(f"Tertinggi {kunci_g[puncak]}: {rp(kk[puncak])} · rata-rata {rp(round(sum(kk.values()) / len(kk)))} per {'bulan' if bulanan else 'hari'}")
    if "teratas" not in sembunyi:
        with st.container(key="kartu_g_br_teratas"):
            st.markdown(f"**Toko dan barang teratas, {label}**")
            e1, e2 = st.columns(2)
            from keuangan.bantu import jumlah_kunjungan
            for kol, judul, kunci_t, nama, satuan in (
                    (e1, "🏪 Toko", lambda t: t.get("toko"), lambda i: (toko_dari(i) or {}).get("nama", ""), "kunjungan"),
                    (e2, "🛒 Barang", lambda t: t.get("barang"), lambda i: (barang_dari(i) or {}).get("nama", ""), "kali dibeli")):
                with kol:
                    isi = _teratas(ts, kunci_t)
                    html = f'<div class="top-h">{judul}</div>'
                    if not isi:
                        html += '<div class="sub-rinci">Belum ada data pada periode ini.</div>'
                    puncak = max((j for _, j in isi), default=1) or 1
                    for n, (i, jml) in enumerate(isi, 1):
                        kali = jumlah_kunjungan([t for t in ts if kunci_t(t) == i and t["jenis"] == "keluar"])
                        html += (f'<div class="top-r"><span class="no">{n}</span><div class="tm"><div class="tn">{e(nama(i))}</div>'
                                 f'<div class="ts">{kali} {satuan}</div><div class="bar bl"><i style="width:{jml / puncak * 100:.0f}%"></i></div></div>'
                                 f'<div class="tj">{rp(jml)}</div></div>')
                    st.markdown(html, unsafe_allow_html=True)
    if "terakhir" not in sembunyi:
        with st.container(key="kartu_g_br_terakhir"):
            st.markdown("**Transaksi terakhir**")
            terakhir = sorted(D["transaksi"], key=kunci_urut, reverse=True)[:6]
            if not terakhir:
                st.caption("Belum ada transaksi. Mulai dari menu Catat transaksi.")
            for t in terakhir:
                st.markdown(f'<div class="perhatian">{baris_transaksi(t)}</div>', unsafe_allow_html=True)
            if D["transaksi"]:
                st.button("Lihat semua transaksi", key="lompat_tr", on_click=pindah_halaman, args=("Daftar transaksi",))
