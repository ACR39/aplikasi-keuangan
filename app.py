"""Pencatat Keuangan Pribadi (Streamlit).

Mencatat pemasukan, pengeluaran, transfer antar dompet, anggaran bulanan,
serta utang-piutang. Data disimpan sebagai satu file JSON di repositori GitHub
(disarankan repositori privat terpisah), foto struk disimpan di folder foto/.
Kalau pengaturan GitHub tidak ada, aplikasi memakai file lokal untuk uji coba.
"""
import base64
import hashlib
import hmac
import html
import io
import json
import os
import time
import uuid
from datetime import date, datetime, timedelta, timezone

import pandas as pd
import requests
import streamlit as st

try:
    from PIL import Image, ImageOps
except Exception:
    Image = ImageOps = None

st.set_page_config(page_title="Pencatat Keuangan", page_icon="💰", layout="wide")

# ========================================================================= CSS
st.markdown("""
<style>
.block-container{padding:1rem 2rem 4rem;max-width:1600px}
[data-testid="stToolbarActions"],[data-testid="stMainMenu"],[data-testid="stAppDeployButton"],[data-testid="stDecoration"],[data-testid="stStatusWidget"]{display:none !important}
[data-testid="stHeader"]{background:transparent}
.eyebrow{font-size:.72rem;font-weight:700;letter-spacing:.09em;color:#2b7a57}
.judul-hal{font-size:1.6rem;font-weight:700;color:#111827;margin:.1rem 0 .15rem;letter-spacing:-.01em}
.kepala{display:flex;align-items:center;justify-content:space-between;gap:1rem;flex-wrap:wrap;
  background:#fff;border:1px solid #e5e7eb;border-left:4px solid #2b7a57;border-radius:12px;
  padding:1rem 1.3rem;margin:0 0 1.4rem;box-shadow:0 1px 3px rgba(15,23,42,.05)}
.kepala .desk{font-size:.86rem;color:#64748b;max-width:62ch}
.pengguna{display:flex;align-items:center;gap:.6rem;background:#f1f5f9;border-radius:999px;padding:.35rem .9rem .35rem .4rem}
.pengguna .av{width:30px;height:30px;border-radius:50%;background:linear-gradient(135deg,#34a874,#1f6b49);
  color:#fff;font-weight:700;font-size:.85rem;display:flex;align-items:center;justify-content:center}
.pengguna .nm{font-size:.84rem;font-weight:600;color:#0f172a;line-height:1.15}
.pengguna .pr{font-size:.7rem;color:#64748b;text-transform:capitalize}
.pengguna.sb{background:transparent;margin:.9rem 0 .5rem;border-radius:0;border-top:1px solid rgba(255,255,255,.08);padding:.9rem .2rem 0}
[data-testid="stSidebar"] .pengguna.sb .nm{color:#fff;font-size:.88rem}
[data-testid="stSidebar"] .pengguna.sb .pr{color:#94a3b8}
[data-testid="stSidebar"]{background:#0b1220}
[data-testid="stSidebarHeader"]{position:absolute;top:.5rem;right:.5rem;width:auto;height:auto;padding:0;margin:0;z-index:5}
[data-testid="stSidebarUserContent"]{padding-top:1.1rem}
[data-testid="stSidebar"] *{color:#e5e7eb}
[data-testid="stSidebar"] [data-testid="stCaptionContainer"] *{color:#94a3b8}
.brand{display:flex;align-items:center;gap:.7rem;padding:.3rem .2rem 1.1rem;border-bottom:1px solid rgba(255,255,255,.08);margin-bottom:.4rem}
.brand .b1{font-weight:700;font-size:1.05rem;color:#fff;line-height:1.2}
.brand .b2{font-size:.76rem;color:#94a3b8;margin-top:.1rem}
.sp{height:1.2rem}
.grup{font-size:.66rem;font-weight:700;letter-spacing:.12em;color:#64748b;margin:1rem 0 .35rem .3rem}
[data-testid="stSidebar"] [data-testid="stExpander"]{background:transparent;border:0;box-shadow:none;margin-bottom:.2rem}
[data-testid="stSidebar"] [data-testid="stExpander"] details{border:0}
[data-testid="stSidebar"] [data-testid="stExpander"] summary{font-weight:600;font-size:.92rem;padding:.55rem .5rem;border-radius:8px;background:transparent !important;color:#e5e7eb !important}
[data-testid="stSidebar"] [data-testid="stExpander"] summary:hover{background:rgba(255,255,255,.06) !important}
[data-testid="stSidebar"] [data-testid="stExpanderDetails"]{padding:.1rem 0 .3rem .5rem;border-left:1px solid rgba(255,255,255,.1);margin-left:1rem}
[class*="st-key-nav_"] button{justify-content:flex-start !important;text-align:left !important;border:0 !important;
  border-radius:8px;min-height:2.4rem;background:transparent !important;color:#cbd5e1 !important;
  font-weight:500;font-size:.9rem;box-shadow:inset 3px 0 0 transparent}
[class*="st-key-nav_"] button:hover{background:rgba(255,255,255,.06) !important;color:#fff !important}
[class*="st-key-nav_"] button[kind="primary"]{background:rgba(52,168,116,.18) !important;color:#fff !important;
  font-weight:600;box-shadow:inset 3px 0 0 #34d399}
[class*="st-key-nav_"] button > div,[class*="st-key-nav_"] button [data-testid="stMarkdownContainer"],
[class*="st-key-nav_"] button p{text-align:left !important;justify-content:flex-start !important}
[class*="st-key-nav_muat"] button{border:1px solid rgba(255,255,255,.12) !important;justify-content:center !important}
.st-key-kartu_filter,.st-key-kartu_tabel,.st-key-kartu_utama,.st-key-kartu_perhatian,[class*="st-key-kartu_g"]{background:#fff;border:1px solid #e3e7ee;border-radius:16px;
  padding:1.1rem 1.2rem;box-shadow:0 1px 3px rgba(16,24,40,.06);margin-bottom:.9rem}
[data-testid="stExpander"]{background:#fff;border-radius:14px !important;box-shadow:0 1px 3px rgba(16,24,40,.06)}
.statcard{display:flex;flex-wrap:wrap;background:#fff;border:1px solid #e3e7ee;border-radius:16px;
  box-shadow:0 1px 3px rgba(16,24,40,.06);margin:.2rem 0 .6rem;overflow:hidden}
.sc-kiri{flex:2 1 260px;padding:1rem 1.2rem}
.sc-judul{font-size:1.45rem;font-weight:800;color:#111827;margin-top:.4rem}
.sc-ket{font-size:.85rem;color:#6b7280;margin-top:.15rem}
.tag{display:inline-block;background:#e8f3ec;color:#1f6b49;font-size:.72rem;font-weight:700;border-radius:999px;
  padding:.15rem .65rem;margin-right:.4rem}
.sc-stat{flex:1 1 130px;border-left:1px solid #eef0f4;text-align:center;padding:1rem .5rem}
.sc-lab{font-size:.7rem;font-weight:700;letter-spacing:.07em;text-transform:uppercase;color:#6b7280}
.sc-val{font-size:1.35rem;font-weight:800;color:#111827;margin-top:.25rem}
.sc-val.g{color:#166534}.sc-val.m{color:#b42318}.sc-val.b{color:#2f5d9e}
.thead-s{background:#256b4a;color:#fff;font-weight:650;font-size:.7rem;letter-spacing:.03em;text-transform:uppercase;text-align:center;padding:.3rem .25rem;border-radius:4px;height:2.6rem;display:flex;align-items:center;justify-content:center}
.garis{border-top:1px solid #e3e7ee;margin:.3rem 0}
.brg{font-weight:650}
.sub{font-size:.85rem;color:#5b6573}
.bidang{font-weight:700;font-size:.78rem;text-transform:uppercase;letter-spacing:.07em;color:#256b4a;background:#e8f3ec;border-left:3px solid #256b4a;padding:.35rem .7rem;border-radius:4px;margin:.6rem 0 .2rem}
.st-ok{color:#166534;font-weight:600}.st-warn{color:#8a5a00;font-weight:600}.st-bad{color:#b42318;font-weight:600}
.lencana{display:inline-block;font-size:.66rem;font-weight:700;border-radius:999px;padding:.05rem .5rem;margin-left:.4rem;vertical-align:middle;white-space:nowrap}
.lc-m{background:#fff4d6;color:#8a5a00}.lc-r{background:#fde8e6;color:#b42318}.lc-b{background:#e6eefb;color:#2f5d9e}.lc-h{background:#e3f3ea;color:#166534}
.perhatian{padding:.45rem 0;border-bottom:1px solid #eef0f4;font-size:.92rem;color:#1f2937}
.perhatian:last-child{border-bottom:0}
[class*="st-key-item_"]{background:#fff;border:1px solid #e3e7ee;border-radius:14px;padding:.8rem 1rem;
  box-shadow:0 1px 3px rgba(16,24,40,.06);margin-bottom:.4rem;color:#111827 !important}
.itm{display:flex;align-items:center;gap:.85rem}
.itm .ic{flex:0 0 46px;width:46px;height:46px;border-radius:50%;background:#e8f3ec;color:#256b4a;font-weight:800;
  font-size:1.15rem;display:flex;align-items:center;justify-content:center;overflow:hidden}
.itm .ic.out{background:#fde8e6;color:#b42318}
.itm .ic.trf{background:#e6eefb;color:#2f5d9e}
.itm .isi{flex:1 1 auto;min-width:0}
.itm .jd{font-weight:700;font-size:1rem;color:#111827;word-break:break-word}
.itm .mt{font-size:.82rem;color:#5b6573;margin-top:.1rem}
.itm .cat{font-size:.82rem;color:#374151;margin-top:.15rem}
.itm .qt{flex:0 0 auto;text-align:right;min-width:90px}
.itm .qt b{display:block;font-size:1.15rem;font-weight:800;line-height:1.2;color:#166534}
.itm .qt b.merah{color:#b42318}
.itm .qt b.biru{color:#2f5d9e}
.itm .qt span{display:block;font-size:.72rem;color:#6b7280}
.akt{border:1px solid #e3e7ee;border-radius:10px;padding:.55rem .8rem;margin:.45rem 0;background:#fff}
.akt .ah{font-weight:650}.akt .ar{font-size:.86rem;color:#3d4655;margin-top:.15rem}.akt .am{font-size:.76rem;color:#6b7280;margin-top:.25rem}
</style>
""", unsafe_allow_html=True)

