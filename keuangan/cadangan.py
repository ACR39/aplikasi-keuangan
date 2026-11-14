"""Cadangan (unduh/muat JSON) dan titik pulih ke versi sebelumnya."""
import base64
import json
import os
import posixpath
from datetime import date

import requests
import streamlit as st

from keuangan.bantu import catat, selesai_simpan, versi
from keuangan.inti import D, FILE_LOKAL, adalah_admin, cfg_github, data_kosong, fmt_waktu, hari_ini, sekarang
from keuangan.penyimpanan import _gh_headers, _gh_url, ambil_versi, commit, daftar_versi, lengkapi


# ---------------------------------------------------------------- cadangan otomatis (berkas Excel + JSON di folder cadangan/)
SIMPAN_CADANGAN = 10  # jumlah cadangan terakhir yang disimpan


def _dir() -> str:
    c = cfg_github()
    return posixpath.join(posixpath.dirname(c["path"]), "cadangan") if c else FILE_LOKAL + ".cadangan"


def _tulis(nama: str, isi: bytes):
    c = cfg_github()
    if c:
        r = requests.put(_gh_url(c, posixpath.join(_dir(), nama)), headers=_gh_headers(c), timeout=60,
                         json={"message": f"Cadangan {nama}", "branch": c["branch"], "content": base64.b64encode(isi).decode("ascii")})
        r.raise_for_status()
    else:
        os.makedirs(_dir(), exist_ok=True)
        with open(os.path.join(_dir(), nama), "wb") as f:
            f.write(isi)


def daftar_cadangan() -> list:
    """Nama berkas cadangan (terbaru dulu) beserta sha bila di GitHub: [(nama, sha)]."""
    c = cfg_github()
    try:
        if c:
            r = requests.get(_gh_url(c, _dir()), headers=_gh_headers(c), params={"ref": c["branch"]}, timeout=30)
            if r.status_code != 200:
                return []
            baris = [(x["name"], x["sha"]) for x in r.json() if x["type"] == "file"]
        else:
            baris = [(n, "") for n in os.listdir(_dir())] if os.path.isdir(_dir()) else []
    except Exception:
        return []
    return sorted(baris, reverse=True)


def _baca(nama: str):
    c = cfg_github()
    try:
        if c:
            r = requests.get(_gh_url(c, posixpath.join(_dir(), nama)), timeout=40, params={"ref": c["branch"]},
                             headers={**_gh_headers(c), "Accept": "application/vnd.github.raw+json"})
            return r.content if r.status_code == 200 else None
        with open(os.path.join(_dir(), nama), "rb") as f:
            return f.read()
    except Exception:
        return None


def _hapus_cadangan(nama: str, sha: str):
    c = cfg_github()
    try:
        if c:
            requests.delete(_gh_url(c, posixpath.join(_dir(), nama)), headers=_gh_headers(c), timeout=30,
                            json={"message": f"Hapus cadangan {nama}", "branch": c["branch"], "sha": sha})
        else:
            os.remove(os.path.join(_dir(), nama))
    except Exception:
        pass


def buat_cadangan() -> str:
    """Tulis cadangan Excel dan JSON, buang yang lama. Mengembalikan stempel waktunya. Melempar error bila gagal."""
    from keuangan.ekspor import excel_lengkap
    st_ = sekarang().strftime("%Y%m%d-%H%M")
    _tulis(f"keuangan-{st_}.xlsx", excel_lengkap())
    _tulis(f"keuangan-{st_}.json", json.dumps(D.data, ensure_ascii=False, indent=1, sort_keys=True).encode("utf-8"))
    for jenis in (".xlsx", ".json"):
        for nama, sha in [x for x in daftar_cadangan() if x[0].endswith(jenis)][SIMPAN_CADANGAN:]:
            _hapus_cadangan(nama, sha)
    return st_


def interval_hari() -> int:
    try:
        return max(0, int(D.get("pengaturan", {}).get("cadangan_hari", 0) or 0))
    except (TypeError, ValueError):
        return 0


def perlu_cadangan() -> bool:
    n = interval_hari()
    if not n:
        return False
    terakhir = D.get("pengaturan", {}).get("cadangan_terakhir", "")
    try:
        return (hari_ini() - date.fromisoformat(terakhir)).days >= n
    except ValueError:
        return True


def cadangan_otomatis():
    """Dipanggil tiap sesi oleh admin: bila sudah waktunya, buat cadangan diam-diam (sekali per sesi)."""
    if st.session_state.get("cadangan_dicek") or not adalah_admin() or not perlu_cadangan():
        return
    st.session_state.cadangan_dicek = True
    try:
        buat_cadangan()
    except Exception as ex:
        st.warning(f"Cadangan otomatis gagal: {ex}")
        return
    D["pengaturan"]["cadangan_terakhir"] = hari_ini().isoformat()
    catat("data", "Cadangan otomatis dibuat")
    commit("Cadangan otomatis")


