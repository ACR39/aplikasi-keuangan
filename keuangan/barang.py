"""Barang dan produk: daftar barang per kategori / sub kategori, dipakai saat mencatat transaksi."""
from datetime import date

import streamlit as st

from keuangan.bantu import (
    ikon_foto, kolom_foto, proses_foto, sisa_hari_teks, pilih_kategori, akar, atur, catat, e, f_kat, ikon_kat, kategori_jenis, nama_kat, selesai_simpan, transaksi_barang, turunan, versi,
)
from keuangan.barcode import baca_barcode, cari_produk
from keuangan.inti import D, TGL_MAX, TGL_MIN, baru_id, fmt_iso, hanya_lihat, iso_ke_date, rp
from keuangan.pwa import gulir_ke_atas_bila_baru


def semua_kategori() -> list:
    return [k["id"] for j in ("keluar", "masuk") for k in kategori_jenis(j)]


class _Berkas:
    """Pembungkus byte supaya bisa dipakai proses_foto seperti file unggahan."""
    def __init__(self, data: bytes):
        self._d = data

    def getvalue(self) -> bytes:
        return self._d


def _blok_barcode(kk: str, awal: dict):
    """Pindai atau ketik barcode, lalu isi form dari data barang sendiri atau Open Food Facts."""
    with st.expander("📷 Isi dari barcode: pindai atau ketik", expanded=False):
        foto = st.camera_input("Arahkan kamera ke barcode", key=f"{kk}_cam")
        unggah = st.file_uploader("Atau unggah foto barcode", type=["jpg", "jpeg", "png", "webp"], key=f"{kk}_bcup")
        ketik = st.text_input("Atau ketik angka barcode", max_chars=32, key=f"{kk}_bcket", placeholder="Contoh: 8992388101011")
        if not st.button("Baca dan isi form", key=f"{kk}_bcgo"):
            return
        kode = ketik.strip()
        sumber = foto or unggah
        if not kode and sumber is not None:
            try:
                kode = baca_barcode(sumber.getvalue())
            except Exception as ex:
                st.error(f"Foto tidak bisa dibaca: {ex}")
                return
            if not kode:
                st.warning("Barcode tidak terbaca. Dekatkan, pastikan terang dan tajam, atau ketik angkanya.")
                return
        if not kode:
            st.warning("Ambil foto barcode atau ketik angkanya dulu.")
            return
        ada = next((x for x in D["barang"] if x.get("barcode", "").strip() == kode and x["id"] != awal.get("id")), None)
        if ada:
            st.info(f"Barcode {kode} sudah ada: **{ada['nama']}**. Tidak perlu ditambah lagi.")
            st.button("Ubah barang itu", key=f"{kk}_bcubah", on_click=lambda: st.session_state.update(edit_brg=ada["id"], edit_baru_brg=False, brg_isi=None))
            return
        try:
            with st.spinner("Mencari data produk…"):
                p = cari_produk(kode)
        except Exception as ex:
            st.warning(f"Pencarian produk gagal ({ex}). Barcode tetap diisi, sisanya isi manual.")
            p = None
        isi = {"barcode": kode, **(p or {})}
        st.session_state["brg_isi"] = isi
        st.session_state["brg_pesan"] = (f"Barcode {kode} ditemukan: {p['nama']}. Periksa lalu simpan." if p
                                         else f"Barcode {kode} terisi, tapi datanya tidak ada di Open Food Facts. Isi nama dan lainnya manual.")
        st.session_state["ver"] = versi() + 1
        st.rerun()