CSS_GELAP = """
<style>
:root{color-scheme:dark}
[data-testid="stApp"],[data-testid="stAppViewContainer"],[data-testid="stMain"]{background:#0f1722 !important;color:#e5e7eb}
.eyebrow{color:#5ccf9c !important}
.judul-hal,.sc-judul,.sc-val,.itm .jd,.perhatian,.brg{color:#f1f5f9 !important}
.kepala,.st-key-kartu_filter,.st-key-kartu_tabel,.st-key-kartu_utama,.st-key-kartu_perhatian,[class*="st-key-kartu_g"],
.statcard,[data-testid="stForm"],[data-testid="stExpander"],[class*="st-key-item_"],.akt{
  background:#172131 !important;border-color:#2a3547 !important;box-shadow:none !important;color:#e5e7eb !important}
.kepala .desk,.sc-ket,.sc-lab,.sub,.itm .mt,.itm .cat,.itm .qt span,.akt .am{color:#94a3b8 !important}
.sc-val.m,.itm .qt b.merah{color:#f87171 !important}
.sc-val.g,.itm .qt b{color:#4ade80 !important}
.sc-val.b,.itm .qt b.biru{color:#93c5fd !important}
.sc-stat{border-left-color:#2a3547 !important}
.perhatian,.garis{border-color:#2a3547 !important}
.bidang{background:#1b2d27 !important;color:#5ccf9c !important;border-left-color:#34a874 !important}
</style>
"""

FILE_LOKAL = os.environ.get("KEUANGAN_DATA_FILE", "keuangan_lokal.json")
FOTO_LOKAL = os.environ.get("KEUANGAN_FOTO_DIR", "struk_lokal")
TGL_MIN, TGL_MAX = date(2000, 1, 1), date(2100, 12, 31)
MAKS_AKTIVITAS = 1000
MASA_SAMPAH = 30
WIB = timezone(timedelta(hours=7))


def sekarang() -> datetime:
    return datetime.now(WIB)


def hari_ini() -> date:
    return sekarang().date()


def fmt_iso(s: str) -> str:
    try:
        return date.fromisoformat(s).strftime("%d/%m/%Y")
    except Exception:
        return s or ""


def fmt_waktu(s: str) -> str:
    try:
        return datetime.strptime(s, "%Y-%m-%d %H:%M").strftime("%d/%m/%Y %H:%M")
    except Exception:
        return s or ""


def iso_ke_date(s):
    try:
        return date.fromisoformat(s) if s else None
    except Exception:
        return None


def sisa_hari(s):
    d = iso_ke_date(s)
    return (d - hari_ini()).days if d else None


def rp(n) -> str:
    neg = "-" if n < 0 else ""
    return f"{neg}Rp " + f"{int(round(abs(n))):,}".replace(",", ".")


def data_kosong() -> dict:
    return {
        "dompet": [
            {"id": "d_bank", "nama": "Rekening Bank", "saldo_awal": 0},
            {"id": "d_ewallet", "nama": "E-Wallet", "saldo_awal": 0},
            {"id": "d_tunai", "nama": "Kas Tunai", "saldo_awal": 0},
        ],
        "kategori": [
            {"id": "k_gaji", "nama": "Gaji & Penghasilan", "tipe": "masuk", "anggaran": 0},
            {"id": "k_makan", "nama": "Makanan & Minuman", "tipe": "keluar", "anggaran": 1500000},
            {"id": "k_trans", "nama": "Transportasi", "tipe": "keluar", "anggaran": 500000},
            {"id": "k_tagihan", "nama": "Tagihan & Utilitas", "tipe": "keluar", "anggaran": 1000000},
            {"id": "k_belanja", "nama": "Belanja Kebutuhan", "tipe": "keluar", "anggaran": 1000000},
        ],
        "transaksi": [],
        "utang": [],
        "rencana": [],
        "aktivitas": [],
        "sampah": [],
    }


