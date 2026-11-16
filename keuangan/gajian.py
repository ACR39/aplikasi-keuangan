"""Sisa uang sampai gajian: berapa yang masih boleh dipakai per hari sampai tanggal gajian berikutnya."""
import calendar
from datetime import date, timedelta

import streamlit as st

from keuangan.bantu import atur, catat, dompet_aktif, e, saldo_dompet, selesai_simpan, versi
from keuangan.inti import D, hanya_lihat, hari_ini, iso_ke_date, rp


def hari_gajian() -> int:
    try:
        return max(0, min(31, int(D.get("pengaturan", {}).get("gajian", 0) or 0)))
    except (TypeError, ValueError):
        return 0


def gajian_berikut(h: date, hari: int) -> date:
    """Tanggal gajian berikutnya setelah hari ini. Tanggal 31 di bulan pendek jatuh di hari terakhir bulan itu."""
    def di(y, m):
        return date(y, m, min(hari, calendar.monthrange(y, m)[1]))
    kini = di(h.year, h.month)
    if kini > h:
        return kini
    return di(h.year + (h.month == 12), h.month % 12 + 1)


def hitung(h: date | None = None) -> dict | None:
    h = h or hari_ini()
    hari = hari_gajian()
    if not hari:
        return None
    tujuan = gajian_berikut(h, hari)
    sisa_hari = (tujuan - h).days
    saldo = sum(saldo_dompet(d["id"]) for d in dompet_aktif() if d.get("jenis") != "Kartu kredit")
    tagihan = sum(int(t["jumlah"]) for t in D["tagihan"]
                  if t.get("aktif", True) and t.get("jenis", "keluar") == "keluar" and t.get("berikut")
                  and iso_ke_date(t["berikut"]) and iso_ke_date(t["berikut"]) <= tujuan)
    bebas = saldo - tagihan
    a = (h - timedelta(days=13)).isoformat()
    laju = sum(int(t["jumlah"]) for t in D["transaksi"]
               if t["jenis"] == "keluar" and a <= t["tgl"] <= h.isoformat() and not t.get("tagihan")) / 14
    per_hari = max(0, bebas) // max(1, sisa_hari)
    habis = None
    if laju > 0 and bebas > 0 and laju * sisa_hari > bebas:
        habis = h + timedelta(days=int(bebas / laju))
    return {"tujuan": tujuan, "sisa_hari": sisa_hari, "saldo": saldo, "tagihan": tagihan, "bebas": bebas,
            "per_hari": per_hari, "laju": round(laju), "habis": habis}


def kartu_gajian():
    ro = hanya_lihat()
    r = hitung()
    with st.container(key="kartu_g_br_gajian"):
        st.markdown("**Sisa uang sampai gajian**")
        if r:
            st.markdown(f'<div class="sc-lab">Boleh dipakai per hari</div><div class="mg-val">{e(rp(r["per_hari"]))}</div>'
                        f'<div class="sc-ket">{r["sisa_hari"]} hari lagi sampai gajian, {r["tujuan"].strftime("%d/%m/%Y")}</div>'
                        f'<div class="lg" style="margin-top:.7rem"><div><span class="lab">Saldo dompet</span><b>{e(rp(r["saldo"]))}</b>'
                        f'<small>tanpa kartu kredit</small></div>'
                        f'<div><span class="lab">Tagihan menunggu</span><b>{e(rp(r["tagihan"]))}</b><small>jatuh tempo sebelum gajian</small></div></div>',
                        unsafe_allow_html=True)
            if r["bebas"] <= 0:
                st.markdown(f'<div class="perhatian">Saldo tidak cukup untuk tagihan yang menunggu: kurang {e(rp(-r["bebas"]))}.</div>', unsafe_allow_html=True)
            elif r["habis"]:
                st.markdown(f'<div class="perhatian">Laju {e(rp(r["laju"]))} per hari (14 hari terakhir) lebih besar dari {e(rp(r["per_hari"]))}. '
                            f'Uang diperkirakan habis sekitar {r["habis"].strftime("%d/%m/%Y")}.</div>', unsafe_allow_html=True)
            else:
                st.caption(f'Laju {rp(r["laju"])} per hari (14 hari terakhir), masih di bawah batas ini.')
        else:
            st.caption("Isi tanggal gajian untuk melihat berapa uang yang boleh dipakai per hari sampai gajian berikutnya.")
        if ro:
            return
        with st.expander("Atur tanggal gajian" if not r else "Ubah tanggal gajian"):
            with st.form(f"f_gajian_{versi()}"):
                nilai = st.number_input("Tanggal gajian tiap bulan (0 = tidak dipakai)", min_value=0, max_value=31, step=1, value=hari_gajian())
                if st.form_submit_button("Simpan", type="primary"):
                    D["pengaturan"]["gajian"] = int(nilai)
                    catat("pengaturan", f"Tanggal gajian {int(nilai)}" if nilai else "Matikan tanggal gajian")
                    selesai_simpan("Tanggal gajian disimpan.")
