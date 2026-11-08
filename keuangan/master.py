"""Master data: dompet dan kategori."""
import streamlit as st

from keuangan.bantu import f_kat, atur, catat, e, nama_kat, saldo_dompet, selesai_simpan, versi
from keuangan.inti import D, JENIS_DOMPET, baru_id, rp


def _dipakai_dompet(id_) -> int:
    return sum(1 for t in D["transaksi"] if id_ in (t["dompet"], t.get("ke"))) + sum(1 for t in D["tagihan"] if t["dompet"] == id_)


def halaman_dompet():
    with st.container(key="kartu_g_daftar_dompet"):
        st.markdown('<div class="dh"><span class="dt">Dompet</span><span class="dn">%d</span></div>'
                    '<div class="dd">Tempat uang disimpan: tunai, rekening bank, dompet digital, kartu kredit. Saldo dihitung otomatis '
                    'dari saldo awal ditambah semua transaksi.</div>' % len(D["dompet"]), unsafe_allow_html=True)
        for d in D["dompet"]:
            c = st.columns([1, 0.001, 0.001, 0.001])
            c[0].markdown(f'<div class="itm"><div class="isi"><div class="jd">{e(d["nama"])}{" (diarsipkan)" if d.get("arsip") else ""}</div>'
                          f'<div class="mt">{e(d.get("jenis", ""))} · saldo {rp(saldo_dompet(d["id"]))} · saldo awal {rp(d.get("saldo_awal", 0))}</div></div></div>',
                          unsafe_allow_html=True)
            c[1].button("Ubah", key=f"ub_dm_{d['id']}", on_click=atur, args=("edit_dompet", d["id"]))
            c[2].button("Arsipkan" if not d.get("arsip") else "Aktifkan", key=f"ub_ars_{d['id']}",
                        on_click=atur, args=("ars_dompet", d["id"]))
            c[3].button("Hapus", key=f"hp_dm_{d['id']}", on_click=atur, args=("hapus_dompet", d["id"]))
            if st.session_state.get("ars_dompet") == d["id"]:
                d["arsip"] = not d.get("arsip")
                catat("dompet", f"{'Arsipkan' if d['arsip'] else 'Aktifkan'} dompet {d['nama']}")
                st.session_state.pop("ars_dompet")
                selesai_simpan("Dompet diperbarui.")
            if st.session_state.get("hapus_dompet") == d["id"]:
                n = _dipakai_dompet(d["id"])
                if n:
                    st.warning(f"Dompet {d['nama']} dipakai di {n} transaksi atau tagihan, jadi tidak bisa dihapus. "
                               "Arsipkan saja supaya tidak muncul di pilihan.")
                    st.button("Mengerti", key=f"ok_dm_{d['id']}", on_click=atur, args=("hapus_dompet", None))
                else:
                    st.warning(f"Hapus dompet {d['nama']}?")
                    a, b, _ = st.columns([1, 1, 4])
                    if a.button("Ya, hapus", key=f"ya_dm_{d['id']}", type="primary"):
                        D["dompet"] = [x for x in D["dompet"] if x["id"] != d["id"]]
                        catat("dompet", f"Hapus dompet {d['nama']}")
                        selesai_simpan("Dompet dihapus.", hapus_dompet=None)
                    b.button("Batal", key=f"batal_dm_{d['id']}", on_click=atur, args=("hapus_dompet", None))
        edit = next((x for x in D["dompet"] if x["id"] == st.session_state.get("edit_dompet")), None)
        with st.form(f"f_dompet_{versi()}_{edit['id'] if edit else 'baru'}", clear_on_submit=not edit):
            st.markdown(f"**{'Ubah dompet' if edit else 'Tambah dompet'}**")
            c1, c2, c3 = st.columns(3)
            nama = c1.text_input("Nama", value=edit["nama"] if edit else "", placeholder="Contoh: BCA, GoPay")
            jenis = c2.selectbox("Jenis", JENIS_DOMPET, index=JENIS_DOMPET.index(edit["jenis"]) if edit and edit.get("jenis") in JENIS_DOMPET else 1)
            awal = c3.number_input("Saldo awal (Rp)", step=10000, value=int(edit.get("saldo_awal", 0)) if edit else 0,
                                   help="Saldo sebelum transaksi pertama yang dicatat. Boleh negatif untuk kartu kredit.")
            if st.form_submit_button("Simpan perubahan" if edit else "Tambah", type="primary"):
                if not nama.strip():
                    st.error("Isi nama dompet.")
                elif any(x["nama"].strip().lower() == nama.strip().lower() and x is not edit for x in D["dompet"]):
                    st.error("Sudah ada dompet dengan nama itu.")
                else:
                    if edit:
                        edit.update({"nama": nama.strip(), "jenis": jenis, "saldo_awal": int(awal)})
                    else:
                        D["dompet"].append({"id": baru_id(), "nama": nama.strip(), "jenis": jenis, "saldo_awal": int(awal), "arsip": False})
                    catat("dompet", f"{'Ubah' if edit else 'Tambah'} dompet {nama.strip()}")
                    selesai_simpan("Dompet disimpan.", edit_dompet=None)
        if edit and st.button("Batal ubah", key="batal_ubah_dm"):
            st.session_state.pop("edit_dompet", None)
            st.rerun()