# ============================================================ PENYIMPANAN GITHUB
class Bentrok(Exception):
    """Data di GitHub sudah berubah sejak terakhir dimuat."""


def cfg_github():
    try:
        g = st.secrets["github"]
        return {"token": g["token"], "repo": g["repo"],
                "path": g.get("path", "keuangan.json"), "branch": g.get("branch", "main")}
    except Exception:
        return None


def _gh_url(c, path=None):
    return f"https://api.github.com/repos/{c['repo']}/contents/{path or c['path']}"


def _gh_headers(c):
    return {"Authorization": f"Bearer {c['token']}", "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28"}


def muat():
    c = cfg_github()
    if c:
        r = requests.get(_gh_url(c), headers=_gh_headers(c), params={"ref": c["branch"]}, timeout=20)
        if r.status_code == 404:
            return data_kosong(), None
        r.raise_for_status()
        j = r.json()
        isi = json.loads(base64.b64decode(j["content"]).decode("utf-8"))
        return isi, j["sha"]
    if os.path.exists(FILE_LOKAL):
        with open(FILE_LOKAL, encoding="utf-8") as f:
            return json.load(f), None
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
    else:
        with open(FILE_LOKAL, "w", encoding="utf-8") as f:
            f.write(teks)


def muat_ke_sesi():
    st.session_state.data, st.session_state.sha = muat()


def log_akt(jenis: str, nama: str, rincian: str = ""):
    log = st.session_state.data.setdefault("aktivitas", [])
    log.append({"id": uuid.uuid4().hex[:8], "waktu": sekarang().strftime("%Y-%m-%d %H:%M"),
                "oleh": pengguna_nama(), "jenis": jenis, "nama": nama, "rincian": rincian})
    if len(log) > MAKS_AKTIVITAS:
        st.session_state.data["aktivitas"] = log[-MAKS_AKTIVITAS:]


def commit(pesan_ok: str | None = None) -> bool:
    pesan = f"{pesan_ok or 'Perbarui data keuangan'} (oleh {pengguna_nama()})"
    try:
        simpan(st.session_state.data, pesan)
    except Bentrok:
        muat_ke_sesi()
        st.error("Data sudah diubah dari perangkat lain. Data terbaru telah dimuat, silakan ulangi.")
        return False
    except Exception as e:
        st.error(f"Gagal menyimpan: {e}")
        return False
    if pesan_ok:
        st.toast(pesan_ok, icon="✅")
    return True


def selesai_simpan(pesan: str, **setelah):
    if commit(pesan):
        for k, v in setelah.items():
            st.session_state[k] = v
        st.session_state.ver = st.session_state.get("ver", 0) + 1
        st.rerun()


# ================================================================ FOTO STRUK
def simpan_foto(id_trx: str, mentah: bytes) -> str:
    if Image is None:
        raise RuntimeError("Pustaka Pillow belum terpasang.")
    im = ImageOps.exif_transpose(Image.open(io.BytesIO(mentah))).convert("RGB")
    im.thumbnail((900, 900))
    out = io.BytesIO()
    im.save(out, "JPEG", quality=78, optimize=True)
    isi = out.getvalue()
    path = f"foto/struk_{id_trx}_{int(time.time())}.jpg"
    c = cfg_github()
    if c:
        body = {"message": f"Struk {id_trx}", "branch": c["branch"],
                "content": base64.b64encode(isi).decode("ascii")}
        r = requests.put(_gh_url(c, path), headers=_gh_headers(c), json=body, timeout=40)
        r.raise_for_status()
    else:
        os.makedirs(FOTO_LOKAL, exist_ok=True)
        with open(os.path.join(FOTO_LOKAL, os.path.basename(path)), "wb") as f:
            f.write(isi)
    return path


@st.cache_data(show_spinner=False, max_entries=200)
def _foto_gh(path: str, repo: str, branch: str, token: str):
    r = requests.get(f"https://api.github.com/repos/{repo}/contents/{path}", timeout=20,
                     headers={"Authorization": f"Bearer {token}", "Accept": "application/vnd.github.raw+json",
                              "X-GitHub-Api-Version": "2022-11-28"}, params={"ref": branch})
    return r.content if r.status_code == 200 else None


def ambil_foto(path: str):
    if not path:
        return None
    try:
        c = cfg_github()
        if c:
            return _foto_gh(path, c["repo"], c["branch"], c["token"])
        with open(os.path.join(FOTO_LOKAL, os.path.basename(path)), "rb") as f:
            return f.read()
    except Exception:
        return None


# ============================================================== LOGIN & AKSES
def _akun() -> dict:
    try:
        return {str(k): dict(v) for k, v in st.secrets["users"].items()}
    except Exception:
        return {}


def cocok_hash(sandi: str, tersimpan: str) -> bool:
    try:
        skema, iterasi, garam, h = str(tersimpan).split("$")
        if skema != "pbkdf2":
            return False
        calon = hashlib.pbkdf2_hmac("sha256", sandi.encode("utf-8"), bytes.fromhex(garam), int(iterasi))
        return hmac.compare_digest(calon.hex(), h)
    except Exception:
        return False


def pengguna_nama() -> str:
    u = st.session_state.get("user")
    return u["username"] if u else "pemilik"


def adalah_admin() -> bool:
    u = st.session_state.get("user")
    return u is None or u.get("peran") == "admin"


def cek_login():
    akun = _akun()
    if not akun:
        try:
            sandi = st.secrets["password"]
        except Exception:
            return
        if st.session_state.get("masuk"):
            return
        with st.form("login"):
            st.markdown("#### 🔒 Masuk ke Pencatat Keuangan")
            x = st.text_input("Kata sandi", type="password")
            if st.form_submit_button("Masuk", type="primary"):
                if hmac.compare_digest(x, str(sandi)):
                    st.session_state.masuk = True
                    st.rerun()
                st.error("Kata sandi salah.")
        st.stop()
    if st.session_state.get("user"):
        return
    with st.form("login_multi"):
        st.markdown("#### 🔒 Masuk ke Pencatat Keuangan")
        uname = st.text_input("Username").strip().lower()
        x = st.text_input("Kata sandi", type="password")
        if st.form_submit_button("Masuk", type="primary"):
            a = akun.get(uname)
            ok = cocok_hash(x, a["password_hash"] if a and "password_hash" in a else "pbkdf2$1$00$00")
            if a and ok:
                st.session_state.user = {"username": uname, "nama": a.get("nama", uname),
                                         "peran": a.get("peran", "admin")}
                st.rerun()
            st.error("Username atau kata sandi salah.")
    st.stop()


