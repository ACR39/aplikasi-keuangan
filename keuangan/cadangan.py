"""Cadangan (unduh/muat JSON) dan titik pulih ke versi sebelumnya."""
import json

import streamlit as st

from keuangan.bantu import catat, selesai_simpan
from keuangan.inti import D, data_kosong, fmt_waktu, sekarang
from keuangan.penyimpanan import ambil_versi, daftar_versi, lengkapi


def halaman_cadangan():
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
        for lab, kunci in (("Transaksi", "transaksi"), ("Dompet", "dompet"), ("Kategori", "kategori"), ("Anggaran", "anggaran"),
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
