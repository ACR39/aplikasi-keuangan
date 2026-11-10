"""Prakiraan akhir bulan: proyeksi pengeluaran, kemungkinan anggaran terlewati, dan batas harian yang aman."""
import calendar
from datetime import date, timedelta

import streamlit as st

from keuangan.anggaran import label_ag, status_anggaran
from keuangan.bantu import batang, e
from keuangan.inti import D, hari_ini, rp


def _keluar(t: dict) -> int:
    return int(t["jumlah"]) if t["jenis"] == "keluar" else int(t.get("biaya", 0) or 0) if t["jenis"] == "transfer" else 0


def tagihan_sisa_bulan(h: date) -> int:
    """Total tagihan keluar aktif yang jatuh tempo sampai akhir bulan dan belum dicatat."""
    akhir = date(h.year, h.month, calendar.monthrange(h.year, h.month)[1]).isoformat()
    return sum(int(t["jumlah"]) for t in D["tagihan"]
               if t.get("aktif", True) and t.get("jenis", "keluar") == "keluar" and t.get("berikut") and t["berikut"] <= akhir)


def prakiraan(h: date | None = None) -> dict | None:
    """Hitung prakiraan bulan berjalan. None bila belum ada data pengeluaran bulan ini."""
    h = h or hari_ini()
    ym = h.strftime("%Y-%m")
    n_hari = calendar.monthrange(h.year, h.month)[1]
    sisa = n_hari - h.day
    ts = [t for t in D["transaksi"] if t["tgl"][:7] == ym and t["tgl"] <= h.isoformat()]
    terpakai = sum(_keluar(t) for t in ts)
    if not terpakai:
        return None
    # laju harian variabel: 14 hari terakhir, tanpa transaksi yang berasal dari tagihan (sifatnya sekali sebulan)
    a = (h - timedelta(days=13)).isoformat()
    var = sum(_keluar(t) for t in D["transaksi"] if a <= t["tgl"] <= h.isoformat() and not t.get("tagihan"))
    laju = var / 14
    tagihan = tagihan_sisa_bulan(h)
    proyeksi = terpakai + tagihan + round(laju * sisa)
    return {"ym": ym, "terpakai": terpakai, "laju": round(laju), "tagihan": tagihan, "sisa_hari": sisa, "proyeksi": proyeksi,
            "n_hari": n_hari}


def prakiraan_anggaran(h: date | None = None) -> list:
    """[(anggaran, terpakai, proyeksi, tanggal_lewat | None)] untuk anggaran yang diperkirakan terlewati."""
    h = h or hari_ini()
    n_hari = calendar.monthrange(h.year, h.month)[1]
    hasil = []
    for ag, pakai, persen in status_anggaran(h.strftime("%Y-%m")):
        if not ag["batas"] or not pakai:
            continue
        proy = round(pakai / max(1, h.day) * n_hari)
        if proy <= ag["batas"]:
            continue
        lewat = None
        if pakai < ag["batas"]:
            hari_ke = int(ag["batas"] / (pakai / max(1, h.day))) + 1
            if hari_ke <= n_hari:
                lewat = date(h.year, h.month, hari_ke)
        hasil.append((ag, pakai, proy, lewat))
    return hasil


def total_batas() -> int:
    return sum(int(a["batas"]) for a in D["anggaran"] if not a.get("tipe") or a.get("tipe") == "kategori")


def teks_ringkas() -> str:
    """Satu kalimat untuk bagian 'Perlu perhatian'; '' bila tidak ada yang perlu dikhawatirkan."""
    p = prakiraan()
    if not p:
        return ""
    b = total_batas()
    if b and p["proyeksi"] > b:
        return f'📈 Prakiraan pengeluaran bulan ini {rp(p["proyeksi"])}, <b>melebihi</b> total anggaran {rp(b)} sekitar {rp(p["proyeksi"] - b)}'
    return ""


def kartu_prakiraan():
    p = prakiraan()
    with st.container(key="kartu_g_br_prakiraan"):
        st.markdown("**📈 Prakiraan akhir bulan**")
        if not p:
            st.caption("Muncul setelah ada pengeluaran bulan ini.")
            return
        st.markdown(f'<div class="ag"><b>Perkiraan total pengeluaran</b><span>{rp(p["proyeksi"])}</span></div>', unsafe_allow_html=True)
        b = total_batas()
        if b:
            st.markdown(batang(p["proyeksi"], b), unsafe_allow_html=True)
            sel = b - p["proyeksi"]
            st.caption(f"Total anggaran kategori {rp(b)}: " + (f"diperkirakan sisa {rp(sel)}." if sel >= 0 else f"diperkirakan lewat {rp(-sel)}."))
        st.caption(f'Sudah keluar {rp(p["terpakai"])} · laju {rp(p["laju"])}/hari (14 hari terakhir) × {p["sisa_hari"]} hari lagi'
                   + (f' · tagihan belum dicatat {rp(p["tagihan"])}' if p["tagihan"] else ""))
        if b and p["sisa_hari"] > 0:
            sisa_uang = b - p["terpakai"] - p["tagihan"]
            aman = max(0, sisa_uang) // p["sisa_hari"]
            st.caption(f"Agar tidak melewati total anggaran, batas harian yang aman: **{rp(aman)}** per hari." if sisa_uang > 0
                       else "Total anggaran sudah habis terpakai.")
        for ag, pakai, proy, lewat in prakiraan_anggaran():
            st.markdown(f'<div class="perhatian">🟠 <b>{e(label_ag(ag))}</b>: perkiraan {rp(proy)} dari batas {rp(ag["batas"])}'
                        + (f', batas tercapai sekitar tanggal {lewat.day}' if lewat else ', sudah terlewati') + '</div>', unsafe_allow_html=True)