cek_login()

if "data" not in st.session_state:
    try:
        muat_ke_sesi()
    except Exception as e:
        st.error(f"Data tidak bisa dimuat: {e}")
        st.stop()

D = st.session_state.data
for k, awal in data_kosong().items():
    D.setdefault(k, awal)

if st.session_state.get("gelap"):
    st.markdown(CSS_GELAP, unsafe_allow_html=True)


# ============================================================ FUNGSI BANTU DATA
def atur(kunci: str, nilai):
    st.session_state[kunci] = nilai


def pindah_halaman(h: str):
    st.session_state.halaman = h
    for k in ("tx_mode", "tx_hapus", "ut_mode", "ut_hapus", "rc_mode", "rc_hapus"):
        st.session_state.pop(k, None)


def nama_dompet(id_d: str) -> str:
    d = next((x for x in D["dompet"] if x["id"] == id_d), None)
    return d["nama"] if d else "Tanpa dompet"


def nama_kat(id_k: str) -> str:
    k = next((x for x in D["kategori"] if x["id"] == id_k), None)
    return k["nama"] if k else "Tanpa kategori"


def saldo_dompet(id_d: str) -> int:
    d = next((x for x in D["dompet"] if x["id"] == id_d), None)
    saldo = int(d.get("saldo_awal", 0) or 0) if d else 0
    for t in D["transaksi"]:
        jml = int(t.get("jumlah", 0) or 0)
        if t.get("tipe") == "masuk" and t.get("dompet") == id_d:
            saldo += jml
        elif t.get("tipe") == "keluar" and t.get("dompet") == id_d:
            saldo -= jml
        elif t.get("tipe") == "transfer":
            if t.get("dompet") == id_d:
                saldo -= jml
            if t.get("ke_dompet") == id_d:
                saldo += jml
    return saldo


def kartu_tx_html(t: dict) -> str:
    tipe = t.get("tipe", "keluar")
    jml = int(t.get("jumlah", 0) or 0)
    if tipe == "masuk":
        ic, kls_ic, tanda, kls_b, lbl = "↙", "", "+", "", "Pemasukan"
        lenc = '<span class="lencana lc-h">Masuk</span>'
        meta = [fmt_iso(t.get("tanggal", "")), nama_dompet(t.get("dompet", "")), nama_kat(t.get("kategori", ""))]
    elif tipe == "transfer":
        ic, kls_ic, tanda, kls_b, lbl = "⇄", " trf", "", "biru", "Transfer"
        lenc = '<span class="lencana lc-b">Transfer</span>'
        meta = [fmt_iso(t.get("tanggal", "")), f"{nama_dompet(t.get('dompet', ''))} → {nama_dompet(t.get('ke_dompet', ''))}"]
    else:
        ic, kls_ic, tanda, kls_b, lbl = "↗", " out", "-", "merah", "Pengeluaran"
        lenc = '<span class="lencana lc-r">Keluar</span>'
        meta = [fmt_iso(t.get("tanggal", "")), nama_dompet(t.get("dompet", "")), nama_kat(t.get("kategori", ""))]

    cat = f'<div class="cat">{html.escape(t["catatan"])}</div>' if t.get("catatan") else ""
    return (f'<div class="itm"><div class="ic{kls_ic}">{ic}</div><div class="isi">'
            f'<div class="jd">{html.escape(t.get("judul", "Transaksi"))}{lenc}</div>'
            f'<div class="mt">{html.escape(" • ".join(meta))}</div>{cat}</div>'
            f'<div class="qt"><b class="{kls_b}">{tanda}{rp(jml)}</b><span>{lbl}</span></div></div>')


# ============================================================ NAVIGASI SIDEBAR
if not cfg_github():
    st.warning("Mode uji coba: data disimpan di file lokal. Isi pengaturan `[github]` di Streamlit Secrets agar tersimpan permanen di repositori privat.")

UTAMA = ["Cari & saring", "Kelola transaksi", "Saldo dompet", "Riwayat aktivitas", "Tempat sampah"]
PANTAU = ["Anggaran bulanan", "Utang & piutang", "Target tabungan"]
MASTER = ["Dompet & rekening", "Kategori & anggaran", "Cadangan data"]
HALAMAN = ["Beranda"] + UTAMA + PANTAU + (MASTER if adalah_admin() else [])

if st.session_state.get("halaman") not in HALAMAN:
    st.session_state.halaman = "Beranda"
halaman = st.session_state.halaman

IKON = {
    "Beranda": "home", "Cari & saring": "search", "Kelola transaksi": "receipt_long",
    "Saldo dompet": "account_balance_wallet", "Riwayat aktivitas": "manage_history", "Tempat sampah": "delete",
    "Anggaran bulanan": "pie_chart", "Utang & piutang": "handshake", "Target tabungan": "savings",
    "Dompet & rekening": "credit_card", "Kategori & anggaran": "sell", "Cadangan data": "backup",
}

LOGO = ('<svg width="38" height="38" viewBox="0 0 38 38" xmlns="http://www.w3.org/2000/svg">'
        '<defs><linearGradient id="g" x1="0" y1="0" x2="1" y2="1">'
        '<stop offset="0" stop-color="#34a874"/><stop offset="1" stop-color="#1f6b49"/></linearGradient></defs>'
        '<rect width="38" height="38" rx="10" fill="url(#g)"/>'
        '<path d="M10 13h18a2 2 0 0 1 2 2v10a2 2 0 0 1-2 2H10a2 2 0 0 1-2-2V15a2 2 0 0 1 2-2zm14 7a1.5 1.5 0 1 0 0-3 1.5 1.5 0 0 0 0 3z" '
        'fill="none" stroke="#fff" stroke-width="2" stroke-linejoin="round"/></svg>')

with st.sidebar:
    st.markdown(f'<div class="brand">{LOGO}<div><div class="b1">KeuanganKu</div>'
                '<div class="b2">Keuangan & arus kas</div></div></div>', unsafe_allow_html=True)

    def tombol_nav(h):
        st.button(h, key=f"nav_{h}", use_container_width=True, icon=f":material/{IKON[h]}:",
                  type="primary" if h == halaman else "secondary", on_click=pindah_halaman, args=(h,))

    st.markdown('<div class="grup">UTAMA</div>', unsafe_allow_html=True)
    tombol_nav("Beranda")
    st.markdown('<div class="grup">MENU</div>', unsafe_allow_html=True)
    with st.expander("Transaksi", icon=":material/receipt_long:", expanded=halaman in UTAMA):
        for h in UTAMA:
            tombol_nav(h)
    with st.expander("Pantau", icon=":material/monitoring:", expanded=halaman in PANTAU):
        for h in PANTAU:
            tombol_nav(h)
    if adalah_admin():
        with st.expander("Pengaturan", icon=":material/settings:", expanded=halaman in MASTER):
            for h in MASTER:
                tombol_nav(h)
    st.markdown('<div class="sp"></div>', unsafe_allow_html=True)
    st.toggle("Mode gelap", key="gelap")
    if st.button("Muat ulang", key="nav_muat", use_container_width=True, icon=":material/refresh:"):
        muat_ke_sesi()
        st.rerun()
    if cfg_github():
        st.caption(f"Repo: {cfg_github()['repo']}")