def _form(awal: dict | None, kat_awal: str = ""):
    awal = awal or {}
    pra = {} if awal else (st.session_state.get("brg_isi") or {})
    if not semua_kategori():
        st.warning("Belum ada kategori. Tambah dulu di Pengaturan > Data master > Kategori.")
        return
    pil = awal.get("kategori") or kat_awal
    kk = f"f_brg_{versi()}_{awal.get('id', 'baru')}"
    jenis = next((k["jenis"] for k in D["kategori"] if k["id"] == pil), "keluar")
    jenis = st.radio("Jenis kategori", ["keluar", "masuk"], index=0 if jenis == "keluar" else 1, horizontal=True,
                     format_func=lambda j: "Pengeluaran" if j == "keluar" else "Pemasukan", key=f"{kk}_jenis")
    kat = pilih_kategori(f"{kk}_{jenis}", jenis, pil if any(k["id"] == pil and k["jenis"] == jenis for k in D["kategori"]) else "")
    if st.session_state.get("brg_pesan"):
        st.success(st.session_state["brg_pesan"])
    _blok_barcode(kk, awal)
    with st.form(f"{kk}_{kat}", clear_on_submit=False):
        nama = st.text_input("Nama barang", value=awal.get("nama") or pra.get("nama", ""), placeholder="Contoh: Indomie goreng")
        c3, c4 = st.columns(2)
        satuan = c3.text_input("Satuan, opsional", value=awal.get("satuan", ""), placeholder="bungkus, kg, liter")
        harga = c4.number_input("Harga satuan (Rp), opsional", min_value=0, step=500, value=int(awal.get("harga", 0) or 0),
                                help="Terisi otomatis saat mencatat. Harga ikut diperbarui dari transaksi terbaru barang ini.")
        with st.expander("Rincian lain: barcode, merek, ukuran, kedaluwarsa, foto", expanded=bool(awal.get("barcode") or awal.get("merek") or awal.get("foto") or pra)):
            r1, r2 = st.columns(2)
            barcode = r1.text_input("Barcode / kode produk", value=awal.get("barcode") or pra.get("barcode", ""), max_chars=32,
                                    help="Ketik, tempel, atau scan dengan pembaca barcode USB/Bluetooth. Di halaman Catat, barcode bisa dicari langsung.")
            merek = r2.text_input("Merek", value=awal.get("merek") or pra.get("merek", ""), max_chars=40, placeholder="Indofood")
            r3, r4 = st.columns(2)
            ukuran = r3.text_input("Ukuran / isi kemasan", value=awal.get("ukuran") or pra.get("ukuran", ""), max_chars=30, placeholder="85 g, 1 liter")
            exp = r4.date_input("Kedaluwarsa, opsional", value=iso_ke_date(awal.get("kedaluwarsa")), min_value=TGL_MIN, max_value=TGL_MAX,
                                format="DD/MM/YYYY", help="Tanggal kedaluwarsa stok terbaru. Pengingat muncul di Beranda saat sudah dekat.")
            langganan = st.checkbox("Barang langganan (dibeli rutin)", value=bool(awal.get("langganan")))
            catatan_b = st.text_input("Catatan", value=awal.get("catatan", ""), max_chars=120)
            berkas, hapus_f = kolom_foto("Foto barang", f"{kk}_foto", awal.get("foto", ""))
        if st.form_submit_button("Simpan perubahan" if awal else "Tambah barang", type="primary"):
            if not nama.strip():
                st.error("Isi nama barang.")
            elif barcode.strip() and any(x.get("barcode", "").strip() == barcode.strip() and x["id"] != awal.get("id") for x in D["barang"]):
                st.error("Barcode itu sudah dipakai barang lain.")
            elif any(x["nama"].strip().lower() == nama.strip().lower() and x["kategori"] == kat and x["id"] != awal.get("id")
                     for x in D["barang"]):
                st.error("Barang itu sudah ada di kategori ini.")
            else:
                isi = {"nama": nama.strip(), "kategori": kat, "satuan": satuan.strip(), "harga": int(harga)}
                if berkas is None and not awal.get("foto") and pra.get("foto_bytes") and pra.get("barcode") == barcode.strip():
                    berkas = _Berkas(pra["foto_bytes"])
                foto = proses_foto(berkas, hapus_f, awal.get("foto", ""), "barang")
                for k_, v_ in (("barcode", barcode.strip()), ("merek", merek.strip()), ("ukuran", ukuran.strip()),
                               ("kedaluwarsa", exp.isoformat() if exp else ""), ("langganan", bool(langganan)),
                               ("catatan", catatan_b.strip()), ("foto", foto)):
                    if v_:
                        isi[k_] = v_
                    else:
                        awal.pop(k_, None)
                if awal:
                    awal.update(isi)
                else:
                    D["barang"].append({"id": baru_id(), **isi})
                catat("barang", f"{'Ubah' if awal else 'Tambah'} barang {isi['nama']} di {nama_kat(kat)}")
                selesai_simpan("Barang disimpan.", edit_brg=None, edit_baru_brg=False, brg_isi=None, brg_pesan=None)


def _lepas_barang(b: dict):
    """Hapus barang. Transaksi lama tetap ada; tautan barang dilepas dan namanya dipindah ke catatan bila kosong."""
    for t in D["transaksi"]:
        if t.get("barang") == b["id"]:
            if not t.get("catatan"):
                t["catatan"] = b["nama"]
            for k in ("barang", "qty", "harga_satuan"):
                t.pop(k, None)
    D["barang"] = [x for x in D["barang"] if x["id"] != b["id"]]
    from keuangan.penyimpanan import hapus_foto
    hapus_foto(b.get("foto", ""))