def _panel_otomatis():
    with st.expander("Cadangan otomatis ke Excel" + (f" · tiap {interval_hari()} hari" if interval_hari() else " · mati"), expanded=False):
        st.caption(f"Saat admin membuka aplikasi dan sudah waktunya, cadangan Excel dan JSON disimpan di folder cadangan penyimpanan data "
                   f"(maks {SIMPAN_CADANGAN} terakhir). Untuk memulihkan, muat berkas JSA-nya di bawah.".replace("JSA", "JSON"))
        pil = {0: "Mati", 1: "Tiap hari", 7: "Tiap minggu", 14: "Tiap 2 minggu", 30: "Tiap bulan"}
        n = st.selectbox("Jadwal", list(pil), index=list(pil).index(interval_hari()) if interval_hari() in pil else 0,
                         format_func=lambda x: pil[x], key=f"cd_jadwal_{versi()}")
        c1, c2 = st.columns(2)
        if c1.button("Simpan jadwal", key="cd_simpan"):
            D["pengaturan"]["cadangan_hari"] = n
            catat("data", f"Jadwal cadangan: {pil[n]}")
            selesai_simpan("Jadwal cadangan disimpan.")
        if c2.button("Cadangkan sekarang", key="cd_sekarang"):
            try:
                buat_cadangan()
            except Exception as ex:
                st.error(f"Gagal: {ex}")
            else:
                D["pengaturan"]["cadangan_terakhir"] = hari_ini().isoformat()
                catat("data", "Cadangan dibuat manual")
                selesai_simpan("Cadangan dibuat.")
        if D.get("pengaturan", {}).get("cadangan_terakhir"):
            st.caption(f"Terakhir: {D['pengaturan']['cadangan_terakhir']}")
        for nama, _ in daftar_cadangan()[:8]:
            isi = _baca(nama)
            if isi:
                st.download_button(f"⬇ {nama}", isi, file_name=nama, key=f"cd_dl_{nama}")


def halaman_cadangan():
    _panel_otomatis()
    with st.container(key="kartu_g_cadangan"):
        st.caption("Unduh seluruh data sebagai file, atau muat file data dari tempat lain. "
                   "Memuat file akan **mengganti semua data** yang ada sekarang.")
        st.download_button("Unduh data.json", json.dumps(D.data, ensure_ascii=False, indent=1, sort_keys=True),
                           file_name=f"keuangan-{sekarang().strftime('%Y%m%d')}.json", mime="application/json")
        with st.form("impor_json"):
            berkas = st.file_uploader("File data.json", type=["json"])
            yakin = st.checkbox("Ya, ganti semua data dengan isi file ini")
            if st.form_submit_button("Muat file"):
                if berkas is None:
                    st.error("Pilih filenya dulu.")
                elif not yakin:
                    st.error('Centang dulu "Ya, ganti semua data".')
                else:
                    try:
                        baru = json.load(berkas)
                        assert isinstance(baru, dict) and isinstance(baru.get("transaksi"), list) and isinstance(baru.get("dompet"), list)
                    except Exception:
                        st.error("File tidak dikenali sebagai data keuangan.")
                    else:
                        st.session_state.data = lengkapi(baru)
                        catat("data", "Data dimuat dari file")
                        selesai_simpan("Data dimuat.")


def halaman_pulih():
    with st.container(key="kartu_g_pulih"):
        st.caption("Setiap perubahan tersimpan sebagai satu versi. Pilih versi lama untuk melihat perbedaannya, "
                   "lalu pulihkan seluruh data ke versi itu.")
        try:
            daftar = daftar_versi()
        except Exception as ex:
            st.error(f"Riwayat versi tidak bisa dibaca: {ex}")
            return
        if not daftar:
            st.info("Belum ada versi tersimpan. Versi pertama tercatat saat ada perubahan data berikutnya.")
            return
        peta = {v["id"]: v for v in daftar}
        pilih = st.selectbox("Versi", list(peta), key="pl_versi",
                             format_func=lambda i: f"{fmt_waktu(peta[i]['waktu'])} · {peta[i]['pesan'][:55]}")
        try:
            lama = ambil_versi(pilih)
        except Exception as ex:
            st.error(f"Versi ini tidak bisa dibuka: {ex}")
            return
        st.markdown("**Perbandingan** (sekarang → versi ini)")
        for lab, kunci in (("Transaksi", "transaksi"), ("Barang", "barang"), ("Toko", "toko"), ("Platform", "platform"), ("Daftar belanja", "belanja"), ("Dompet", "dompet"), ("Kategori", "kategori"), ("Anggaran", "anggaran"),
                           ("Tagihan", "tagihan"), ("Target tabungan", "tabungan"), ("Utang-piutang", "utang"), ("Tempat sampah", "sampah")):
            st.markdown(f'<div class="perhatian"><b>{lab}</b>: {len(D.get(kunci, []))} → {len(lama.get(kunci, []))}</div>', unsafe_allow_html=True)
        if json.dumps(lama, sort_keys=True) == json.dumps(D.data, sort_keys=True):
            st.info("Versi ini sama persis dengan data sekarang, tidak ada yang perlu dipulihkan.")
            return
        yakin = st.checkbox("Ya, ganti seluruh data sekarang dengan versi ini", key=f"pl_yakin_{pilih}")
        if st.button("Pulihkan ke versi ini", type="primary", disabled=not yakin, key="pl_go"):
            st.session_state.data = lama
            catat("data", f"Dipulihkan ke versi {fmt_waktu(peta[pilih]['waktu'])}: {peta[pilih]['pesan'][:80]}")
            selesai_simpan("Data dipulihkan.")