DESKRIPSI = {
    "Beranda": "Ringkasan saldo bersih, arus kas bulan ini, peringatan anggaran, dan grafik.",
    "Cari & saring": "Cari dan saring transaksi berdasarkan bulan, dompet, kategori, atau kata kunci.",
    "Kelola transaksi": "Tambah pemasukan, pengeluaran, atau transfer antar dompet beserta foto struk.",
    "Saldo dompet": "Rincian saldo terkini di setiap rekening bank, e-wallet, dan kas tunai.",
    "Riwayat aktivitas": "Catatan otomatis setiap penambahan, pengeditan, atau penghapusan transaksi.",
    "Tempat sampah": "Transaksi yang dihapus disimpan 30 hari di sini dan bisa dipulihkan kembali.",
    "Anggaran bulanan": "Pantau batas anggaran per kategori pengeluaran agar tidak melebihi target.",
    "Utang & piutang": "Catat uang yang dipinjam atau dipinjamkan beserta pengingat jatuh tempo.",
    "Target tabungan": "Rencana pembelian atau dana darurat yang ingin dicapai.",
    "Dompet & rekening": "Kelola daftar rekening bank, dompet digital, dan saldo awalnya.",
    "Kategori & anggaran": "Kelola kategori pemasukan/pengeluaran beserta batas anggaran bulanannya.",
    "Cadangan data": "Unduh seluruh data dalam bentuk JSON/CSV atau pulihkan dari berkas.",
}
_grup = ("PENGATURAN" if halaman in MASTER else "RINGKASAN" if halaman == "Beranda"
         else "PANTAU" if halaman in PANTAU else "TRANSAKSI")
st.markdown(f'<div class="kepala"><div><div class="eyebrow">{_grup}</div>'
            f'<div class="judul-hal">{html.escape(halaman)}</div>'
            f'<div class="desk">{html.escape(DESKRIPSI.get(halaman, ""))}</div></div></div>',
            unsafe_allow_html=True)


# ==================================================================== BERANDA
if halaman == "Beranda":
    bln_ini = hari_ini().strftime("%Y-%m")
    tx_bln = [t for t in D["transaksi"] if t.get("tanggal", "").startswith(bln_ini)]
    masuk_bln = sum(int(t.get("jumlah", 0)) for t in tx_bln if t.get("tipe") == "masuk")
    keluar_bln = sum(int(t.get("jumlah", 0)) for t in tx_bln if t.get("tipe") == "keluar")
    total_saldo = sum(saldo_dompet(d["id"]) for d in D["dompet"])
    utang_aktif = sum(1 for u in D["utang"] if not u.get("lunas"))

    st.markdown(
        f'<div class="statcard"><div class="sc-kiri"><span class="tag">Total Saldo Bersih</span>'
        f'<div class="sc-judul">{rp(total_saldo)}</div>'
        f'<div class="sc-ket">Tersebar di {len(D["dompet"])} dompet / rekening</div></div>'
        f'<div class="sc-stat"><div class="sc-lab">Masuk ({bln_ini})</div><div class="sc-val g">{rp(masuk_bln)}</div></div>'
        f'<div class="sc-stat"><div class="sc-lab">Keluar ({bln_ini})</div><div class="sc-val m">{rp(keluar_bln)}</div></div>'
        f'<div class="sc-stat"><div class="sc-lab">Selisih Bulan Ini</div><div class="sc-val b">{rp(masuk_bln - keluar_bln)}</div></div>'
        f'<div class="sc-stat"><div class="sc-lab">Utang/Piutang Aktif</div><div class="sc-val">{utang_aktif}</div></div>'
        '</div>', unsafe_allow_html=True)

    perhatian = []
    for k in D["kategori"]:
        ang = int(k.get("anggaran", 0) or 0)
        if k.get("tipe") == "keluar" and ang > 0:
            pakai = sum(int(t.get("jumlah", 0)) for t in tx_bln if t.get("tipe") == "keluar" and t.get("kategori") == k["id"])
            if pakai > ang:
                perhatian.append(f"⛔ <b>Anggaran terlampaui:</b> {html.escape(k['nama'])} ({rp(pakai)} dari batas {rp(ang)})")
            elif pakai >= ang * 0.8:
                perhatian.append(f"⚠️ <b>Anggaran hampir habis:</b> {html.escape(k['nama'])} ({int(pakai*100/ang)}% terpakai)")
    for u in D["utang"]:
        s = sisa_hari(u.get("tenggat"))
        if not u.get("lunas") and s is not None and s <= 7:
            ket = f"lewat {-s} hari" if s < 0 else ("hari ini" if s == 0 else f"{s} hari lagi")
            perhatian.append(f"🔔 <b>Jatuh tempo {u.get('arah')}:</b> {html.escape(u.get('nama', ''))} ({html.escape(u.get('orang', ''))}) — {ket}")

    with st.container(key="kartu_perhatian"):
        st.markdown("**Perlu perhatian**")
        if perhatian:
            for p in perhatian:
                st.markdown(f'<div class="perhatian">{p}</div>', unsafe_allow_html=True)
        else:
            st.caption("Semua anggaran dan catatan utang/piutang dalam kondisi aman.")

    g1, g2 = st.columns(2)
    with g1.container(key="kartu_g1"):
        st.markdown("**Saldo per dompet**")
        df_d = pd.DataFrame([{"Dompet": d["nama"], "Saldo": saldo_dompet(d["id"])} for d in D["dompet"]])
        if not df_d.empty:
            st.bar_chart(df_d, x="Dompet", y="Saldo", horizontal=True, color="#2b7a57", height=260)
    with g2.container(key="kartu_g2"):
        st.markdown(f"**Pengeluaran per kategori ({bln_ini})**")
        per_k = {}
        for t in tx_bln:
            if t.get("tipe") == "keluar":
                nk = nama_kat(t.get("kategori", ""))
                per_k[nk] = per_k.get(nk, 0) + int(t.get("jumlah", 0))
        if per_k:
            st.bar_chart(pd.DataFrame({"Kategori": list(per_k), "Jumlah": list(per_k.values())}),
                         x="Kategori", y="Jumlah", horizontal=True, color="#b42318", height=260)
        else:
            st.caption("Belum ada pengeluaran bulan ini.")


