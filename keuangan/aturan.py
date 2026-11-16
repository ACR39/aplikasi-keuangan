"""Aturan kategori otomatis: bila catatan memuat kata kunci tertentu, pakai kategori (dan dompet atau toko) yang ditetapkan."""
import streamlit as st

from keuangan.bantu import baru_id, catat, dompet_aktif, f_dompet, f_kat, f_toko, kat_dari, kategori_jenis, selesai_simpan, toko_dari, versi
from keuangan.inti import D, hanya_lihat
from keuangan.mutasi import _norm


def daftar() -> list:
    return D["pengaturan"].setdefault("aturan", [])


def cocok(teks: str, jenis: str):
    """Aturan terbaik untuk teks ini: kata kunci utuh yang paling panjang, sejenis, dengan kategori yang masih ada. None bila tidak ada."""
    n = f" {_norm(teks)} "
    terbaik = None
    for a in daftar():
        k = _norm(a.get("kata", ""))
        if not k or a.get("jenis") != jenis or f" {k} " not in n or not kat_dari(a.get("kategori")):
            continue
        if terbaik is None or len(k) > len(_norm(terbaik["kata"])):
            terbaik = a
    return terbaik


def halaman_aturan():
    st.caption("Kalau catatan memuat kata kunci, kategori terisi sendiri saat tangkap cepat dan impor mutasi. Dompet dan toko ikut terisi di tangkap cepat bila tidak disebut. "
               "Kata kunci yang lebih panjang menang. Catat transaksi lewat form lengkap tidak memakai aturan ini.")
    if not hanya_lihat():
        with st.container():
            jenis = st.radio("Untuk", ["keluar", "masuk"], horizontal=True, format_func=lambda j: "Pengeluaran" if j == "keluar" else "Pemasukan", key=f"ar_jenis_{versi()}")
            with st.form(f"f_aturan_{versi()}_{jenis}", clear_on_submit=True):
                kata = st.text_input("Kata kunci di catatan", placeholder="Contoh: gojek, indomaret, gaji")
                ids = [k["id"] for k in kategori_jenis(jenis)]
                kat = st.selectbox("Kategori", ids, format_func=f_kat())
                c1, c2 = st.columns(2)
                dom = c1.selectbox("Dompet (opsional)", [""] + [d["id"] for d in dompet_aktif()], format_func=f_dompet({"": "(tidak diatur)"}))
                tk = c2.selectbox("Toko (opsional)", [""] + [x["id"] for x in D["toko"]], format_func=f_toko({"": "(tidak diatur)"}))
                if st.form_submit_button("Tambah aturan", type="primary"):
                    if len(_norm(kata)) < 2:
                        st.error("Kata kunci minimal 2 huruf.")
                    elif any(_norm(a["kata"]) == _norm(kata) and a["jenis"] == jenis for a in daftar()):
                        st.error("Sudah ada aturan dengan kata kunci itu.")
                    else:
                        daftar().append({"id": baru_id(), "kata": kata.strip(), "jenis": jenis, "kategori": kat, "dompet": dom, "toko": tk})
                        catat("data", f"Aturan kategori: {kata.strip()}")
                        selesai_simpan("Aturan ditambah.")
    if not daftar():
        st.info("Belum ada aturan.")
        return
    uji = st.text_input("Uji sebuah catatan", key="ar_uji", placeholder="Ketik catatan untuk melihat aturan mana yang berlaku")
    if uji.strip():
        hasil = [(j, cocok(uji, j)) for j in ("keluar", "masuk")]
        hasil = [(j, a) for j, a in hasil if a]
        for j, a in hasil:
            st.success(f"Cocok dengan “{a['kata']}” ({'keluar' if j == 'keluar' else 'masuk'}).")
        if not hasil:
            st.caption("Tidak ada aturan yang cocok.")
    for a in sorted(daftar(), key=lambda x: x["kata"].lower()):
        with st.container(key=f"kartu_g_ar_{a['id']}"):
            ket = [f"{'Keluar' if a['jenis'] == 'keluar' else 'Masuk'} → {f_kat()(a['kategori']) if kat_dari(a['kategori']) else '(kategori dihapus)'}"]
            if a.get("dompet"):
                ket.append(f_dompet()(a["dompet"]))
            if a.get("toko") and toko_dari(a["toko"]):
                ket.append(toko_dari(a["toko"])["nama"])
            st.markdown(f"**{a['kata']}**  \n<small>{' · '.join(ket)}</small>", unsafe_allow_html=True)
            if not hanya_lihat() and st.button("Hapus", key=f"ar_hapus_{a['id']}"):
                D["pengaturan"]["aturan"] = [x for x in daftar() if x["id"] != a["id"]]
                catat("data", f"Hapus aturan kategori: {a['kata']}")
                selesai_simpan("Aturan dihapus.")
