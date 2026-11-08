"""Catat transaksi (pemasukan, pengeluaran, transfer) dan daftar transaksi dengan filter, ubah, dan hapus."""
import streamlit as st

from keuangan.bantu import (
    f_dompet, f_kat, turunan,
    atur, baris_transaksi, catat, dompet_aktif, dompet_dari, kat_pertama, kategori_jenis, nama_dompet, nama_kat,
    ringkas_teks, selesai_simpan, tambah_transaksi, versi, daftar_bulan, deretan_stat, kartu_stat,
)
from keuangan.inti import (
    D, JENIS, TGL_MAX, TGL_MIN, baru_id, fmt_iso, hanya_lihat, hari_ini, iso_ke_date, nama_bulan, rp, sekarang,
)

HALAMAN_ISI = 30


def _pilihan_dompet(termasuk: str = "") -> list:
    ids = [d["id"] for d in dompet_aktif()]
    if termasuk and termasuk not in ids and dompet_dari(termasuk):
        ids.append(termasuk)
    return ids


def form_transaksi(kunci: str, jenis: str, awal: dict | None = None, tombol: str = "Simpan", bersih: bool = False):
    """Form satu transaksi. Kembalikan dict isian kalau tombol ditekan dan isian sah, kalau tidak None."""
    awal = awal or {}
    dompet = _pilihan_dompet(awal.get("dompet", ""))
    if not dompet or (jenis == "transfer" and len(dompet) < 2):
        st.warning("Tambah dompet dulu di menu Pengaturan > Dompet" + (" (transfer butuh minimal dua dompet)." if jenis == "transfer" else "."))
        return None
    if jenis != "transfer" and not kategori_jenis(jenis):
        st.warning("Belum ada kategori untuk jenis ini. Tambah dulu di Pengaturan > Kategori.")
        return None
    with st.form(kunci, clear_on_submit=bersih):
        c1, c2 = st.columns(2)
        tgl = c1.date_input("Tanggal", value=iso_ke_date(awal.get("tgl")) or hari_ini(), min_value=TGL_MIN, max_value=TGL_MAX,
                            format="DD/MM/YYYY")
        jumlah = c2.number_input("Jumlah (Rp)", min_value=0, step=1000, value=int(awal.get("jumlah", 0) or 0))
        c3, c4 = st.columns(2)
        dari = c3.selectbox("Dari dompet" if jenis in ("keluar", "transfer") else "Ke dompet", dompet,
                            index=dompet.index(awal["dompet"]) if awal.get("dompet") in dompet else 0,
                            format_func=f_dompet())
        kat, ke, biaya = "", "", 0
        if jenis == "transfer":
            sisa = [d for d in dompet]
            idx = sisa.index(awal["ke"]) if awal.get("ke") in sisa else (1 if len(sisa) > 1 else 0)
            ke = c4.selectbox("Ke dompet", sisa, index=idx, format_func=f_dompet())
            biaya = st.number_input("Biaya admin (Rp), opsional", min_value=0, step=500, value=int(awal.get("biaya", 0) or 0))
        else:
            ids = [k["id"] for k in kategori_jenis(jenis)]
            pil = kat_pertama(jenis, awal.get("kategori", ""))
            kat = c4.selectbox("Kategori", ids, index=ids.index(pil) if pil in ids else 0, format_func=f_kat())
        catatan = st.text_input("Catatan, opsional", value=awal.get("catatan", ""), max_chars=120,
                                placeholder="Contoh: makan siang, bensin, gaji bulan ini")
        kirim = st.form_submit_button(tombol, type="primary")
    if not kirim:
        return None
    if jumlah <= 0:
        st.error("Jumlah harus lebih dari nol.")
        return None
    if jenis == "transfer" and dari == ke:
        st.error("Dompet asal dan tujuan tidak boleh sama.")
        return None
    return {"tgl": tgl, "jumlah": int(jumlah), "dompet": dari, "kategori": kat, "ke": ke, "biaya": int(biaya),
            "catatan": catatan}


def halaman_catat():
    if hanya_lihat():
        st.info("Akun ini hanya bisa melihat.")
        return
    with st.container(key="kartu_g_catat"):
        jenis = st.radio("Jenis", list(JENIS), format_func=JENIS.get, horizontal=True, key="tr_jenis",
                         label_visibility="collapsed")
        isi = form_transaksi(f"f_catat_{jenis}_{versi()}", jenis, tombol="Simpan transaksi", bersih=True)
        if isi:
            t = tambah_transaksi(jenis, isi["tgl"], isi["jumlah"], isi["dompet"], isi["kategori"], isi["catatan"],
                                 isi["ke"], isi["biaya"])
            catat("tambah", ringkas_teks(t))
            selesai_simpan(f"Transaksi dicatat: {JENIS[jenis].lower()} {rp(isi['jumlah'])}")
    st.markdown("**Terakhir dicatat**")
    terakhir = sorted(D["transaksi"], key=lambda t: (t["tgl"], t.get("dibuat", "")), reverse=True)[:5]
    if not terakhir:
        st.caption("Belum ada transaksi.")
    for t in terakhir:
        with st.container(key=f"tx_cat_{t['id']}"):
            st.markdown(baris_transaksi(t), unsafe_allow_html=True)


