"""Utang dan piutang: pencatatan, cicilan, dan (opsional) ikut tercatat sebagai transaksi dompet."""
import streamlit as st

from keuangan.bantu import (
    f_dompet,
    atur, batang, catat, dompet_aktif, e, kat_pertama, nama_dompet, selesai_simpan, tambah_transaksi, versi,
)
from keuangan.inti import D, TGL_MAX, TGL_MIN, baru_id, fmt_iso, hanya_lihat, hari_ini, iso_ke_date, rp, sisa_hari

ARAH = {"utang": "Utang saya", "piutang": "Piutang (orang berutang ke saya)"}


def dibayar(u: dict) -> int:
    return sum(int(b["jumlah"]) for b in u.get("bayar", []))


def sisa(u: dict) -> int:
    return int(u["jumlah"]) - dibayar(u)


def jatuh_tempo_dekat(hari: int = 7) -> list:
    hasil = [u for u in D["utang"] if sisa(u) > 0 and u.get("tenggat") and (sisa_hari(u["tenggat"]) or 9999) <= hari]
    return sorted(hasil, key=lambda u: u["tenggat"])


def _kat_utang(arah: str, bayar: bool) -> str:
    """Utang: terima pinjaman = masuk, bayar = keluar. Piutang sebaliknya."""
    keluar = (arah == "piutang") if not bayar else (arah == "utang")
    return kat_pertama("keluar" if keluar else "masuk", "k_bayar_utang" if keluar else "k_terima_utang")


def _jenis_trx(arah: str, bayar: bool) -> str:
    return "keluar" if ((arah == "piutang") != bayar) else "masuk"


def _form_baru(arah: str):
    dompet = [d["id"] for d in dompet_aktif()]
    with st.form(f"f_ut_{arah}_{versi()}", clear_on_submit=True):
        c1, c2 = st.columns(2)
        orang = c1.text_input("Nama orang", placeholder="Contoh: Budi")
        jumlah = c2.number_input("Jumlah (Rp)", min_value=0, step=50000, value=0)
        c3, c4 = st.columns(2)
        tgl = c3.date_input("Tanggal", value=hari_ini(), min_value=TGL_MIN, max_value=TGL_MAX, format="DD/MM/YYYY")
        pakai_tenggat = c4.checkbox("Pakai tenggat")
        tenggat = c4.date_input("Tenggat", value=hari_ini(), min_value=TGL_MIN, max_value=TGL_MAX, format="DD/MM/YYYY")
        catatan = st.text_input("Catatan, opsional")
        ke_dompet = st.checkbox("Catat juga ke dompet " + ("(uang pinjaman masuk)" if arah == "utang" else "(uang keluar)"),
                                value=bool(dompet), disabled=not dompet)
        dom = st.selectbox("Dompet", dompet or [""], format_func=f_dompet({"": "-"}))
        if st.form_submit_button("Simpan", type="primary"):
            if not orang.strip() or jumlah <= 0:
                st.error("Isi nama dan jumlah.")
                return
            u = {"id": baru_id(), "arah": arah, "orang": orang.strip(), "jumlah": int(jumlah), "tgl": tgl.isoformat(),
                 "tenggat": tenggat.isoformat() if pakai_tenggat else "", "catatan": catatan.strip(), "bayar": []}
            D["utang"].append(u)
            if ke_dompet and dom:
                tambah_transaksi(_jenis_trx(arah, False), tgl, jumlah, dom, _kat_utang(arah, False),
                                 f"{'Pinjaman dari' if arah == 'utang' else 'Pinjamkan ke'} {u['orang']}", utang=u["id"])
            catat("utang", f"{ARAH[arah]}: {u['orang']} {rp(jumlah)}")
            selesai_simpan("Tersimpan.")


