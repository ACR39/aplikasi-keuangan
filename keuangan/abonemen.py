"""Catatan langganan (streaming, internet, aplikasi, keanggotaan): berapa totalnya, kapan habis atau diperpanjang."""
import streamlit as st

from keuangan.bantu import TIAP, atur, catat, deretan_stat, e, kartu_stat, maju_tgl, selesai_simpan, versi
from keuangan.inti import D, TGL_MAX, TGL_MIN, baru_id, fmt_iso, hanya_lihat, hari_ini, iso_ke_date, rp, sisa_hari

PERIODE = {"mingguan": "Tiap minggu", "bulanan": "Tiap bulan", "tiga_bulan": "Tiap 3 bulan", "tahunan": "Tiap tahun"}
KALI_PER_TAHUN = {"mingguan": 52, "bulanan": 12, "tiga_bulan": 4, "tahunan": 1}


def per_tahun(a: dict) -> int:
    return round(int(a["jumlah"]) * KALI_PER_TAHUN.get(a.get("tiap", "bulanan"), 12))


def per_bulan(a: dict) -> int:
    return round(per_tahun(a) / 12)


def aktif() -> list:
    return [a for a in D["abonemen"] if a.get("aktif", True)]


def status(a: dict) -> tuple:
    """(teks, kelas) berdasarkan sisa hari sampai tanggal habis atau perpanjangan."""
    s = sisa_hari(a.get("berikut"))
    kata = "diperpanjang" if a.get("otomatis") else "habis"
    if s is None:
        return "", ""
    if s < 0:
        return f"Sudah lewat {-s} hari", "st-bad"
    if s == 0:
        return f"{kata.capitalize()} hari ini", "st-bad"
    if s <= 7:
        return f"{kata.capitalize()} {s} hari lagi", "st-warn"
    return f"{kata.capitalize()} {s} hari lagi", "st-ok"


def baris_perhatian() -> list:
    hasil = []
    for a in sorted(aktif(), key=lambda a: a.get("berikut") or "9999"):
        s = sisa_hari(a.get("berikut"))
        if s is None or s > 7:
            continue
        teks = status(a)[0].lower()
        hasil.append(f'Langganan <b>{e(a["nama"])}</b> {rp(a["jumlah"])}: {teks} ({fmt_iso(a["berikut"])})'
                     + ("" if a.get("otomatis") else ". Perpanjang atau hentikan."))
    return hasil


def _perpanjang(a: dict):
    tgl = iso_ke_date(a.get("berikut")) or hari_ini()
    while tgl <= hari_ini() or tgl == iso_ke_date(a.get("berikut")):
        tgl = maju_tgl(tgl, a["tiap"])
    a["berikut"] = tgl.isoformat()
    catat("langganan", f"Perpanjang langganan {a['nama']} sampai {fmt_iso(a['berikut'])}")
    selesai_simpan(f"{a['nama']} diperpanjang sampai {fmt_iso(a['berikut'])}.")


def _form(edit: dict | None):
    with st.form(f"f_abo_{(edit or {}).get('id', 'baru')}_{versi()}"):
        nama = st.text_input("Nama langganan", value=(edit or {}).get("nama", ""), placeholder="Netflix, internet rumah, Spotify")
        c1, c2 = st.columns(2)
        jumlah = c1.number_input("Biaya sekali bayar (Rp)", min_value=0, step=1000, value=int((edit or {}).get("jumlah", 0)))
        kunci = list(PERIODE)
        tiap = c2.selectbox("Ditagih", kunci, index=kunci.index((edit or {}).get("tiap", "bulanan")), format_func=PERIODE.get)
        awal = iso_ke_date((edit or {}).get("berikut")) or hari_ini()
        berikut = st.date_input("Habis atau diperpanjang pada", value=awal, min_value=TGL_MIN, max_value=TGL_MAX)
        otomatis = st.checkbox("Diperpanjang otomatis (kartu atau dompet dipotong sendiri)", value=bool((edit or {}).get("otomatis", False)))
        catatan = st.text_input("Catatan, opsional", value=(edit or {}).get("catatan", ""), placeholder="Paket keluarga, akun bersama, nomor pelanggan")
        if not st.form_submit_button("Simpan perubahan" if edit else "Tambah langganan", type="primary"):
            return
    if not nama.strip():
        st.error("Isi nama langganan.")
        return
    isi = {"nama": nama.strip(), "jumlah": int(jumlah), "tiap": tiap, "berikut": berikut.isoformat(), "otomatis": bool(otomatis), "catatan": catatan.strip()}
    if edit:
        edit.update(isi)
        catat("langganan", f"Ubah langganan {isi['nama']}")
        selesai_simpan("Langganan diubah.", edit_abo=None)
    else:
        D["abonemen"].append({"id": baru_id(), "aktif": True, **isi})
        catat("langganan", f"Tambah langganan {isi['nama']} {rp(isi['jumlah'])}")
        selesai_simpan("Langganan ditambahkan.")


