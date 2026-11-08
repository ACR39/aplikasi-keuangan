"""Penyimpanan data (GitHub atau file lokal), versi data untuk titik pulih, dan commit dari sesi."""
import base64
import json
import os
from datetime import datetime, timezone

import requests
import streamlit as st

from keuangan.inti import (
    FILE_LOKAL, WIB, cfg_github, data_kosong, hanya_lihat, lengkapi_kategori, pengguna_nama, sekarang,
)


class Bentrok(Exception):
    """Data di GitHub sudah berubah sejak terakhir dimuat."""


def _gh_url(c, path=None):
    return f"https://api.github.com/repos/{c['repo']}/contents/{path or c['path']}"


def _gh_headers(c):
    return {"Authorization": f"Bearer {c['token']}", "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28"}


def lengkapi(d: dict) -> dict:
    """Pastikan semua kunci data ada (data lama dari versi sebelumnya tetap bisa dibuka)."""
    for k, v in data_kosong().items():
        d.setdefault(k, v)
    lengkapi_kategori(d["kategori"])
    return d


def muat():
    """Kembalikan (data, sha). sha dipakai GitHub untuk mendeteksi bentrok."""
    c = cfg_github()
    if c:
        r = requests.get(_gh_url(c), headers=_gh_headers(c), params={"ref": c["branch"]}, timeout=20)
        if r.status_code == 404:
            return data_kosong(), None
        r.raise_for_status()
        j = r.json()
        return lengkapi(json.loads(base64.b64decode(j["content"]).decode("utf-8"))), j["sha"]
    if os.path.exists(FILE_LOKAL):
        with open(FILE_LOKAL, encoding="utf-8") as f:
            return lengkapi(json.load(f)), None
    return data_kosong(), None


def simpan(data: dict, pesan: str = "Perbarui data keuangan"):
    c = cfg_github()
    teks = json.dumps(data, ensure_ascii=False, indent=1, sort_keys=True)
    if c:
        body = {"message": pesan, "branch": c["branch"],
                "content": base64.b64encode(teks.encode("utf-8")).decode("ascii")}
        if st.session_state.get("sha"):
            body["sha"] = st.session_state.sha
        r = requests.put(_gh_url(c), headers=_gh_headers(c), json=body, timeout=30)
        if r.status_code in (409, 422):
            raise Bentrok()
        r.raise_for_status()
        st.session_state.sha = r.json()["content"]["sha"]
        return
    with open(FILE_LOKAL, "w", encoding="utf-8") as f:
        f.write(teks)
    try:                                   # salinan tiap versi, untuk Titik pulih
        dv = FILE_LOKAL + ".versi"
        os.makedirs(dv, exist_ok=True)
        nama_v = sekarang().strftime("%Y%m%d-%H%M%S-%f") + ".json"
        with open(os.path.join(dv, nama_v), "w", encoding="utf-8") as f:
            json.dump({"waktu": sekarang().strftime("%Y-%m-%d %H:%M"), "pesan": pesan, "data": data},
                      f, ensure_ascii=False)
        for lama_v in sorted(os.listdir(dv))[:-30]:
            os.remove(os.path.join(dv, lama_v))
    except Exception:
        pass


def daftar_versi(batas: int = 30) -> list:
    """Versi data sebelumnya, terbaru dulu: [{id, waktu 'YYYY-MM-DD HH:MM' (WIB), pesan}]."""
    c = cfg_github()
    if c:
        r = requests.get(f"https://api.github.com/repos/{c['repo']}/commits", headers=_gh_headers(c),
                         params={"path": c["path"], "sha": c["branch"], "per_page": batas}, timeout=30)
        r.raise_for_status()
        hasil = []
        for x in r.json():
            t = datetime.strptime(x["commit"]["committer"]["date"], "%Y-%m-%dT%H:%M:%SZ")
            wkt = t.replace(tzinfo=timezone.utc).astimezone(WIB).strftime("%Y-%m-%d %H:%M")
            hasil.append({"id": x["sha"], "waktu": wkt, "pesan": x["commit"]["message"].split("\n")[0]})
        return hasil
    dv = FILE_LOKAL + ".versi"
    if not os.path.isdir(dv):
        return []
    hasil = []
    for n in sorted(os.listdir(dv), reverse=True)[:batas]:
        try:
            with open(os.path.join(dv, n), encoding="utf-8") as f:
                j = json.load(f)
            hasil.append({"id": n, "waktu": j.get("waktu", ""), "pesan": j.get("pesan", "")})
        except Exception:
            continue
    return hasil


@st.cache_data(show_spinner=False, max_entries=20)
def _versi_gh(sha: str, repo: str, path: str, token: str):
    r = requests.get(f"https://api.github.com/repos/{repo}/contents/{path}", timeout=40,
                     headers={"Authorization": f"Bearer {token}", "Accept": "application/vnd.github.raw+json",
                              "X-GitHub-Api-Version": "2022-11-28"}, params={"ref": sha})
    r.raise_for_status()
    return json.loads(r.content.decode("utf-8"))


def ambil_versi(id_versi: str) -> dict:
    c = cfg_github()
    if c:
        return lengkapi(_versi_gh(id_versi, c["repo"], c["path"], c["token"]))
    with open(os.path.join(FILE_LOKAL + ".versi", os.path.basename(id_versi)), encoding="utf-8") as f:
        return lengkapi(json.load(f)["data"])


def muat_ke_sesi():
    st.session_state.data, st.session_state.sha = muat()


def commit(pesan_ok: str | None = None) -> bool:
    """Simpan st.session_state.data. Tampilkan hasilnya ke pengguna."""
    if hanya_lihat():
        muat_ke_sesi()
        st.error("Akun ini hanya bisa melihat, perubahan tidak disimpan.")
        return False
    pesan = f"{pesan_ok or 'Perbarui data keuangan'} (oleh {pengguna_nama()})"
    try:
        simpan(st.session_state.data, pesan)
    except Bentrok:
        muat_ke_sesi()
        st.error("Data sudah diubah dari tempat lain. Data terbaru sudah dimuat, silakan ulangi perubahan Anda.")
        return False
    except Exception as e:
        st.error(f"Gagal menyimpan: {e}")
        return False
    if pesan_ok:
        st.toast(pesan_ok, icon="✅")
    return True
