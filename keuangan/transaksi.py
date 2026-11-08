"""Catat transaksi (pemasukan, pengeluaran, transfer) dan daftar transaksi dengan filter, ubah, dan hapus."""
import streamlit as st

from keuangan.bantu import (
    barang_dalam, barang_dari, f_barang, perbarui_harga_barang, teks_barang,
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
    """Form satu transaksi. Kembalikan dict isian kalau tombol ditekan dan isian sah, kalau tidak None.

    Kategori dan barang dipilih di luar st.form supaya daftar barang langsung menyesuaikan kategori.
    """
    awal = awal or {}
    dompet = _pilihan_dompet(awal.get("dompet", ""))
    if not dompet or (jenis == "transfer" and len(dompet) < 2):
        st.warning("Tambah dompet dulu di menu Pengaturan > Dompet" + (" (transfer butuh minimal dua dompet)." if jenis == "transfer" else "."))
        return None
    if jenis != "transfer" and not kategori_jenis(jenis):
        st.warning("Belum ada kategori untuk jenis ini. Tambah dulu di Pengaturan > Kategori.")
        return None
    kat, brg = "", ""
    if jenis != "transfer":
        ids = [k["id"] for k in kategori_jenis(jenis)]
        pil = kat_pertama(jenis, awal.get("kategori", ""))
        c1, c2 = st.columns(2)
        kat = c1.selectbox("Kategori", ids, index=ids.index(pil) if pil in ids else 0, format_func=f_kat(), key=f"{kunci}_kat")
        opsi = [""] + [b["id"] for b in barang_dalam(kat)]
        if awal.get("barang") and awal["barang"] not in opsi and kat == awal.get("kategori") and barang_dari(awal["barang"]):
            opsi.append(awal["barang"])
        if st.session_state.get(f"{kunci}_brg") not in opsi:
            st.session_state.pop(f"{kunci}_brg", None)
        brg = c2.selectbox("Barang (opsional)", opsi, index=opsi.index(awal["barang"]) if awal.get("barang") in opsi else 0,
                           format_func=f_barang(kat), key=f"{kunci}_brg",
                           help="Pilih barang agar harga dan jumlahnya tercatat. Tambah barang di menu Barang dan produk.")
    b = barang_dari(brg) if brg else None
    with st.form(f"{kunci}_f_{brg}", clear_on_submit=bersih):
        c1, c2 = st.columns(2)
        tgl = c1.date_input("Tanggal", value=iso_ke_date(awal.get("tgl")) or hari_ini(), min_value=TGL_MIN, max_value=TGL_MAX,
                            format="DD/MM/YYYY")
        qty = hs = 0
        if b:
            satuan = f" ({b['satuan']})" if b.get("satuan") else ""
            qty = c2.number_input(f"Banyaknya{satuan}", min_value=0.0, step=1.0, format="%g",
                                  value=float(awal.get("qty") or 1) if awal.get("barang") == brg else 1.0)
            c3, c4 = st.columns(2)
            hs = c3.number_input("Harga satuan (Rp)", min_value=0, step=500,
                                 value=int(awal.get("harga_satuan") or b.get("harga") or 0) if awal.get("barang") == brg else int(b.get("harga") or 0))
            c4.markdown(f"<div style='padding-top:1.9rem;font-weight:700'>Total: {rp(round(qty * hs))}</div>"
                        "<div class='sc-ket'>dihitung saat disimpan</div>", unsafe_allow_html=True)
            jumlah = int(round(qty * hs))
            c5, c6 = st.columns(2)
            dari = c5.selectbox("Dari dompet" if jenis == "keluar" else "Ke dompet", dompet,
                                index=dompet.index(awal["dompet"]) if awal.get("dompet") in dompet else 0, format_func=f_dompet())
        else:
            jumlah = c2.number_input("Jumlah (Rp)", min_value=0, step=1000, value=int(awal.get("jumlah", 0) or 0))
            c3, c4 = st.columns(2)
            dari = c3.selectbox("Dari dompet" if jenis in ("keluar", "transfer") else "Ke dompet", dompet,
                                index=dompet.index(awal["dompet"]) if awal.get("dompet") in dompet else 0, format_func=f_dompet())
        ke, biaya = "", 0
        if jenis == "transfer":
            idx = dompet.index(awal["ke"]) if awal.get("ke") in dompet else (1 if len(dompet) > 1 else 0)
            ke = c4.selectbox("Ke dompet", dompet, index=idx, format_func=f_dompet())
            biaya = st.number_input("Biaya admin (Rp), opsional", min_value=0, step=500, value=int(awal.get("biaya", 0) or 0))
        catatan = st.text_input("Catatan, opsional", value=awal.get("catatan", ""), max_chars=120,
                                placeholder="Contoh: makan siang, bensin, gaji bulan ini")
        kirim = st.form_submit_button(tombol, type="primary")
    if not kirim:
        return None
    if jumlah <= 0:
        st.error("Jumlah harus lebih dari nol." if not b else "Banyaknya dan harga satuan harus lebih dari nol.")
        return None
    if jenis == "transfer" and dari == ke:
        st.error("Dompet asal dan tujuan tidak boleh sama.")
        return None
    return {"tgl": tgl, "jumlah": int(jumlah), "dompet": dari, "kategori": kat, "ke": ke, "biaya": int(biaya),
            "catatan": catatan, "barang": brg, "qty": float(qty) if b else 0, "harga_satuan": int(hs) if b else 0}


def halaman_catat():
    if hanya_lihat():
        st.info("Akun ini hanya bisa melihat.")
        return
    with st.container(key="kartu_g_catat"):
        jenis = st.radio("Jenis", list(JENIS), format_func=JENIS.get, horizontal=True, key="tr_jenis", index=1,
                         label_visibility="collapsed")
        kunci = f"f_catat_{jenis}_{versi()}"
        isi = form_transaksi(kunci, jenis, tombol="Simpan transaksi", bersih=True)
        if isi:
            t = tambah_transaksi(jenis, isi["tgl"], isi["jumlah"], isi["dompet"], isi["kategori"], isi["catatan"],
                                 isi["ke"], isi["biaya"], barang=isi["barang"], qty=isi["qty"], harga_satuan=isi["harga_satuan"])
            catat("tambah", ringkas_teks(t))
            selesai_simpan(f"Transaksi dicatat: {JENIS[jenis].lower()} {rp(isi['jumlah'])}")
        if jenis != "transfer":
            kat = st.session_state.get(f"{kunci}_kat")
            with st.expander("Barang belum ada? Tambah di sini"):
                st.caption(f"Barang akan masuk ke kategori **{nama_kat(kat)}**.")
                with st.form(f"f_cepat_{kunci}", clear_on_submit=True):
                    c1, c2, c3 = st.columns([2, 1, 1])
                    nama = c1.text_input("Nama barang", placeholder="Contoh: Indomie goreng")
                    satuan = c2.text_input("Satuan", placeholder="bungkus")
                    harga = c3.number_input("Harga (Rp)", min_value=0, step=500, value=0)
                    if st.form_submit_button("Tambah barang"):
                        if not nama.strip() or not kat:
                            st.error("Isi nama barang.")
                        elif any(x["nama"].lower() == nama.strip().lower() and x["kategori"] == kat for x in D["barang"]):
                            st.error("Barang itu sudah ada di kategori ini.")
                        else:
                            nb = {"id": baru_id(), "nama": nama.strip(), "kategori": kat, "harga": int(harga), "satuan": satuan.strip()}
                            D["barang"].append(nb)
                            catat("barang", f"Tambah barang {nb['nama']} di {nama_kat(kat)}")
                            nxt = f"f_catat_{jenis}_{versi() + 1}"
                            selesai_simpan("Barang ditambah.", **{f"{nxt}_kat": kat, f"{nxt}_brg": nb["id"]})
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
        q = c5.text_input("Cari catatan, kategori, atau barang", key="tr_q", placeholder="Ketik kata kunci").strip().lower()
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
        if q and q not in f'{t.get("catatan", "")} {nama_kat(t.get("kategori"))} {nama_dompet(t["dompet"])} {teks_barang(t)}'.lower():
            continue
        hasil.append(t)
    return sorted(hasil, key=lambda t: (t["tgl"], t.get("dibuat", "")), reverse=True)


def _hapus(t: dict):
    D["transaksi"] = [x for x in D["transaksi"] if x["id"] != t["id"]]
    D["sampah"].append({"id": baru_id(), "transaksi": t, "dihapus": hari_ini().isoformat()})
    if t.get("barang"):
        perbarui_harga_barang(t["barang"])
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
                    barang_lama = t.get("barang")
                    t.update({"tgl": isi["tgl"].isoformat(), "jumlah": isi["jumlah"], "dompet": isi["dompet"],
                              "catatan": isi["catatan"].strip()})
                    if isi["barang"]:
                        t.update({"barang": isi["barang"], "qty": isi["qty"], "harga_satuan": isi["harga_satuan"]})
                    else:
                        for kk in ("barang", "qty", "harga_satuan"):
                            t.pop(kk, None)
                    if t["jenis"] == "transfer":
                        t["ke"], t["biaya"] = isi["ke"], isi["biaya"]
                    else:
                        t["kategori"] = isi["kategori"]
                    for bid in {barang_lama, t.get("barang")} - {None, ""}:
                        perbarui_harga_barang(bid)
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