def halaman_barang():
    atas = st.container()  # form tambah/ubah ditaruh di sini (paling atas) supaya tidak perlu menggulir ke bawah
    with st.container(key="kartu_filter"):
        c1, c2 = st.columns([1, 1])
        kat = c1.selectbox("Kategori", ["semua"] + semua_kategori(), key="br_kat", format_func=f_kat({"semua": "Semua kategori"}))
        q = c2.text_input("Cari nama, merek, atau barcode", key="br_q", placeholder="Ketik kata kunci").strip().lower()
    daftar = [b for b in D["barang"] if (kat == "semua" or b["kategori"] in turunan(kat)) and q in f'{b["nama"]} {b.get("merek", "")} {b.get("barcode", "")}'.lower()]
    st.caption(f"{len(daftar)} barang" + ("" if daftar else ". Belum ada, tambahkan di atas (atau langsung dari menu Catat transaksi)."))
    kelompok = {}
    for b in sorted(daftar, key=lambda b: (nama_kat(b["kategori"]).lower(), b["nama"].lower())):
        kelompok.setdefault(b["kategori"], []).append(b)
    for k, isi in kelompok.items():
        st.markdown(f'<div class="dgrup">{e(nama_kat(k))}<span>{len(isi)}</span></div>', unsafe_allow_html=True)
        for b in isi:
            pakai = transaksi_barang(b["id"])
            total = sum(t["jumlah"] for t in pakai)
            ket = (f'{rp(b["harga"])}' + (f' / {e(b["satuan"])}' if b.get("satuan") else "") if b.get("harga") else "harga belum diisi")
            rinci = " · ".join(e(x) for x in (b.get("merek"), b.get("ukuran")) if x)
            if rinci:
                ket = rinci + " · " + ket
            if b.get("barcode"):
                ket += f' · ⫴ {e(b["barcode"])}'
            if b.get("langganan"):
                ket += " · 🔁 langganan"
            if b.get("kedaluwarsa"):
                ket += f' · ⏳ {e(sisa_hari_teks(b["kedaluwarsa"]))}'
            ket += f' · dibeli {len(pakai)}×' + (f' · terakhir {fmt_iso(pakai[0]["tgl"])}' if pakai else "") + (f' · total {rp(total)}' if pakai else "")
            with st.container(key=f"tx_br_{b['id']}"):
                kolom = st.columns([1] + ([0.001, 0.001] if not hanya_lihat() else []))
                kolom[0].markdown(f'<div class="rt">{ikon_foto(b.get("foto"), kat_ikon(b["kategori"]), kat_warna(b["kategori"]))}'
                                  f'<div class="isi"><div class="jd">{e(b["nama"])}</div><div class="mt">{ket}</div></div></div>',
                                  unsafe_allow_html=True)
                if not hanya_lihat():
                    kolom[1].button("Ubah", key=f"kedit_br_{b['id']}", on_click=atur, args=("edit_brg", b["id"]))
                    kolom[2].button("Hapus", key=f"khapus_br_{b['id']}", on_click=atur, args=("hapus_brg", b["id"]))
            if st.session_state.get("hapus_brg") == b["id"]:
                st.warning(f"Hapus barang {b['nama']}? " + (f"Dipakai di {len(pakai)} transaksi; transaksinya tetap ada dan namanya dipindah ke catatan." if pakai else ""))
                a, c, _ = st.columns([1, 1, 4])
                if a.button("Ya, hapus", key=f"ya_br_{b['id']}", type="primary"):
                    _lepas_barang(b)
                    catat("barang", f"Hapus barang {b['nama']}")
                    selesai_simpan("Barang dihapus.", hapus_brg=None)
                c.button("Batal", key=f"batal_br_{b['id']}", on_click=atur, args=("hapus_brg", None))
    if hanya_lihat():
        return
    edit = next((x for x in D["barang"] if x["id"] == st.session_state.get("edit_brg")), None)
    with atas:
        if not edit and not st.session_state.get("edit_baru_brg"):
            gulir_ke_atas_bila_baru(None)
            st.button("➕ Tambah barang baru", key="tambah_brg_btn", type="primary", on_click=atur, args=("edit_baru_brg", True))
            return
        gulir_ke_atas_bila_baru(("brg", edit["id"] if edit else "baru"))
        with st.container(key="kartu_g_form_brg"):
            st.markdown(f"**{'Ubah barang' if edit else 'Tambah barang'}**")
            _form(edit, kat if kat != "semua" else "")
            if st.button("Batal", key="batal_ubah_brg"):
                st.session_state.pop("edit_brg", None)
                st.session_state["edit_baru_brg"] = False
                st.session_state["brg_isi"] = st.session_state["brg_pesan"] = None
                st.rerun()
            st.caption("Memindahkan barang ke kategori lain tidak mengubah kategori pada transaksi yang sudah tercatat.")


def kat_warna(id_) -> str:
    from keuangan.bantu import kat_dari
    k = kat_dari(id_)
    return k.get("warna", "#9aa0a6") if k else "#9aa0a6"


def kat_ikon(id_) -> str:
    from keuangan.bantu import kat_dari
    k = kat_dari(id_)
    return k.get("ikon", "📦") if k else "📦"