# =========================================================== KELOLA TRANSAKSI
if halaman == "Kelola transaksi":
    by_id = {t["id"]: t for t in D["transaksi"]}
    mode = st.session_state.get("tx_mode")
    with st.container(key="kartu_utama"):
        if mode:
            t_lama = by_id.get(mode, {})
            st.markdown("#### Form Transaksi")
            tipe_map = {"keluar": "Pengeluaran", "masuk": "Pemasukan", "transfer": "Transfer Antar Dompet"}
            tipe_pil = st.segmented_control("Tipe Transaksi", list(tipe_map.keys()),
                                            default=t_lama.get("tipe", "keluar"),
                                            format_func=lambda x: tipe_map[x], key=f"tx_tipe_{mode}") or "keluar"
            with st.form(f"form_tx_{mode}"):
                c1, c2 = st.columns([3, 2])
                judul = c1.text_input("Judul / Keperluan", value=t_lama.get("judul", ""), placeholder="Contoh: Makan siang, Gaji bulanan")
                jumlah = c2.number_input("Nominal (Rp)", min_value=0, value=int(t_lama.get("jumlah", 0) or 0), step=5000)

                d1, d2, d3 = st.columns(3)
                tgl = d1.date_input("Tanggal", value=iso_ke_date(t_lama.get("tanggal")) or hari_ini(), format="DD/MM/YYYY")
                pd_map = {d["id"]: d["nama"] for d in D["dompet"]}
                dompet = d2.selectbox("Dompet / Rekening", list(pd_map), format_func=lambda i: pd_map[i],
                                      index=list(pd_map).index(t_lama["dompet"]) if t_lama.get("dompet") in pd_map else 0)
                ke_dompet, kat = "", ""
                if tipe_pil == "transfer":
                    ke_dompet = d3.selectbox("Ke Dompet Tujuan", list(pd_map), format_func=lambda i: pd_map[i])
                else:
                    pk_map = {k["id"]: k["nama"] for k in D["kategori"] if k.get("tipe") == tipe_pil}
                    if not pk_map:
                        pk_map = {k["id"]: k["nama"] for k in D["kategori"]}
                    kat = d3.selectbox("Kategori", list(pk_map), format_func=lambda i: pk_map[i])

                catatan = st.text_input("Catatan tambahan (opsional)", value=t_lama.get("catatan", ""))
                upl = st.file_uploader("Foto struk / bukti (opsional)", type=["jpg", "jpeg", "png", "webp"])
                b1, b2, _ = st.columns([1.2, 1, 3])
                simpan_btn = b1.form_submit_button("Simpan", type="primary")
                batal_btn = b2.form_submit_button("Kembali")

            if batal_btn:
                st.session_state.tx_mode = None
                st.rerun()
            if simpan_btn:
                if not judul.strip() or jumlah <= 0:
                    st.error("Judul dan nominal (lebih dari Rp 0) wajib diisi.")
                elif tipe_pil == "transfer" and dompet == ke_dompet:
                    st.error("Dompet asal dan tujuan tidak boleh sama.")
                else:
                    id_ = t_lama.get("id") or uuid.uuid4().hex[:8]
                    foto_path = t_lama.get("foto", "")
                    if upl is not None:
                        try:
                            foto_path = simpan_foto(id_, upl.getvalue())
                        except Exception as e:
                            st.error(f"Gagal mengunggah foto struk: {e}")
                            st.stop()
                    baru = {
                        "id": id_, "tanggal": tgl.isoformat(), "tipe": tipe_pil,
                        "judul": judul.strip(), "jumlah": int(jumlah), "dompet": dompet,
                        "ke_dompet": ke_dompet, "kategori": kat, "catatan": catatan.strip(),
                        "foto": foto_path, "oleh": pengguna_nama()
                    }
                    if mode == "baru":
                        D["transaksi"].append(baru)
                        log_akt("tambah", baru["judul"], f"{tipe_map[tipe_pil]} {rp(jumlah)}")
                    else:
                        D["transaksi"] = [baru if x["id"] == mode else x for x in D["transaksi"]]
                        log_akt("ubah", baru["judul"], f"Diperbarui menjadi {rp(jumlah)}")
                    selesai_simpan("Transaksi disimpan.", tx_mode=None)
        else:
            kc, kt = st.columns([5, 2], vertical_alignment="center")
            cari = kc.text_input("Cari", placeholder="Cari judul atau catatan...", label_visibility="collapsed").lower().strip()
            kt.button("Tambah Transaksi", type="primary", icon=":material/add:", use_container_width=True,
                      on_click=atur, args=("tx_mode", "baru"))

            urut = sorted(D["transaksi"], key=lambda x: x.get("tanggal", ""), reverse=True)
            if cari:
                urut = [t for t in urut if cari in f"{t.get('judul','')} {t.get('catatan','')}".lower()]

            if not urut:
                st.info("Belum ada transaksi yang tercatat.")
            for t in urut[:100]:
                with st.container(key=f"item_tx_{t['id']}"):
                    st.markdown(kartu_tx_html(t), unsafe_allow_html=True)
                    if t.get("foto"):
                        with st.expander("Lihat foto struk"):
                            dat = ambil_foto(t["foto"])
                            if dat:
                                st.image(dat, width=280)
                    e1, e2, _ = st.columns([1, 1, 4])
                    e1.button("Edit", key=f"kedit_{t['id']}", on_click=atur, args=("tx_mode", t["id"]), use_container_width=True)
                    if e2.button("Hapus", key=f"khapus_{t['id']}", use_container_width=True):
                        D["transaksi"] = [x for x in D["transaksi"] if x["id"] != t["id"]]
                        D["sampah"].append({"id": uuid.uuid4().hex[:8], "transaksi": dict(t),
                                            "dihapus": sekarang().strftime("%Y-%m-%d %H:%M"), "oleh": pengguna_nama()})
                        log_akt("buang", t.get("judul", ""), rp(t.get("jumlah", 0)))
                        selesai_simpan("Dipindahkan ke tempat sampah.")


# ============================================================== CARI & SARING
if halaman == "Cari & saring":
    with st.container(key="kartu_filter"):
        q = st.text_input("Kata kunci", icon=":material/search:", placeholder="Cari judul transaksi atau catatan...", label_visibility="collapsed").lower().strip()
        c1, c2, c3, c4 = st.columns(4)
        daftar_bln = ["semua"] + sorted({t.get("tanggal", "")[:7] for t in D["transaksi"] if t.get("tanggal")}, reverse=True)
        f_bln = c1.selectbox("Periode Bulan", daftar_bln, format_func=lambda x: "Semua waktu" if x == "semua" else x)
        f_tipe = c2.selectbox("Tipe", ["semua", "masuk", "keluar", "transfer"], format_func=lambda x: x.capitalize())
        pd_map = {"semua": "Semua dompet", **{d["id"]: d["nama"] for d in D["dompet"]}}
        f_dom = c3.selectbox("Dompet", list(pd_map), format_func=lambda i: pd_map[i])
        pk_map = {"semua": "Semua kategori", **{k["id"]: k["nama"] for k in D["kategori"]}}
        f_kat = c4.selectbox("Kategori", list(pk_map), format_func=lambda i: pk_map[i])

    hasil = D["transaksi"]
    if f_bln != "semua":
        hasil = [t for t in hasil if t.get("tanggal", "").startswith(f_bln)]
    if f_tipe != "semua":
        hasil = [t for t in hasil if t.get("tipe") == f_tipe]
    if f_dom != "semua":
        hasil = [t for t in hasil if t.get("dompet") == f_dom or t.get("ke_dompet") == f_dom]
    if f_kat != "semua":
        hasil = [t for t in hasil if t.get("kategori") == f_kat]
    if q:
        hasil = [t for t in hasil if q in f"{t.get('judul','')} {t.get('catatan','')}".lower()]

    t_in = sum(int(t.get("jumlah", 0)) for t in hasil if t.get("tipe") == "masuk")
    t_out = sum(int(t.get("jumlah", 0)) for t in hasil if t.get("tipe") == "keluar")
    st.caption(f"Menampilkan {len(hasil)} transaksi · Total Masuk: **{rp(t_in)}** · Total Keluar: **{rp(t_out)}**")

    for t in sorted(hasil, key=lambda x: x.get("tanggal", ""), reverse=True):
        with st.container(key=f"item_c_{t['id']}"):
            st.markdown(kartu_tx_html(t), unsafe_allow_html=True)


