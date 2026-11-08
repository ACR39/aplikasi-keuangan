"""Beranda: ringkasan bulan, hal yang perlu perhatian, saldo dompet, anggaran, tabungan, dan grafik."""
import pandas as pd
import streamlit as st

from keuangan.anggaran import status_anggaran
from keuangan.bantu import (
    atur, baris_transaksi, batang, deretan_stat, dompet_aktif, e, geser_bulan, kartu_stat, nama_kat, per_kategori,
    pilih_bulan, pindah_halaman, ringkas_bulan, saldo_dompet, total_saldo, ym_ini,
)
from keuangan.inti import D, fmt_iso, hanya_lihat, nama_bulan, rp
from keuangan.tabungan import terkumpul
from keuangan.tagihan import status_tagihan, tagihan_mendekat
from keuangan.utang import jatuh_tempo_dekat, sisa

SEKSI_BERANDA = [("ringkasan", "Ringkasan angka"), ("perhatian", "Perlu perhatian"), ("dompet", "Saldo per dompet"),
                 ("anggaran", "Anggaran bulan ini"), ("tabungan", "Target tabungan"), ("g_kategori", "Grafik pengeluaran per kategori"),
                 ("g_tren", "Grafik 6 bulan terakhir"), ("terakhir", "Transaksi terakhir")]


def disembunyikan() -> list:
    return D.get("pengaturan", {}).get("beranda", [])


def _perhatian() -> list:
    baris = []
    for t in tagihan_mendekat(7):
        teks, _ = status_tagihan(t)
        baris.append(f'⏰ Tagihan <b>{e(t["nama"])}</b> {rp(t["jumlah"])}: {teks.lower()} ({fmt_iso(t["berikut"])})')
    for u in jatuh_tempo_dekat(7):
        arah = "bayar utang ke" if u["arah"] == "utang" else "tagih piutang dari"
        baris.append(f'🤝 Waktunya {arah} <b>{e(u["orang"])}</b>: sisa {rp(sisa(u))} (tenggat {fmt_iso(u["tenggat"])})')
    for a, pakai, persen in status_anggaran(ym_ini()):
        if persen >= 100:
            baris.append(f'🔴 Anggaran <b>{e(nama_kat(a["kategori"]))}</b> terlewati: {rp(pakai)} dari {rp(a["batas"])}')
        elif persen >= 80:
            baris.append(f'🟡 Anggaran <b>{e(nama_kat(a["kategori"]))}</b> sudah {persen:.0f}% ({rp(pakai)} dari {rp(a["batas"])})')
    for d in dompet_aktif():
        if saldo_dompet(d["id"]) < 0 and d.get("jenis") != "Kartu kredit":
            baris.append(f'⚠️ Saldo dompet <b>{e(d["nama"])}</b> negatif: {rp(saldo_dompet(d["id"]))}. Cek transaksi atau saldo awalnya.')
    return baris


def halaman_beranda():
    ym = pilih_bulan("br_bulan")
    sembunyi = disembunyikan()
    masuk, keluar = ringkas_bulan(ym)
    if "ringkasan" not in sembunyi:
        deretan_stat(kartu_stat("Total saldo", rp(total_saldo()), "semua dompet aktif", "g" if total_saldo() >= 0 else "m"),
                     kartu_stat("Pemasukan", rp(masuk), nama_bulan(ym), "g"),
                     kartu_stat("Pengeluaran", rp(keluar), nama_bulan(ym), "m"),
                     kartu_stat("Selisih", rp(masuk - keluar), "ditabung" if masuk >= keluar else "defisit",
                                "g" if masuk >= keluar else "m"))
    if "perhatian" not in sembunyi:
        with st.container(key="kartu_perhatian"):
            st.markdown("**Perlu perhatian**")
            hal = _perhatian()
            if not hal:
                st.caption("Tidak ada yang mendesak. Tagihan, utang, dan anggaran aman.")
            for h in hal:
                st.markdown(f'<div class="perhatian">{h}</div>', unsafe_allow_html=True)
    if "dompet" not in sembunyi:
        st.markdown("**Saldo per dompet**")
        if not dompet_aktif():
            st.info("Belum ada dompet aktif. Tambahkan di Pengaturan > Dompet.")
        kartu = "".join(f'<div class="dk1"><div class="j">{e(d.get("jenis", ""))}</div><div class="n">{e(d["nama"])}</div>'
                        f'<div class="s{" neg" if saldo_dompet(d["id"]) < 0 else ""}">{rp(saldo_dompet(d["id"]))}</div></div>'
                        for d in dompet_aktif())
        st.markdown(f'<div class="dompet-k">{kartu}</div>', unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    with c1:
        if "anggaran" not in sembunyi:
            with st.container(key="kartu_g_br_anggaran"):
                st.markdown("**Anggaran**")
                dt = status_anggaran(ym)[:6]
                if not dt:
                    st.caption("Belum ada anggaran.")
                for a, pakai, persen in dt:
                    st.markdown(f'<div class="ag"><b>{e(nama_kat(a["kategori"]))}</b><span>{rp(pakai)} / {rp(a["batas"])}</span></div>'
                                f'{batang(pakai, a["batas"])}', unsafe_allow_html=True)
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
                    st.markdown(f'<div class="ag"><b>{e(g["nama"])}</b><span>{rp(kum)} / {rp(g["target"])}</span></div>'
                                f'{batang(kum, g["target"], "bl" if kum < g["target"] else "")}', unsafe_allow_html=True)
                st.button("Kelola target", key="lompat_tab", on_click=pindah_halaman, args=("Target tabungan",))
    d1, d2 = st.columns(2)
    with d1:
        if "g_kategori" not in sembunyi:
            with st.container(key="kartu_g_br_kat"):
                st.markdown(f"**Pengeluaran per kategori, {nama_bulan(ym)}**")
                data = per_kategori(ym, "keluar")
                if data:
                    st.bar_chart(pd.DataFrame({"Kategori": [nama_kat(k) for k in data], "Jumlah": list(data.values())}).set_index("Kategori"),
                                 color="#d64545", horizontal=True)
                else:
                    st.caption("Belum ada pengeluaran bulan ini.")
    with d2:
        if "g_tren" not in sembunyi:
            with st.container(key="kartu_g_br_tren"):
                st.markdown("**6 bulan terakhir**")
                bln = [geser_bulan(ym_ini(), -i) for i in range(5, -1, -1)]
                label = [nama_bulan(b)[:3] + " " + b[2:4] for b in bln]
                st.bar_chart(pd.DataFrame({"Bulan": label, "Pemasukan": [ringkas_bulan(b)[0] for b in bln],
                                           "Pengeluaran": [ringkas_bulan(b)[1] for b in bln]}).set_index("Bulan"),
                             color=["#34a874", "#d64545"], stack=False)
    if "terakhir" not in sembunyi:
        with st.container(key="kartu_g_br_terakhir"):
            st.markdown("**Transaksi terakhir**")
            terakhir = sorted(D["transaksi"], key=lambda t: (t["tgl"], t.get("dibuat", "")), reverse=True)[:6]
            if not terakhir:
                st.caption("Belum ada transaksi. Mulai dari menu Catat transaksi.")
            for t in terakhir:
                st.markdown(f'<div class="perhatian">{baris_transaksi(t)}</div>', unsafe_allow_html=True)
            if D["transaksi"]:
                st.button("Lihat semua transaksi", key="lompat_tr", on_click=pindah_halaman, args=("Daftar transaksi",))