def halaman_langganan():
    ro = hanya_lihat()
    edit = next((a for a in D["abonemen"] if a["id"] == st.session_state.get("edit_abo")), None)
    if not ro:
        with st.expander("Ubah langganan" if edit else "Tambah langganan", expanded=bool(edit) or not D["abonemen"]):
            _form(edit)
            if edit:
                st.button("Batal", key="batal_abo", on_click=atur, args=("edit_abo", None))
    if not D["abonemen"]:
        st.info("Belum ada langganan. Catat Netflix, internet, atau aplikasi berbayar lain supaya totalnya terlihat dan tidak terlewat saat habis.")
        return
    a_aktif = aktif()
    deretan_stat(kartu_stat("Aktif", str(len(a_aktif))),
                 kartu_stat("Per bulan", rp(sum(per_bulan(a) for a in a_aktif)), kelas="m"),
                 kartu_stat("Per tahun", rp(sum(per_tahun(a) for a in a_aktif)), kelas="m"))
    for a in sorted(D["abonemen"], key=lambda a: (not a.get("aktif", True), a.get("berikut") or "9999")):
        teks, kelas = status(a) if a.get("aktif", True) else ("Dihentikan", "")
        with st.container(key=f"abo_{a['id']}", border=True):
            st.markdown(f'<div class="ag"><b>{e(a["nama"])}</b><span>{rp(a["jumlah"])} · {e(PERIODE.get(a["tiap"], "").lower())}</span></div>', unsafe_allow_html=True)
            st.markdown(f'<div class="sc-ket"><span class="{kelas}">{e(teks)}</span>'
                        + (f' · {"perpanjang" if a.get("otomatis") else "habis"} {fmt_iso(a["berikut"])}' if a.get("berikut") and a.get("aktif", True) else "")
                        + f' · setara {rp(per_bulan(a))} per bulan</div>', unsafe_allow_html=True)
            if a.get("catatan"):
                st.caption(a["catatan"])
            if ro:
                continue
            c = st.columns(3)
            if a.get("aktif", True):
                c[0].button("Perpanjang", key=f"abo_p_{a['id']}", on_click=_perpanjang, args=(a,))
            else:
                c[0].button("Aktifkan", key=f"abo_a_{a['id']}", on_click=_ubah_aktif, args=(a, True))
            c[1].button("Ubah", key=f"abo_u_{a['id']}", on_click=atur, args=("edit_abo", a["id"]))
            if st.session_state.get("hapus_abo") == a["id"]:
                st.warning(f"Hapus catatan langganan {a['nama']}?")
                ya, tdk = st.columns(2)
                if ya.button("Ya, hapus", key=f"abo_ya_{a['id']}", type="primary"):
                    D["abonemen"] = [x for x in D["abonemen"] if x["id"] != a["id"]]
                    catat("langganan", f"Hapus langganan {a['nama']}")
                    selesai_simpan("Langganan dihapus.", hapus_abo=None)
                tdk.button("Batal", key=f"abo_tdk_{a['id']}", on_click=atur, args=("hapus_abo", None))
            else:
                c[2].button("Hapus", key=f"abo_h_{a['id']}", on_click=atur, args=("hapus_abo", a["id"]))
            if a.get("aktif", True):
                st.button("Hentikan langganan", key=f"abo_s_{a['id']}", on_click=_ubah_aktif, args=(a, False))


def _ubah_aktif(a: dict, nilai: bool):
    a["aktif"] = nilai
    catat("langganan", f"{'Aktifkan' if nilai else 'Hentikan'} langganan {a['nama']}")
    selesai_simpan("Langganan " + ("diaktifkan." if nilai else "dihentikan."))