def _daftar(arah: str):
    daftar = [u for u in D["utang"] if u["arah"] == arah]
    aktif = sorted([u for u in daftar if sisa(u) > 0], key=lambda u: (u.get("tenggat") or "9999", u["orang"].lower()))
    lunas = [u for u in daftar if sisa(u) <= 0]
    total = sum(sisa(u) for u in aktif)
    st.caption(f"Belum lunas: **{len(aktif)}** · total sisa **{rp(total)}**")
    if not aktif:
        st.info("Tidak ada yang belum lunas.")
    for u in aktif:
        with st.container(key=f"kartu_g_ut_{u['id']}"):
            h = sisa_hari(u.get("tenggat"))
            ket = "" if h is None else (f" · <span class='st-bad'>terlambat {-h} hari</span>" if h < 0 else
                                        f" · tenggat {fmt_iso(u['tenggat'])} ({h} hari lagi)")
            st.markdown(f'<div class="ag"><b style="font-size:1.02rem">{e(u["orang"])}</b>'
                        f'<span>Sisa <b>{rp(sisa(u))}</b> dari {rp(u["jumlah"])}</span></div>{batang(dibayar(u), u["jumlah"], "bl")}'
                        f'<div class="sc-ket">Sejak {fmt_iso(u["tgl"])}{ket}{" · " + e(u["catatan"]) if u.get("catatan") else ""}</div>',
                        unsafe_allow_html=True)
            if hanya_lihat():
                continue
            with st.form(f"f_byr_{u['id']}_{versi()}", clear_on_submit=True):
                c1, c2, c3, c4 = st.columns([1.3, 1.3, 1.3, 1])
                jml = c1.number_input("Pembayaran (Rp)", min_value=0, step=50000, value=0, label_visibility="collapsed")
                dompet = [d["id"] for d in dompet_aktif()]
                dom = c2.selectbox("Dompet", ["" ] + dompet, format_func=f_dompet({"": "Tanpa dompet"}),
                                   label_visibility="collapsed")
                tgl = c3.date_input("Tanggal", value=hari_ini(), min_value=TGL_MIN, max_value=TGL_MAX, format="DD/MM/YYYY",
                                    label_visibility="collapsed")
                if c4.form_submit_button("Catat bayar", type="primary"):
                    if jml <= 0:
                        st.error("Jumlah harus lebih dari nol.")
                    elif jml > sisa(u):
                        st.error(f"Melebihi sisa ({rp(sisa(u))}).")
                    else:
                        u["bayar"].append({"id": baru_id(), "tgl": tgl.isoformat(), "jumlah": int(jml)})
                        if dom:
                            tambah_transaksi(_jenis_trx(arah, True), tgl, jml, dom, _kat_utang(arah, True),
                                             f"{'Bayar utang ke' if arah == 'utang' else 'Terima pembayaran dari'} {u['orang']}",
                                             utang=u["id"])
                        catat("utang", f"Pembayaran {rp(jml)} · {u['orang']}")
                        selesai_simpan("Pembayaran dicatat.")
            c = st.columns([1, 1, 5])
            c[0].button("Hapus", key=f"khapus_ut_{u['id']}", on_click=atur, args=("hapus_ut", u["id"]))
            if u["bayar"]:
                with st.expander(f"Riwayat pembayaran ({len(u['bayar'])})"):
                    for b in sorted(u["bayar"], key=lambda b: b["tgl"], reverse=True):
                        st.markdown(f'<div class="perhatian">{fmt_iso(b["tgl"])} · <b>{rp(b["jumlah"])}</b></div>', unsafe_allow_html=True)
            if st.session_state.get("hapus_ut") == u["id"]:
                st.warning("Hapus catatan ini? Transaksi di dompet yang sudah tercatat tidak ikut terhapus.")
                a, b, _ = st.columns([1, 1, 4])
                if a.button("Ya, hapus", key=f"ya_ut_{u['id']}", type="primary"):
                    D["utang"] = [x for x in D["utang"] if x["id"] != u["id"]]
                    catat("utang", f"Hapus catatan {u['orang']}")
                    selesai_simpan("Dihapus.", hapus_ut=None)
                b.button("Batal", key=f"batal_ut_{u['id']}", on_click=atur, args=("hapus_ut", None))
    if lunas:
        with st.expander(f"Sudah lunas ({len(lunas)})"):
            for u in lunas:
                st.markdown(f'<div class="perhatian"><b>{e(u["orang"])}</b> · {rp(u["jumlah"])} · sejak {fmt_iso(u["tgl"])}</div>',
                            unsafe_allow_html=True)
    if not hanya_lihat():
        with st.container(key=f"kartu_g_baru_{arah}"):
            st.markdown("**Tambah catatan baru**")
            _form_baru(arah)


def halaman_utang():
    t_u, t_p = st.tabs(list(ARAH.values()))
    with t_u:
        _daftar("utang")
    with t_p:
        _daftar("piutang")