# =============================================================== SALDO DOMPET
if halaman == "Saldo dompet":
    with st.container(key="kartu_utama"):
        for d in D["dompet"]:
            s = saldo_dompet(d["id"])
            st.markdown(
                f'<div class="itm"><div class="ic">💳</div><div class="isi">'
                f'<div class="jd">{html.escape(d["nama"])}</div>'
                f'<div class="mt">Saldo awal: {rp(d.get("saldo_awal", 0))}</div></div>'
                f'<div class="qt"><b class="{"merah" if s < 0 else ""}">{rp(s)}</b><span>Saldo saat ini</span></div></div>',
                unsafe_allow_html=True)
            st.markdown('<div class="garis"></div>', unsafe_allow_html=True)


# =========================================================== ANGGARAN BULANAN
if halaman == "Anggaran bulanan":
    bln_ini = hari_ini().strftime("%Y-%m")
    tx_bln = [t for t in D["transaksi"] if t.get("tanggal", "").startswith(bln_ini) and t.get("tipe") == "keluar"]
    with st.container(key="kartu_utama"):
        st.markdown(f"#### Pemakaian Anggaran Bulan Ini (`{bln_ini}`)")
        for k in [x for x in D["kategori"] if x.get("tipe") == "keluar"]:
            ang = int(k.get("anggaran", 0) or 0)
            pakai = sum(int(t.get("jumlah", 0)) for t in tx_bln if t.get("kategori") == k["id"])
            st.markdown(f"**{k['nama']}** — {rp(pakai)} / {rp(ang) if ang else 'Tanpa batas'}")
            if ang > 0:
                st.progress(min(1.0, pakai / ang), text=f"{int(pakai * 100 / ang)}% terpakai · Sisa {rp(max(ang - pakai, 0))}")
            st.markdown('<div class="garis"></div>', unsafe_allow_html=True)


# ============================================================ UTANG & PIUTANG
if halaman == "Utang & piutang":
    aktif = [u for u in D["utang"] if not u.get("lunas")]
    lunas = [u for u in D["utang"] if u.get("lunas")]
    with st.container(key="kartu_utama"):
        with st.expander("➕ Catat Utang / Piutang Baru"):
            with st.form("form_utang", clear_on_submit=True):
                arah = st.radio("Jenis", ["utang", "piutang"], horizontal=True,
                                format_func=lambda x: "Saya berutang (Utang)" if x == "utang" else "Orang meminjam ke saya (Piutang)")
                c1, c2, c3 = st.columns(3)
                nama = c1.text_input("Keperluan / Keterangan")
                orang = c2.text_input("Nama Orang / Lembaga")
                jml = c3.number_input("Jumlah (Rp)", min_value=0, step=10000)
                tenggat = st.date_input("Jatuh Tempo (opsional)", value=None, format="DD/MM/YYYY")
                if st.form_submit_button("Simpan Catatan", type="primary"):
                    if nama.strip() and orang.strip() and jml > 0:
                        D["utang"].append({
                            "id": uuid.uuid4().hex[:8], "arah": arah, "nama": nama.strip(),
                            "orang": orang.strip(), "jumlah": int(jml), "tanggal": hari_ini().isoformat(),
                            "tenggat": tenggat.isoformat() if tenggat else "", "lunas": ""
                        })
                        selesai_simpan("Catatan utang/piutang disimpan.")
                    else:
                        st.error("Lengkapi nama keperluan, orang, dan nominal.")

        st.markdown(f"#### Belum Lunas ({len(aktif)})")
        if not aktif:
            st.caption("Tidak ada utang atau piutang aktif.")
        for u in aktif:
            lenc = '<span class="lencana lc-r">Utang Saya</span>' if u["arah"] == "utang" else '<span class="lencana lc-b">Piutang</span>'
            tgt = f" • Jatuh tempo: {fmt_iso(u['tenggat'])}" if u.get("tenggat") else ""
            st.markdown(
                f'<div class="itm"><div class="ic">🤝</div><div class="isi">'
                f'<div class="jd">{html.escape(u["nama"])}{lenc}</div>'
                f'<div class="mt">{html.escape(u["orang"])}{tgt}</div></div>'
                f'<div class="qt"><b class="{"merah" if u["arah"]=="utang" else ""}">{rp(u["jumlah"])}</b></div></div>',
                unsafe_allow_html=True)
            if st.button("Tandai Sudah Lunas", key=f"lunas_{u['id']}"):
                u["lunas"] = hari_ini().isoformat()
                selesai_simpan("Ditandai lunas.")
            st.markdown('<div class="garis"></div>', unsafe_allow_html=True)


# ============================================================ TARGET TABUNGAN
if halaman == "Target tabungan":
    with st.container(key="kartu_utama"):
        with st.expander("➕ Buat Target Baru"):
            with st.form("form_target", clear_on_submit=True):
                c1, c2, c3 = st.columns(3)
                nama = c1.text_input("Nama Target (Contoh: Dana Darurat / Beli Laptop)")
                target = c2.number_input("Target Nominal (Rp)", min_value=0, step=100000)
                terkumpul = c3.number_input("Sudah Terkumpul (Rp)", min_value=0, step=50000)
                if st.form_submit_button("Simpan Target", type="primary"):
                    if nama.strip() and target > 0:
                        D["rencana"].append({"id": uuid.uuid4().hex[:8], "nama": nama.strip(),
                                             "target": int(target), "terkumpul": int(terkumpul)})
                        selesai_simpan("Target ditambahkan.")
        if not D["rencana"]:
            st.info("Belum ada target tabungan.")
        for r in D["rencana"]:
            tgt = max(int(r.get("target", 1)), 1)
            kmp = int(r.get("terkumpul", 0))
            st.markdown(f"**{r['nama']}** — {rp(kmp)} dari {rp(tgt)}")
            st.progress(min(1.0, kmp / tgt), text=f"{int(kmp * 100 / tgt)}% tercapai · Kurang {rp(max(tgt - kmp, 0))}")
            c1, c2 = st.columns([3, 1], vertical_alignment="bottom")
            tambah_n = c1.number_input("Update jumlah terkumpul (Rp)", min_value=0, value=kmp, step=50000, key=f"tr_{r['id']}")
            if c2.button("Perbarui", key=f"tr_btn_{r['id']}", use_container_width=True):
                r["terkumpul"] = int(tambah_n)
                selesai_simpan("Progres tabungan diperbarui.")
            st.markdown('<div class="garis"></div>', unsafe_allow_html=True)