def halaman_kategori():
    for jenis, judul in (("keluar", "Kategori pengeluaran"), ("masuk", "Kategori pemasukan")):
        with st.container(key=f"kartu_g_daftar_kat_{jenis}"):
            daftar = [k for k in D["kategori"] if k["jenis"] == jenis]
            st.markdown(f'<div class="dh"><span class="dt">{judul}</span><span class="dn">{len(daftar)}</span></div>', unsafe_allow_html=True)
            for k in daftar:
                n = sum(1 for t in D["transaksi"] if t.get("kategori") == k["id"])
                c = st.columns([1, 0.001, 0.001])
                c[0].markdown(f'<div class="itm"><div class="isi"><div class="jd">{e(k["nama"])}</div>'
                              f'<div class="mt">{n} transaksi</div></div></div>', unsafe_allow_html=True)
                c[1].button("Ubah", key=f"ub_kt_{k['id']}", on_click=atur, args=("edit_kat", k["id"]))
                c[2].button("Hapus", key=f"hp_kt_{k['id']}", on_click=atur, args=("hapus_kat", k["id"]))
                if st.session_state.get("hapus_kat") == k["id"]:
                    pakai = n + sum(1 for a in D["anggaran"] if a["kategori"] == k["id"]) + sum(1 for t in D["tagihan"] if t["kategori"] == k["id"])
                    if pakai:
                        lain = [x["id"] for x in daftar if x["id"] != k["id"]]
                        if not lain:
                            st.warning("Kategori ini dipakai dan tidak ada kategori lain untuk menampung. Tambah kategori lain dulu.")
                        else:
                            st.warning(f"{k['nama']} dipakai di {pakai} data. Gabungkan ke kategori lain sebelum dihapus.")
                            ganti = st.selectbox("Gabungkan ke", lain, format_func=f_kat(), key=f"tb_gab_{k['id']}")
                            a, b, _ = st.columns([1.3, 1, 4])
                            if a.button("Gabung dan hapus", key=f"ya_kt_{k['id']}", type="primary"):
                                for t in D["transaksi"]:
                                    if t.get("kategori") == k["id"]:
                                        t["kategori"] = ganti
                                for t in D["tagihan"]:
                                    if t["kategori"] == k["id"]:
                                        t["kategori"] = ganti
                                sudah = {a_["kategori"] for a_ in D["anggaran"] if a_["kategori"] != k["id"]}
                                D["anggaran"] = [a_ for a_ in D["anggaran"] if a_["kategori"] != k["id"] or ganti not in sudah]
                                for a_ in D["anggaran"]:
                                    if a_["kategori"] == k["id"]:
                                        a_["kategori"] = ganti
                                D["kategori"] = [x for x in D["kategori"] if x["id"] != k["id"]]
                                catat("kategori", f"Gabung kategori {k['nama']} ke {nama_kat(ganti)}")
                                selesai_simpan("Kategori digabung.", hapus_kat=None)
                            b.button("Batal", key=f"batal_kt_{k['id']}", on_click=atur, args=("hapus_kat", None))
                    else:
                        st.warning(f"Hapus kategori {k['nama']}?")
                        a, b, _ = st.columns([1, 1, 4])
                        if a.button("Ya, hapus", key=f"ya_kt_{k['id']}", type="primary"):
                            D["kategori"] = [x for x in D["kategori"] if x["id"] != k["id"]]
                            catat("kategori", f"Hapus kategori {k['nama']}")
                            selesai_simpan("Kategori dihapus.", hapus_kat=None)
                        b.button("Batal", key=f"batal_kt_{k['id']}", on_click=atur, args=("hapus_kat", None))
            edit = next((x for x in daftar if x["id"] == st.session_state.get("edit_kat")), None)
            with st.form(f"f_kat_{jenis}_{versi()}_{edit['id'] if edit else 'baru'}", clear_on_submit=not edit):
                nama = st.text_input("Ubah nama kategori" if edit else "Kategori baru", value=edit["nama"] if edit else "")
                if st.form_submit_button("Simpan perubahan" if edit else "Tambah", type="primary"):
                    if not nama.strip():
                        st.error("Isi nama kategori.")
                    elif any(x["nama"].strip().lower() == nama.strip().lower() and x is not edit for x in daftar):
                        st.error("Sudah ada kategori dengan nama itu.")
                    else:
                        if edit:
                            edit["nama"] = nama.strip()
                        else:
                            D["kategori"].append({"id": baru_id(), "nama": nama.strip(), "jenis": jenis})
                        catat("kategori", f"{'Ubah' if edit else 'Tambah'} kategori {nama.strip()}")
                        selesai_simpan("Kategori disimpan.", edit_kat=None)
            if edit and st.button("Batal ubah", key=f"batal_ubah_kt_{jenis}"):
                st.session_state.pop("edit_kat", None)
                st.rerun()
