"""Anggaran bulanan per kategori pengeluaran."""
import streamlit as st

from keuangan.bantu import (
    f_kat,
    atur, batang, catat, deretan_stat, e, ikon_kat, kartu_stat, kategori_jenis, nama_kat, per_kategori, pilih_bulan,
    selesai_simpan, turunan, versi,
)
from keuangan.inti import D, baru_id, hanya_lihat, nama_bulan, rp


def status_anggaran(ym: str) -> list:
    """[(anggaran, terpakai, persen)] diurutkan dari yang paling penuh."""
    pakai = per_kategori(ym, "keluar")

    def dipakai(a):
        return sum(pakai.get(i, 0) for i in turunan(a["kategori"]))
    hasil = [(a, dipakai(a), (dipakai(a) / a["batas"] * 100) if a["batas"] else 0) for a in D["anggaran"]]
    return sorted(hasil, key=lambda x: -x[2])


def halaman_anggaran():
    ym = pilih_bulan("ag_bulan")
    daftar = status_anggaran(ym)
    total_b = sum(a["batas"] for a, _, _ in daftar)
    total_p = sum(p for _, p, _ in daftar)
    deretan_stat(kartu_stat("Total anggaran", rp(total_b)), kartu_stat("Terpakai", rp(total_p), kelas="m" if total_p > total_b else ""),
                 kartu_stat("Sisa", rp(total_b - total_p), kelas="g" if total_b >= total_p else "m"),
                 kartu_stat("Kategori", str(len(daftar))))
    if not daftar:
        st.info("Belum ada anggaran. Tambahkan batas pengeluaran per kategori di bawah.")
    with st.container(key="kartu_g_anggaran"):
        for a, pakai, persen in daftar:
            st.markdown(
                f'<div class="perhatian"><div class="ag"><b>{ikon_kat(a["kategori"])}{e(nama_kat(a["kategori"]))}</b>'
                f'<span>{rp(pakai)} dari {rp(a["batas"])} · <b>{persen:.0f}%</b></span></div>{batang(pakai, a["batas"])}'
                f'<div class="ag"><span>{"Lewat " + rp(pakai - a["batas"]) if pakai > a["batas"] else "Sisa " + rp(a["batas"] - pakai)}</span></div></div>',
                unsafe_allow_html=True)
            if not hanya_lihat():
                c1, c2, _ = st.columns([1, 1, 4])
                c1.button("Ubah", key=f"kedit_ag_{a['id']}", on_click=atur, args=("edit_ag", a["id"]))
                c2.button("Hapus", key=f"khapus_ag_{a['id']}", on_click=atur, args=("hapus_ag", a["id"]))
                if st.session_state.get("hapus_ag") == a["id"]:
                    st.warning(f"Hapus anggaran {nama_kat(a['kategori'])}? Transaksi tidak ikut terhapus.")
                    y, b, _ = st.columns([1, 1, 4])
                    if y.button("Ya, hapus", key=f"ya_ag_{a['id']}", type="primary"):
                        D["anggaran"] = [x for x in D["anggaran"] if x["id"] != a["id"]]
                        catat("anggaran", f"Hapus anggaran {nama_kat(a['kategori'])}")
                        selesai_simpan("Anggaran dihapus.", hapus_ag=None)
                    b.button("Batal", key=f"batal_ag_{a['id']}", on_click=atur, args=("hapus_ag", None))
    if hanya_lihat():
        return
    edit = next((x for x in D["anggaran"] if x["id"] == st.session_state.get("edit_ag")), None)
    pakai_id = {x["kategori"] for x in D["anggaran"]}
    ids = [k["id"] for k in kategori_jenis("keluar") if edit and k["id"] == edit["kategori"] or k["id"] not in pakai_id]
    with st.container(key="kartu_g_form_ag"):
        st.markdown(f"**{'Ubah anggaran' if edit else 'Tambah anggaran'}**")
        if not ids:
            st.caption("Semua kategori pengeluaran sudah punya anggaran.")
            return
        with st.form(f"f_ag_{versi()}_{edit['id'] if edit else 'baru'}", clear_on_submit=True):
            c1, c2 = st.columns(2)
            kat = c1.selectbox("Kategori", ids, index=ids.index(edit["kategori"]) if edit else 0, format_func=f_kat())
            batas = c2.number_input("Batas per bulan (Rp)", min_value=0, step=50000, value=int(edit["batas"]) if edit else 0)
            if st.form_submit_button("Simpan perubahan" if edit else "Tambah", type="primary"):
                if batas <= 0:
                    st.error("Batas harus lebih dari nol.")
                else:
                    if edit:
                        edit.update({"kategori": kat, "batas": int(batas)})
                    else:
                        D["anggaran"].append({"id": baru_id(), "kategori": kat, "batas": int(batas)})
                    catat("anggaran", f"Anggaran {nama_kat(kat)} {rp(batas)} per bulan")
                    selesai_simpan("Anggaran disimpan.", edit_ag=None)
        if edit and st.button("Batal ubah", key="batal_ubah_ag"):
            st.session_state.pop("edit_ag", None)
            st.rerun()
        st.caption(f"Batas berlaku tiap bulan. Angka terpakai dihitung dari pengeluaran pada {nama_bulan(ym)}. Anggaran kategori utama sudah mencakup semua sub kategorinya.")