# ================================================= RIWAYAT AKTIVITAS & SAMPAH
if halaman == "Riwayat aktivitas":
    with st.container(key="kartu_utama"):
        log = sorted(D.get("aktivitas", []), key=lambda x: x.get("waktu", ""), reverse=True)
        if not log:
            st.info("Belum ada riwayat aktivitas.")
        for x in log[:100]:
            st.markdown(
                f'<div class="akt"><div class="ah">{html.escape(x.get("nama", ""))} '
                f'<span class="lencana lc-b">{html.escape(x.get("jenis", ""))}</span></div>'
                f'<div class="ar">{html.escape(x.get("rincian", ""))}</div>'
                f'<div class="am">{fmt_waktu(x.get("waktu", ""))} · oleh {html.escape(x.get("oleh", ""))}</div></div>',
                unsafe_allow_html=True)

if halaman == "Tempat sampah":
    with st.container(key="kartu_utama"):
        if not D["sampah"]:
            st.info("Tempat sampah kosong.")
        for s in D["sampah"]:
            t = s["transaksi"]
            st.markdown(kartu_tx_html(t), unsafe_allow_html=True)
            c1, c2, _ = st.columns([1.2, 1.2, 3])
            if c1.button("Pulihkan", key=f"pulih_{s['id']}", type="primary"):
                D["transaksi"].append(t)
                D["sampah"] = [x for x in D["sampah"] if x["id"] != s["id"]]
                log_akt("pulih", t.get("judul", ""), rp(t.get("jumlah", 0)))
                selesai_simpan("Transaksi dipulihkan.")
            if c2.button("Hapus Permanen", key=f"hapus_p_{s['id']}"):
                D["sampah"] = [x for x in D["sampah"] if x["id"] != s["id"]]
                selesai_simpan("Dihapus permanen.")


# ======================================================== PENGATURAN (MASTER)
if adalah_admin() and halaman == "Dompet & rekening":
    with st.container(key="kartu_utama"):
        for d in D["dompet"]:
            c1, c2, c3 = st.columns([3, 2, 1], vertical_alignment="bottom")
            nm = c1.text_input("Nama Dompet", value=d["nama"], key=f"dn_{d['id']}")
            sa = c2.number_input("Saldo Awal (Rp)", value=int(d.get("saldo_awal", 0)), step=50000, key=f"ds_{d['id']}")
            if c3.button("Simpan", key=f"db_{d['id']}", use_container_width=True):
                d["nama"], d["saldo_awal"] = nm.strip(), int(sa)
                selesai_simpan("Dompet diperbarui.")
        st.markdown('<div class="garis"></div>', unsafe_allow_html=True)
        with st.form("tambah_dompet", clear_on_submit=True):
            st.markdown("#### Tambah Dompet Baru")
            c1, c2 = st.columns(2)
            nama = c1.text_input("Nama Dompet (Contoh: BCA, GoPay)")
            saldo_awal = c2.number_input("Saldo Awal (Rp)", value=0, step=50000)
            if st.form_submit_button("Tambah Dompet", type="primary"):
                if nama.strip():
                    D["dompet"].append({"id": uuid.uuid4().hex[:8], "nama": nama.strip(), "saldo_awal": int(saldo_awal)})
                    selesai_simpan("Dompet ditambahkan.")

if adalah_admin() and halaman == "Kategori & anggaran":
    with st.container(key="kartu_utama"):
        for k in D["kategori"]:
            c1, c2, c3, c4 = st.columns([3, 1.5, 2, 1], vertical_alignment="bottom")
            nm = c1.text_input("Kategori", value=k["nama"], key=f"kn_{k['id']}")
            tp = c2.selectbox("Tipe", ["keluar", "masuk"], index=0 if k.get("tipe") == "keluar" else 1, key=f"kt_{k['id']}")
            ang = c3.number_input("Batas Anggaran/Bln (Rp)", min_value=0, value=int(k.get("anggaran", 0)), step=50000, key=f"ka_{k['id']}")
            if c4.button("Simpan", key=f"kb_{k['id']}", use_container_width=True):
                k["nama"], k["tipe"], k["anggaran"] = nm.strip(), tp, int(ang)
                selesai_simpan("Kategori diperbarui.")
        st.markdown('<div class="garis"></div>', unsafe_allow_html=True)
        with st.form("tambah_kategori", clear_on_submit=True):
            st.markdown("#### Tambah Kategori Baru")
            c1, c2, c3 = st.columns(3)
            nama = c1.text_input("Nama Kategori")
            tipe = c2.selectbox("Tipe", ["keluar", "masuk"])
            anggaran = c3.number_input("Anggaran Bulanan (Rp)", min_value=0, value=0, step=50000)
            if st.form_submit_button("Tambah Kategori", type="primary"):
                if nama.strip():
                    D["kategori"].append({"id": uuid.uuid4().hex[:8], "nama": nama.strip(), "tipe": tipe, "anggaran": int(anggaran)})
                    selesai_simpan("Kategori ditambahkan.")

if adalah_admin() and halaman == "Cadangan data":
    with st.container(key="kartu_utama"):
        st.caption("Unduh seluruh data dalam format JSON (untuk pemulihan penuh) atau CSV (untuk dibuka di Excel).")
        c1, c2 = st.columns(2)
        c1.download_button("⬇️ Unduh keuangan.json", json.dumps(D, ensure_ascii=False, indent=1),
                           file_name="keuangan.json", mime="application/json", use_container_width=True)
        if D["transaksi"]:
            df_csv = pd.DataFrame(D["transaksi"])
            c2.download_button("⬇️ Ekspor Transaksi (.csv)", df_csv.to_csv(index=False).encode("utf-8"),
                               file_name="transaksi_keuangan.csv", mime="text/csv", use_container_width=True)
        st.markdown('<div class="garis"></div>', unsafe_allow_html=True)
        with st.form("impor_json"):
            berkas = st.file_uploader("Pulihkan dari file keuangan.json", type=["json"])
            yakin = st.checkbox("Ya, timpa seluruh data saat ini dengan isi file ini")
            if st.form_submit_button("Muat & Timpa Data", type="primary"):
                if berkas and yakin:
                    baru = json.load(berkas)
                    for k, awal in data_kosong().items():
                        baru.setdefault(k, awal)
                    st.session_state.data = baru
                    selesai_simpan("Data berhasil dipulihkan.")
