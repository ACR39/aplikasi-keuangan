"""Impor mutasi rekening (CSV/Excel dari bank atau e-wallet) dengan usulan kategori dari kebiasaan sebelumnya."""
import re
from collections import Counter

import pandas as pd
import streamlit as st

from keuangan.bantu import catat, dompet_aktif, f_dompet, kat_dari, kat_pertama, kategori_jenis, nama_kat, selesai_simpan, tambah_transaksi, versi
from keuangan.ekspor import _angka, _baca, _tanggal
from keuangan.inti import D, rp

KATA_TGL = ("tanggal", "tgl", "date", "waktu")
KATA_KET = ("keterangan", "deskripsi", "description", "uraian", "berita", "remark", "detail", "transaksi", "narasi")
KATA_DB = ("debit", "keluar", "db", "debet")
KATA_CR = ("kredit", "credit", "masuk", "cr")
KATA_JML = ("jumlah", "amount", "nominal", "mutasi")


def _tebak(kolom: list, kata: tuple, lewati: tuple = ()):
    for k in kolom:
        if any(w == str(k).strip().lower() for w in kata) and k not in lewati:
            return k
    for k in kolom:
        if any(w in str(k).strip().lower() for w in kata) and k not in lewati:
            return k
    return None


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[^a-z\s]", " ", str(s).lower())).strip()


def usulan_kategori(ket: str, jenis: str) -> str:
    """Kategori paling sering dipakai untuk keterangan serupa: catatan sama persis dulu, lalu kata yang sama; '' bila tidak ada."""
    n = _norm(ket)
    if not n:
        return ""
    ada = [t for t in D["transaksi"] if t["jenis"] == jenis and t.get("kategori") and kat_dari(t["kategori"])]
    persis = Counter(t["kategori"] for t in ada if _norm(t.get("catatan", "")) == n)
    if persis:
        return persis.most_common(1)[0][0]
    kata = {w for w in n.split() if len(w) >= 4}
    if not kata:
        return ""
    skor = Counter()
    for t in ada:
        sama = kata & {w for w in _norm(t.get("catatan", "")).split() if len(w) >= 4}
        if sama:
            skor[t["kategori"]] += len(sama)
    return skor.most_common(1)[0][0] if skor else ""


def baca_mutasi(df: pd.DataFrame, kol_tgl, kol_ket, kol_jml=None, kol_db=None, kol_cr=None) -> list:
    """Ubah tabel jadi daftar [{tgl, ket, jenis, jumlah}]. Pakai satu kolom bertanda (+/-) atau kolom debit dan kredit terpisah."""
    hasil = []
    for _, b in df.iterrows():
        try:
            tgl = _tanggal(b[kol_tgl])
        except ValueError:
            continue
        ket = str(b[kol_ket]).strip() if kol_ket else ""
        if kol_db or kol_cr:
            try:
                db = abs(_angka(b[kol_db])) if kol_db else 0
                cr = abs(_angka(b[kol_cr])) if kol_cr else 0
            except ValueError:
                continue
            if db:
                jenis, jml = "keluar", db
            elif cr:
                jenis, jml = "masuk", cr
            else:
                continue
        else:
            teks = str(b[kol_jml]).strip()
            try:
                v = _angka(re.sub(r"[a-zA-Z]", "", teks).replace("(", "-").replace(")", ""))
            except ValueError:
                continue
            if not v:
                continue
            ke_dr = bool(re.search(r"\b(db|dr|debit)\b", teks.lower())) or v < 0 or teks.startswith("-")
            jenis, jml = ("keluar", abs(v)) if ke_dr else ("masuk", abs(v))
        hasil.append({"tgl": tgl, "ket": ket, "jenis": jenis, "jumlah": jml})
    return hasil


def duplikat(dompet: str, r: dict) -> bool:
    return any(t["dompet"] == dompet and t["tgl"] == r["tgl"] and t["jenis"] == r["jenis"] and int(t["jumlah"]) == r["jumlah"] for t in D["transaksi"])


