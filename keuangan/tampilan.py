"""Pilihan bagian Beranda yang ditampilkan (disimpan di data, berlaku untuk semua perangkat)."""
import streamlit as st

from keuangan.bantu import catat, selesai_simpan
from keuangan.beranda import SEKSI_BERANDA, disembunyikan
from keuangan.inti import D, hanya_lihat


def halaman_tampilan():
    with st.container(key="kartu_g_tampilan"):
        st.caption("Pilih bagian yang muncul di Beranda. Pilihan disimpan dan berlaku di semua perangkat.")
        sembunyi = disembunyikan()
        with st.form("f_tampilan"):
            tampil = {k: st.checkbox(n, value=k not in sembunyi, key=f"tp_{k}", disabled=hanya_lihat()) for k, n in SEKSI_BERANDA}
            if st.form_submit_button("Simpan", type="primary", disabled=hanya_lihat()):
                D["pengaturan"]["beranda"] = [k for k, v in tampil.items() if not v]
                catat("data", "Ubah bagian Beranda yang ditampilkan")
                selesai_simpan("Tampilan disimpan.")
    from keuangan.pin import panel_pin
    panel_pin()
