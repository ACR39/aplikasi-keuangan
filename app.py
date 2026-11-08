"""Pelacak Keuangan Pribadi (Streamlit).

Mencatat pemasukan, pengeluaran, dan transfer antar dompet, lengkap dengan anggaran bulanan, tagihan berulang,
target tabungan, utang-piutang, dan laporan. Data disimpan sebagai satu file JSON di repositori GitHub
(disarankan repositori privat terpisah). Kalau pengaturan GitHub tidak ada, aplikasi memakai file lokal untuk uji coba.

Kode aplikasi ada di paket keuangan/ (satu modul per bagian).
"""
import streamlit as st

st.set_page_config(page_title="Pelacak Keuangan", page_icon="💰", layout="wide")

from keuangan.rangka import jalankan  # noqa: E402

jalankan()