def _filter() -> list:
    with st.container(key="kartu_filter"):
        c1, c2, c3 = st.columns(3)
        bln = c1.selectbox("Bulan", ["semua"] + daftar_bulan(), key="tr_bulan",
                           format_func=lambda b: "Semua bulan" if b == "semua" else nama_bulan(b))
        jenis = c2.multiselect("Jenis", list(JENIS), default=list(JENIS), key="tr_jenisf", format_func=JENIS.get)
        dom = c3.selectbox("Dompet", ["semua"] + [d["id"] for d in D["dompet"]], key="tr_dompet",
                           format_func=f_dompet({"semua": "Semua dompet"}))
        c4, c5 = st.columns([1, 2])
        kat = c4.selectbox("Kategori", ["semua"] + [k["id"] for k in D["kategori"]], key="tr_kat",
                           format_func=f_kat({"semua": "Semua kategori"}))
        q = c5.text_input("Cari catatan atau kategori", key="tr_q", placeholder="Ketik kata kunci").strip().lower()
    hasil = []
    for t in D["transaksi"]:
        if bln != "semua" and t["tgl"][:7] != bln:
            continue
        if t["jenis"] not in jenis:
            continue
        if dom != "semua" and dom not in (t["dompet"], t.get("ke")):
            continue
        if kat != "semua" and t.get("kategori") not in turunan(kat):
            continue
        if q and q not in f'{t.get("catatan", "")} {nama_kat(t.get("kategori"))} {nama_dompet(t["dompet"])}'.lower():
            continue
        hasil.append(t)
    return sorted(hasil, key=lambda t: (t["tgl"], t.get("dibuat", "")), reverse=True)


def _hapus(t: dict):
    D["transaksi"] = [x for x in D["transaksi"] if x["id"] != t["id"]]
    D["sampah"].append({"id": baru_id(), "transaksi": t, "dihapus": hari_ini().isoformat()})
    catat("hapus", ringkas_teks(t))
    selesai_simpan("Transaksi dihapus (ada di Tempat sampah).", hapus_tx=None)


def halaman_transaksi():
    hasil = _filter()
    masuk = sum(t["jumlah"] for t in hasil if t["jenis"] == "masuk")
    keluar = sum(t["jumlah"] for t in hasil if t["jenis"] == "keluar")
    deretan_stat(kartu_stat("Transaksi", str(len(hasil))), kartu_stat("Pemasukan", rp(masuk), kelas="g"),
                 kartu_stat("Pengeluaran", rp(keluar), kelas="m"),
                 kartu_stat("Selisih", rp(masuk - keluar), kelas="g" if masuk >= keluar else "m"))
    if not hasil:
        st.info("Tidak ada transaksi yang cocok." if D["transaksi"] else "Belum ada transaksi. Mulai dari menu Catat transaksi.")
        return
    batas = st.session_state.get("tr_batas", HALAMAN_ISI)
    edit_id, hapus_id = st.session_state.get("edit_tx"), st.session_state.get("hapus_tx")
    for t in hasil[:batas]:
        if edit_id == t["id"]:
            with st.container(key=f"kartu_g_edit_{t['id']}"):
                st.markdown(f"**Ubah {JENIS[t['jenis']].lower()}**")
                isi = form_transaksi(f"f_edit_{t['id']}", t["jenis"], awal=t, tombol="Simpan perubahan")
                if st.button("Batal", key=f"batal_e_{t['id']}"):
                    st.session_state.pop("edit_tx", None)
                    st.rerun()
                if isi:
                    lama = ringkas_teks(t)
                    t.update({"tgl": isi["tgl"].isoformat(), "jumlah": isi["jumlah"], "dompet": isi["dompet"],
                              "catatan": isi["catatan"].strip()})
                    if t["jenis"] == "transfer":
                        t["ke"], t["biaya"] = isi["ke"], isi["biaya"]
                    else:
                        t["kategori"] = isi["kategori"]
                    catat("ubah", f"{lama} → {ringkas_teks(t)}")
                    selesai_simpan("Transaksi diubah.", edit_tx=None)
            continue
        with st.container(key=f"tx_{t['id']}"):
            if hanya_lihat():
                st.markdown(baris_transaksi(t), unsafe_allow_html=True)
            else:
                c = st.columns([1, 0.001, 0.001])
                c[0].markdown(baris_transaksi(t), unsafe_allow_html=True)
                c[1].button("Ubah", key=f"kedit_{t['id']}", on_click=atur, args=("edit_tx", t["id"]))
                c[2].button("Hapus", key=f"khapus_{t['id']}", on_click=atur, args=("hapus_tx", t["id"]))
            if hapus_id == t["id"]:
                st.warning(f"Hapus transaksi ini? ({ringkas_teks(t)}) Bisa dipulihkan dari Tempat sampah selama 30 hari.")
                a, b, _ = st.columns([1, 1, 4])
                if a.button("Ya, hapus", key=f"ya_h_{t['id']}", type="primary"):
                    _hapus(t)
                b.button("Batal", key=f"batal_h_{t['id']}", on_click=atur, args=("hapus_tx", None))
    if len(hasil) > batas:
        st.write("")
        if st.button(f"Tampilkan lebih banyak ({len(hasil) - batas} lagi)", key="tr_lagi"):
            st.session_state.tr_batas = batas + HALAMAN_ISI
            st.rerun()
