"""Toko dan tempat beli: daftar toko (nama, jenis, lokasi) yang dipilih saat mencatat transaksi."""
import streamlit as st

from keuangan.bantu import atur, catat, e, selesai_simpan, transaksi_toko, versi
from keuangan.inti import D, TOKO_IKON, baru_id, fmt_iso, hanya_lihat, rp


def _form(awal: dict | None):
    awal = awal or {}
    with st.form(f"f_toko_{versi()}_{awal.get('id', 'baru')}", clear_on_submit=not awal):
        c1, c2 = st.columns(2)
        nama = c1.text_input("Nama toko", value=awal.get("nama", ""), placeholder="Contoh: Indomaret Merdeka")
        jenis_list = list(TOKO_IKON)
        jenis = c2.selectbox("Jenis", jenis_list, index=jenis_list.index(awal["jenis"]) if awal.get("jenis") in jenis_list else 0)
        lokasi = st.text_input("Lokasi, opsional", value=awal.get("lokasi", ""), max_chars=80, placeholder="Jl. Merdeka, Bandung")
        if st.form_submit_button("Simpan perubahan" if awal else "Tambah toko", type="primary"):
            if not nama.strip():
                st.error("Isi nama toko.")
            elif any(x["nama"].strip().lower() == nama.strip().lower() and x.get("lokasi", "").strip().lower() == lokasi.strip().lower()
                     and x["id"] != awal.get("id") for x in D["toko"]):
                st.error("Toko itu sudah ada.")
            else:
                isi = {"nama": nama.strip(), "jenis": jenis, "lokasi": lokasi.strip()}
                if awal:
                    awal.update(isi)
                else:
                    D["toko"].append({"id": baru_id(), **isi})
                catat("toko", f"{'Ubah' if awal else 'Tambah'} toko {isi['nama']}")
                selesai_simpan("Toko disimpan.", edit_toko=None)


def _lepas_toko(x: dict):
    """Hapus toko. Transaksi tetap ada; nama toko dipindah ke catatan bila kosong, lokasi transaksi dipertahankan."""
    for t in D["transaksi"]:
        if t.get("toko") == x["id"]:
            if not t.get("catatan"):
                t["catatan"] = x["nama"]
            t.pop("toko", None)
    D["toko"] = [y for y in D["toko"] if y["id"] != x["id"]]


def halaman_toko():
    with st.container(key="kartu_filter"):
        c1, c2 = st.columns(2)
        jn = c1.selectbox("Jenis", ["semua"] + list(TOKO_IKON), key="tk_jenis", format_func=lambda j: "Semua jenis" if j == "semua" else j)
        q = c2.text_input("Cari nama atau lokasi", key="tk_q", placeholder="Ketik kata kunci").strip().lower()
    daftar = [x for x in D["toko"] if (jn == "semua" or x.get("jenis") == jn) and q in f'{x["nama"]} {x.get("lokasi", "")}'.lower()]
    st.caption(f"{len(daftar)} toko" + ("" if daftar else ". Belum ada, tambahkan di bawah (atau langsung dari menu Catat transaksi)."))
    for x in sorted(daftar, key=lambda x: x["nama"].lower()):
        pakai = transaksi_toko(x["id"])
        total = sum(t["jumlah"] for t in pakai if t["jenis"] == "keluar")
        ket = x.get("jenis", "Lainnya") + (f' · {e(x["lokasi"])}' if x.get("lokasi") else "")
        ket += f" · dikunjungi {len(pakai)}×" + (f" · total {rp(total)} · terakhir {fmt_iso(pakai[0]['tgl'])}" if pakai else "")
        with st.container(key=f"tx_tk_{x['id']}"):
            kolom = st.columns([1] + ([0.001, 0.001] if not hanya_lihat() else []))
            kolom[0].markdown(f'<div class="rt"><div class="ic kat" style="background:#256b4a22">{TOKO_IKON.get(x.get("jenis"), "📍")}</div>'
                              f'<div class="isi"><div class="jd">{e(x["nama"])}</div><div class="mt">{ket}</div></div></div>',
                              unsafe_allow_html=True)
            if not hanya_lihat():
                kolom[1].button("Ubah", key=f"kedit_tk_{x['id']}", on_click=atur, args=("edit_toko", x["id"]))
                kolom[2].button("Hapus", key=f"khapus_tk_{x['id']}", on_click=atur, args=("hapus_toko", x["id"]))
        if st.session_state.get("hapus_toko") == x["id"]:
            st.warning(f"Hapus toko {x['nama']}? " + (f"Dipakai di {len(pakai)} transaksi; transaksinya tetap ada dan namanya dipindah ke catatan." if pakai else ""))
            a, c, _ = st.columns([1, 1, 4])
            if a.button("Ya, hapus", key=f"ya_tk_{x['id']}", type="primary"):
                _lepas_toko(x)
                catat("toko", f"Hapus toko {x['nama']}")
                selesai_simpan("Toko dihapus.", hapus_toko=None)
            c.button("Batal", key=f"batal_tk_{x['id']}", on_click=atur, args=("hapus_toko", None))
    if hanya_lihat():
        return
    edit = next((x for x in D["toko"] if x["id"] == st.session_state.get("edit_toko")), None)
    with st.container(key="kartu_g_form_tk"):
        st.markdown(f"**{'Ubah toko' if edit else 'Tambah toko'}**")
        _form(edit)
        if edit and st.button("Batal ubah", key="batal_ubah_tk"):
            st.session_state.pop("edit_toko", None)
            st.rerun()
