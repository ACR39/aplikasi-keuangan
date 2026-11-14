"""Kunci aplikasi dengan PIN: terkunci saat sesi dipulihkan dari cookie (buka ulang/refresh) atau saat tombol Kunci ditekan."""
import hashlib
import os
import time

import streamlit as st

from keuangan.akses import KUNCI_DETIK, MAKS_GAGAL, cocok_hash, keluar
from keuangan.bantu import catat, selesai_simpan
from keuangan.inti import D, hanya_lihat


def _nama() -> str:
    u = st.session_state.get("user")
    return u["username"] if u else "_"


def buat_hash_pin(pin: str) -> str:
    garam = os.urandom(12)
    return f"pbkdf2$120000${garam.hex()}${hashlib.pbkdf2_hmac('sha256', pin.encode(), garam, 120000).hex()}"


def pin_tersimpan() -> str:
    return D.get("pengaturan", {}).get("pin", {}).get(_nama(), "")


def punya_pin() -> bool:
    return bool(pin_tersimpan())


def kunci_sekarang():
    st.session_state.terkunci = True


def _buka(pin: str) -> bool:
    return cocok_hash(pin, pin_tersimpan())


def cek_pin():
    """Dipanggil setelah data dimuat. Menampilkan layar kunci dan menghentikan skrip bila perlu."""
    if not punya_pin():
        return
    if "terkunci" not in st.session_state:
        # sesi baru: terkunci bila dipulihkan dari cookie, terbuka bila baru saja masuk dengan kata sandi
        st.session_state.terkunci = bool(st.session_state.get("dari_cookie"))
    if not st.session_state.terkunci:
        return
    sisa = st.session_state.get("pin_kunci_sampai", 0) - time.time()
    st.markdown("""<style>[data-testid="stSidebar"],[data-testid="stSidebarCollapsedControl"],[data-testid="stToolbar"],[data-testid="stHeader"]{display:none !important}
.block-container{max-width:420px !important;padding:14vh 1.2rem 3rem !important}</style>
<div style="text-align:center;margin-bottom:1rem"><div style="font-size:2.4rem"></div>
<div style="font-size:1.4rem;font-weight:700">Aplikasi terkunci</div><div style="color:#64748b;font-size:.9rem">Masukkan PIN untuk melanjutkan</div></div>""",
                unsafe_allow_html=True)
    with st.form("form_pin"):
        pin = st.text_input("PIN", type="password", max_chars=12, placeholder="PIN")
        kirim = st.form_submit_button("Buka", width="stretch", disabled=sisa > 0)
    if sisa > 0:
        st.error(f"Terlalu banyak percobaan. Coba lagi dalam {int(sisa) + 1} detik.")
    elif kirim:
        if _buka(pin):
            st.session_state.terkunci = False
            st.session_state.pin_gagal = 0
            st.rerun()
        st.session_state.pin_gagal = st.session_state.get("pin_gagal", 0) + 1
        if st.session_state.pin_gagal >= MAKS_GAGAL:
            st.session_state.pin_gagal = 0
            st.session_state.pin_kunci_sampai = time.time() + KUNCI_DETIK
            st.rerun()
        st.error("PIN salah.")
    if st.session_state.get("user"):
        st.button("Keluar akun", key="pin_keluar", on_click=keluar)
    st.stop()


def panel_pin():
    """Atur PIN (di halaman Tampilan)."""
    if hanya_lihat():
        return
    with st.container(key="kartu_g_pin"):
        st.markdown("**Kunci PIN**")
        st.caption("PIN dipakai untuk membuka aplikasi saat dibuka ulang di perangkat yang masih tersambung (tanpa mengetik kata sandi lagi). "
                   "Tombol Kunci di menu samping mengunci seketika. PIN ini khusus untuk akunmu.")
        if punya_pin():
            st.success("PIN aktif.")
        with st.form("f_pin"):
            baru = st.text_input("PIN baru (4–12 angka)", type="password", max_chars=12)
            ulang = st.text_input("Ulangi PIN", type="password", max_chars=12)
            c1, c2 = st.columns(2)
            simpan = c1.form_submit_button("Simpan PIN", type="primary")
            hapus = c2.form_submit_button("Hapus PIN", disabled=not punya_pin())
        if simpan:
            if not (baru.isdigit() and 4 <= len(baru) <= 12):
                st.error("PIN harus 4–12 angka.")
            elif baru != ulang:
                st.error("Kedua PIN tidak sama.")
            else:
                D["pengaturan"].setdefault("pin", {})[_nama()] = buat_hash_pin(baru)
                catat("data", "PIN diatur")
                selesai_simpan("PIN disimpan.")
        elif hapus:
            D["pengaturan"].get("pin", {}).pop(_nama(), None)
            catat("data", "PIN dihapus")
            selesai_simpan("PIN dihapus.")