def halaman_mutasi():
    st.caption("Unggah mutasi rekening atau e-wallet (CSV atau Excel). Kolom dikenali otomatis, kategori diusulkan dari catatan yang pernah kamu pakai, "
               "dan transaksi yang tampaknya sudah ada ditandai sehingga tidak tercatat dua kali.")
    dompet = [d["id"] for d in dompet_aktif()]
    if not dompet:
        st.info("Tambahkan dompet dulu di Pengaturan > Dompet.")
        return
    berkas = st.file_uploader("File mutasi", type=["csv", "xlsx", "xlsm"], key=f"mt_berkas_{versi()}")
    if berkas is None:
        return
    try:
        df = _baca(berkas)
    except Exception as ex:
        st.error(f"File tidak bisa dibaca: {ex}")
        return
    kol = list(df.columns)
    if not kol:
        st.error("File kosong.")
        return
    t_tgl, t_ket = _tebak(kol, KATA_TGL), _tebak(kol, KATA_KET)
    t_db, t_cr = _tebak(kol, KATA_DB), _tebak(kol, KATA_CR)
    t_jml = _tebak(kol, KATA_JML, (t_db, t_cr))
    pisah_awal = bool(t_db and t_cr and t_db != t_cr)
    dom = st.selectbox("Masuk ke dompet", dompet, format_func=f_dompet(), key="mt_dom")
    c1, c2 = st.columns(2)
    k_tgl = c1.selectbox("Kolom tanggal", kol, index=kol.index(t_tgl) if t_tgl in kol else 0, key="mt_k_tgl")
    k_ket = c2.selectbox("Kolom keterangan", kol, index=kol.index(t_ket) if t_ket in kol else 0, key="mt_k_ket")
    pisah = st.radio("Format jumlah", ["Satu kolom (negatif = keluar)", "Kolom debit dan kredit terpisah"], index=1 if pisah_awal else 0,
                     horizontal=True, key="mt_pisah").startswith("Kolom")
    if pisah:
        c3, c4 = st.columns(2)
        k_db = c3.selectbox("Kolom debit (uang keluar)", kol, index=kol.index(t_db) if t_db in kol else 0, key="mt_k_db")
        k_cr = c4.selectbox("Kolom kredit (uang masuk)", kol, index=kol.index(t_cr) if t_cr in kol else 0, key="mt_k_cr")
        baris = baca_mutasi(df, k_tgl, k_ket, kol_db=k_db, kol_cr=k_cr)
    else:
        k_jml = st.selectbox("Kolom jumlah", kol, index=kol.index(t_jml) if t_jml in kol else 0, key="mt_k_jml")
        baris = baca_mutasi(df, k_tgl, k_ket, kol_jml=k_jml)
    if not baris:
        st.warning("Tidak ada baris yang terbaca. Periksa pilihan kolom.")
        return
    semua_kat = {}
    for j in ("keluar", "masuk"):
        for k in kategori_jenis(j):
            semua_kat[k["id"]] = f"{'↓' if j == 'masuk' else '↑'} {nama_kat(k['id'])}"
    nama_ke_id = {v: k for k, v in semua_kat.items()}
    tabel = pd.DataFrame([{"Impor": not duplikat(dom, r), "Tanggal": r["tgl"], "Keterangan": r["ket"], "Jenis": r["jenis"], "Jumlah": r["jumlah"],
                           "Kategori": semua_kat.get(usulan_kategori(r["ket"], r["jenis"]) or kat_pertama(r["jenis"], "k_lain") or "", ""),
                           "Catatan": "sudah ada" if duplikat(dom, r) else ""} for r in baris])
    st.caption(f"{len(baris)} baris terbaca, {int((tabel['Catatan'] == 'sudah ada').sum())} tampaknya sudah ada. Ubah kategori atau centang sebelum mengimpor.")
    edit = st.data_editor(tabel, key=f"mt_tabel_{versi()}_{berkas.name}_{dom}", hide_index=True, width="stretch", disabled=["Tanggal", "Keterangan", "Jenis", "Jumlah", "Catatan"],
                          column_config={"Impor": st.column_config.CheckboxColumn(), "Kategori": st.column_config.SelectboxColumn(options=list(nama_ke_id), required=False),
                                         "Jumlah": st.column_config.NumberColumn(format="%d")})
    pilih = edit[edit["Impor"]]
    if st.button(f"Impor {len(pilih)} transaksi", type="primary", key="mt_impor", disabled=pilih.empty):
        for _, b in pilih.iterrows():
            kat = nama_ke_id.get(b["Kategori"], "")
            if kat and (kat_dari(kat) or {}).get("jenis") != b["Jenis"]:
                kat = kat_pertama(b["Jenis"], "k_lain") or ""
            tambah_transaksi(b["Jenis"], b["Tanggal"], int(b["Jumlah"]), dom, kat, b["Keterangan"])
        catat("impor", f"Impor mutasi: {len(pilih)} transaksi dari {berkas.name}")
        selesai_simpan(f"{len(pilih)} transaksi diimpor (total {rp(int(pilih['Jumlah'].sum()))}).")
