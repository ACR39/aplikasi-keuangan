"""Catat transaksi (pemasukan, pengeluaran, transfer) dan daftar transaksi dengan filter, ubah, dan hapus."""
from collections import Counter
from datetime import time as jam_t, timedelta

import streamlit as st

from keuangan.bantu import (
    barang_dalam, barang_dari, f_barang, perbarui_harga_barang, teks_barang,
    f_dompet, f_kat, turunan, harga_normal_barang, tampil_peringatan_harga, peringatan_harga, salin_transaksi, pilih_kategori, kolom_foto, proses_foto, kat_dari, f_toko, toko_dari, teks_toko, kunci_urut, akar,
    atur, baris_transaksi, catat, dompet_aktif, dompet_dari, kat_pertama, kategori_jenis, nama_dompet, nama_kat,
    ringkas_teks, info_diskon, e, selesai_simpan, tambah_transaksi, versi, hapus_foto_bebas, daftar_bulan, deretan_stat, kartu_stat,
    f_platform, nama_platform, anak_dari,
)
from keuangan.anggaran import teks_jatah
from keuangan.peta import proses_gps, terdekat, titik_dari, tombol_gps
from keuangan.ocr import baca_struk, cocokkan_toko, pelajari, ke_tabel, mesin_tersedia
from keuangan.daring import baris_biaya, kebiasaan_toko, olah_online, pastikan_kategori_biaya
from keuangan.struk import struk_serupa, peta_kategori, baca_baris, terapkan_potongan, terapkan_tambahan, baris_pajak, editor_kartu, editor_baris, ringkas_struk, simpan_struk, tabel_kosong, total_cepat
from keuangan.inti import (
    D, JENIS, TOKO_IKON, TGL_MAX, TGL_MIN, baru_id, fmt_iso, hanya_lihat, hari_ini, iso_ke_date, nama_bulan, rp, sekarang,
)

HALAMAN_ISI = 30
SATUAN_UMUM = ["porsi", "pcs", "bungkus", "botol", "buah", "kg", "gram", "liter", "kotak", "lembar", "paket"]


def _pilihan_dompet(termasuk: str = "") -> list:
    ids = [d["id"] for d in dompet_aktif()]
    if termasuk and termasuk not in ids and dompet_dari(termasuk):
        ids.append(termasuk)
    return ids


def _isi_toko_terdekat(sk: str, kunci_toko: str):
    """Bila tombol lokasi ditekan, pilihkan toko tersimpan terdekat (maks 500 m). Panggil SEBELUM selectbox toko."""
    pos = proses_gps(sk)
    if not pos:
        return
    ter = terdekat(pos, D["toko"], 1)
    if ter and ter[0][1] <= 0.5:
        st.session_state[kunci_toko] = ter[0][0]["id"]
        st.toast(f"Toko terdekat: {ter[0][0]['nama']}", icon="📍")
    else:
        st.toast("Tidak ada toko tersimpan dalam 500 m dari sini.", icon="📍")


def _cari_barcode(kunci: str, jenis: str):
    """Callback: cari barang dari barcode lalu pilihkan kategori, sub kategori, dan barangnya."""
    kode = st.session_state.get(f"{kunci}_bc", "").strip()
    st.session_state[f"{kunci}_bc"] = ""
    if not kode:
        return
    b = next((x for x in D["barang"] if x.get("barcode", "").strip() == kode), None)
    k = kat_dari(b["kategori"]) if b else None
    if not b:
        st.session_state[f"{kunci}_bcpesan"] = f"Barcode {kode} belum terdaftar. Tambahkan di Pengaturan > Barang dan produk."
    elif not k or k["jenis"] != jenis:
        st.session_state[f"{kunci}_bcpesan"] = f"{b['nama']} ada di kategori {'pengeluaran' if k and k['jenis'] == 'keluar' else 'pemasukan'}, bukan jenis ini."
    else:
        st.session_state[f"{kunci}_kat"] = akar(b["kategori"])
        st.session_state[f"{kunci}_sub"] = b["kategori"] if akar(b["kategori"]) != b["kategori"] else ""
        st.session_state[f"{kunci}_brg"] = b["id"]
        st.session_state[f"{kunci}_bcpesan"] = f"Terpilih: {b['nama']}"


def _barang_dipilih(kunci: str):
    """Saat barang dipilih, isi kategori dan sub kategori sesuai barang itu."""
    b = barang_dari(st.session_state.get(f"{kunci}_brg"))
    if not b or not kat_dari(b["kategori"]):
        return
    utama = akar(b["kategori"])
    st.session_state[f"{kunci}_kat"] = utama
    st.session_state[f"{kunci}_sub"] = b["kategori"] if b["kategori"] != utama else ""


def barang_favorit(jenis: str, n: int = 6) -> list:
    """Barang yang paling sering dicatat (90 hari terakhir, kalau kosong seluruh riwayat), untuk jenis transaksi ini."""
    batas = (hari_ini() - timedelta(days=90)).isoformat()
    for dari in (batas, ""):
        hit = Counter(t["barang"] for t in D["transaksi"] if t.get("barang") and t["jenis"] == jenis and t["tgl"] >= dari and barang_dari(t["barang"]))
        if hit:
            return [barang_dari(i) for i, _ in hit.most_common(n)]
    return []


def _pilih_favorit(kunci: str, bid: str):
    st.session_state[f"{kunci}_brg"] = bid
    _barang_dipilih(kunci)
    tk = Counter(t.get("toko") for t in D["transaksi"] if t.get("barang") == bid and t.get("toko") and toko_dari(t["toko"]))
    if tk:
        st.session_state[f"{kunci}_toko"] = tk.most_common(1)[0][0]


def panel_favorit(kunci: str, jenis: str):
    fav = barang_favorit(jenis)
    if not fav:
        return
    st.caption("⭐ Sering dicatat, ketuk untuk mengisi barang, harga, kategori, dan toko")
    kolom = st.columns(3)
    for i, b in enumerate(fav):
        kolom[i % 3].button(b["nama"], key=f"{kunci}_fav_{b['id']}", on_click=_pilih_favorit, args=(kunci, b["id"]), width="stretch")


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
    kat, brg, toko = "", "", ""
    if jenis != "transfer":
        if any(x.get("barcode") for x in D["barang"]):
            st.text_input("Cari dengan barcode", key=f"{kunci}_bc", on_change=_cari_barcode, args=(kunci, jenis),
                          placeholder="Scan atau ketik barcode lalu Enter",
                          help="Barang dengan barcode itu langsung terpilih beserta kategorinya.")
            if st.session_state.get(f"{kunci}_bcpesan"):
                st.caption(st.session_state[f"{kunci}_bcpesan"])
        kat = pilih_kategori(kunci, jenis, awal.get("kategori", "") if kat_dari(awal.get("kategori", "")) else "", kosong=not awal.get("kategori"))
        ada_sub = bool(kat) and bool(anak_dari(kat))
        langsung = bool(kat) and any(b["kategori"] == kat for b in D["barang"])  # barang yang menempel di kategori utama tetap bisa dipilih
        sub_ok = bool(kat) and (not ada_sub or bool(st.session_state.get(f"{kunci}_sub")) or langsung)
        c1, c2 = st.columns(2)
        if sub_ok:
            # daftar barang hanya yang berkategori sama dengan pilihan (sub kalau ada, kalau tidak kategori utama);
            # berubah hanya saat kategori/sub diganti, jadi pilihan lama memang perlu direset
            efektif = st.session_state.get(f"{kunci}_sub") or kat
            opsi = [""] + [b["id"] for b in sorted(D["barang"], key=lambda b: b["nama"].lower())
                           if b["kategori"] == efektif and (kat_dari(b["kategori"]) or {}).get("jenis") == jenis]
            if awal.get("barang") and awal["barang"] not in opsi and barang_dari(awal["barang"]) and (barang_dari(awal["barang"]) or {}).get("kategori") == efektif:
                opsi.append(awal["barang"])
            if st.session_state.get(f"{kunci}_brg") not in opsi:
                st.session_state.pop(f"{kunci}_brg", None)
            brg = c1.selectbox("Barang (opsional)", opsi, index=opsi.index(awal["barang"]) if awal.get("barang") in opsi else 0,
                               format_func=f_barang(), key=f"{kunci}_brg", on_change=_barang_dipilih, args=(kunci,),
                               help="Hanya barang di kategori dan sub kategori yang dipilih. Tambah barang di Pengaturan > Barang dan produk.")
        else:
            st.session_state.pop(f"{kunci}_brg", None)
            c1.selectbox("Barang (opsional)", [""], format_func=lambda i: "Isi kategori dan sub kategori dulu" if not kat else "Pilih sub kategori dulu",
                         key=f"{kunci}_brg_kosong", disabled=True)
        ada_titik = any(titik_dari(x) for x in D["toko"])
        if ada_titik:
            _isi_toko_terdekat(f"{kunci}_gps", f"{kunci}_toko")
        tops = [""] + [x["id"] for x in sorted(D["toko"], key=lambda x: (not x.get("favorit"), x["nama"].lower()))]
        if awal.get("toko") and awal["toko"] not in tops and toko_dari(awal["toko"]):
            tops.append(awal["toko"])
        if st.session_state.get(f"{kunci}_toko") not in tops:
            st.session_state.pop(f"{kunci}_toko", None)
        toko = c2.selectbox("Toko / tempat beli (opsional)" if jenis == "keluar" else "Sumber pemasukan (opsional)", tops, index=tops.index(awal["toko"]) if awal.get("toko") in tops else 0,
                            format_func=f_toko(), key=f"{kunci}_toko",
                            help="Tambah toko di Pengaturan > Toko dan tempat beli.")
        if ada_titik and jenis == "keluar":
            with c2:
                tombol_gps(f"{kunci}_gps", "📍 Pilih toko terdekat")
    if not brg and jenis != "transfer" and barang_dari(st.session_state.get(f"{kunci}_brg")):
        brg = st.session_state[f"{kunci}_brg"]  # pengaman: pilihan barang yang masih tersimpan di sesi tidak boleh hilang
    b = barang_dari(brg) if brg else None
    if b:
        hn_riwayat = harga_normal_barang(brg)
        st.caption(f"Harga terakhir {rp(b.get('harga') or 0)}" + (f" · harga normal biasanya {rp(hn_riwayat)}" if hn_riwayat else ""))
    with st.form(f"{kunci}_f_{brg}_{toko}", clear_on_submit=False):
        c1, c2 = st.columns(2)
        tgl = c1.date_input("Tanggal", value=iso_ke_date(awal.get("tgl")) or hari_ini(), min_value=TGL_MIN, max_value=TGL_MAX,
                            format="DD/MM/YYYY")
        qty = hs = hn = 0
        satuan = ""
        if b:
            qty = c2.number_input("Banyaknya", min_value=0.0, step=1.0, format="%g",
                                  value=float(awal.get("qty") or 1) if awal.get("barang") == brg else 1.0)
            c3, c4 = st.columns(2)
            hs = c3.number_input("Harga satuan (Rp)", min_value=0, step=500,
                                 value=int(awal.get("harga_satuan") or b.get("harga") or 0) if awal.get("barang") == brg else int(b.get("harga") or 0))
            hn = c4.number_input("Harga normal (opsional)", min_value=0, step=500,
                                 value=int(awal.get("harga_normal") or 0) if awal.get("barang") == brg else 0,
                                 help="Isi harga sebelum diskon kalau barang ini sedang diskon. Harga satuan = harga yang Anda bayar.")
            st.caption("Total dihitung dari banyaknya × harga satuan saat disimpan. Harga normal hanya untuk mencatat diskon.")
            jumlah = int(round(qty * hs))
            c5, c6 = st.columns(2)
            dari = c5.selectbox("Dari dompet" if jenis == "keluar" else "Ke dompet", dompet,
                                index=dompet.index(awal["dompet"]) if awal.get("dompet") in dompet else 0, format_func=f_dompet())
            opsi_sat = [""] + sorted({*SATUAN_UMUM, *(x.get("satuan", "") for x in D["barang"] if x.get("satuan")), b.get("satuan", "")} - {""})
            satuan = c6.selectbox("Satuan", opsi_sat, index=opsi_sat.index(b.get("satuan", "")), format_func=lambda x: x or "(tanpa satuan)",
                                  help="Berlaku untuk barang ini seterusnya. Tambah satuan lain di Pengaturan > Barang dan produk.")
        elif jenis != "transfer":
            # tanpa barang: tetap bisa isi banyaknya; total = banyaknya x harga satuan
            q0 = float(awal.get("qty") or 1)
            qty = c2.number_input("Banyaknya", min_value=0.0, step=1.0, format="%g", value=q0)
            h0 = int(awal.get("harga_satuan") or round(int(awal.get("jumlah", 0) or 0) / q0))
            hs = st.number_input("Harga satuan (Rp)", min_value=0, step=1000, value=h0)
            jumlah = int(round(qty * hs))
            st.caption(f"Total: {rp(jumlah)}")
            c3, c4 = st.columns(2)
            dari = c3.selectbox("Dari dompet" if jenis in ("keluar", "transfer") else "Ke dompet", dompet,
                                index=dompet.index(awal["dompet"]) if awal.get("dompet") in dompet else 0, format_func=f_dompet())
        ke, biaya = "", 0
        if jenis == "transfer":
            idx = dompet.index(awal["ke"]) if awal.get("ke") in dompet else (1 if len(dompet) > 1 else 0)
            ke = c4.selectbox("Ke dompet", dompet, index=idx, format_func=f_dompet())
            biaya = st.number_input("Biaya admin (Rp), opsional", min_value=0, step=500, value=int(awal.get("biaya", 0) or 0))
        waktu, lokasi, platform = "", "", ""
        if jenis != "transfer":
            c7, c8 = st.columns(2)
            if awal.get("waktu"):
                nilai = jam_t.fromisoformat(awal["waktu"])
            elif awal and not bersih:
                nilai = None  # transaksi lama tanpa jam: biarkan kosong
            else:
                nilai = sekarang().time().replace(second=0, microsecond=0)
            w = c7.time_input("Waktu beli" if jenis == "keluar" else "Waktu terima", value=nilai, step=60, help="Kosongkan bila tidak perlu.")
            waktu = w.strftime("%H:%M") if w else ""
            tk = toko_dari(toko)
            lokasi = c8.text_input("Lokasi", value=awal.get("lokasi") or (tk or {}).get("lokasi", ""), max_chars=80,
                                   placeholder="Contoh: Jl. Merdeka, Bandung") if jenis == "keluar" else ""
            if jenis == "keluar":
                pops = [""] + [p["id"] for p in D["platform"]]
                if awal.get("platform") and awal["platform"] not in pops:
                    pops.append(awal["platform"])
                platform = st.selectbox("Beli online lewat (opsional)", pops, index=pops.index(awal["platform"]) if awal.get("platform") in pops else 0,
                                        format_func=f_platform(),
                                        help="Pilih GoFood, ShopeeFood, dan sebagainya bila beli lewat aplikasi. Biarkan kosong untuk beli langsung. Atur daftarnya di Pengaturan > Platform beli online.")
        struk_berkas, struk_hapus = None, False
        if jenis != "transfer":
            struk_berkas, struk_hapus = kolom_foto("Foto struk, opsional" if jenis == "keluar" else "Foto bukti, opsional", f"{kunci}_struk", awal.get("struk", ""), "struk")
        catatan = st.text_input("Catatan, opsional", value=awal.get("catatan", ""), max_chars=120,
                                placeholder="Contoh: makan siang, bensin, gaji bulan ini")
        kirim = st.form_submit_button(tombol, type="primary")
    if not kirim:
        return None
    if jenis != "transfer" and not kat:
        st.error("Pilih kategori dulu.")
        return None
    if jumlah <= 0:
        st.error("Jumlah harus lebih dari nol." if not b else "Banyaknya dan harga satuan harus lebih dari nol.")
        return None
    if jenis == "transfer" and dari == ke:
        st.error("Dompet asal dan tujuan tidak boleh sama.")
        return None
    if not b and jenis != "transfer":
        extra = {"qty": float(qty) if qty != 1 else 0, "harga_satuan": int(hs) if qty != 1 else 0}
    else:
        extra = {}
    if b and satuan != b.get("satuan", ""):
        b["satuan"] = satuan
    return {"tgl": tgl, "jumlah": int(jumlah), "dompet": dari, "kategori": kat, "ke": ke, "biaya": int(biaya),
            "catatan": catatan, "barang": brg, "qty": float(qty) if b else extra.get("qty", 0), "harga_satuan": int(hs) if b else extra.get("harga_satuan", 0), "harga_normal": int(hn) if b and hn > hs else 0,
            "toko": toko, "platform": platform, "lokasi": lokasi.strip(), "waktu": waktu,
            "struk_berkas": struk_berkas, "struk_hapus": struk_hapus}


def form_struk():
    """Catat satu struk berisi banyak barang sekaligus, bisa diisi otomatis dari foto struk."""
    dompet = _pilihan_dompet()
    if not dompet:
        st.warning("Tambah dompet dulu di menu Pengaturan > Dompet.")
        return
    base = f"f_struk_{versi()}"
    ocr = st.session_state.get("struk_ocr")
    n_up = st.session_state.get("struk_up_n", 0)
    mesin = mesin_tersedia()
    berkas = st.file_uploader("Foto struk, opsional", type=["jpg", "jpeg", "png", "webp"], key=f"f_struk_up_{n_up}",
                              help="Foto diperkecil otomatis. Di HP bisa langsung memotret. Foto yang sama dilampirkan ke struk ini.")
    if berkas is not None and mesin:
        if st.button("📷 Baca isi struk dari foto ini", key=f"{base}_baca"):
            try:
                with st.spinner("Membaca struk…"):
                    hasil = baca_struk(berkas.getvalue(), list(peta_kategori()[0]))
            except RuntimeError as ex:
                st.error(str(ex))
            else:
                if not hasil["item"]:
                    st.warning("Tidak ada barang yang terbaca. Coba foto yang lebih jelas dan lurus, atau isi manual di bawah.")
                else:
                    st.session_state["struk_ocr"] = olah_online(hasil)
                    st.session_state["ver"] = versi() + 1
                    st.rerun()
    elif berkas is None and not mesin:
        st.caption("Isi otomatis dari foto struk belum aktif. Cara mengaktifkannya ada di README bagian Baca struk otomatis.")
    if berkas is not None:
        from keuangan.ai_fitur import panel_layar
        panel_layar(berkas, base)
    if ocr:
        st.info(f"Terisi otomatis dari foto struk (mesin {ocr['mesin']}). Periksa setiap barang, harga, dan banyaknya sebelum menyimpan.")
        if ocr.get("gagal"):
            st.caption("Mesin sebelumnya gagal, otomatis pindah ke berikutnya: " + " | ".join(ocr["gagal"]))
        if ocr.get("toko") and not cocokkan_toko(ocr["toko"]):
            st.caption(f"Toko di struk: {ocr['toko']}. Belum ada di daftar toko; tambah di Pengaturan > Toko dan tempat beli bila perlu.")
        st.button("Kosongkan hasil baca", key=f"{base}_kosong", on_click=lambda: st.session_state.update(struk_ocr=None, ver=versi() + 1))
    tgl_awal = hari_ini()
    jam_awal = sekarang().time().replace(second=0, microsecond=0)
    toko_awal = ""
    if ocr:
        try:
            if ocr.get("tanggal"):
                tgl_awal = min(max(iso_ke_date(ocr["tanggal"]) or tgl_awal, TGL_MIN), TGL_MAX)
            if ocr.get("waktu"):
                jam_awal = jam_t.fromisoformat(ocr["waktu"])
        except ValueError:
            pass
        toko_awal = (cocokkan_toko(ocr.get("toko")) or {}).get("id", "")
    c1, c2 = st.columns(2)
    tgl = c1.date_input("Tanggal", value=tgl_awal, min_value=TGL_MIN, max_value=TGL_MAX, format="DD/MM/YYYY", key=f"{base}_tgl")
    w = c2.time_input("Waktu beli", value=jam_awal, step=60, key=f"{base}_w")
    c3, c4 = st.columns(2)
    dari = c3.selectbox("Dari dompet", dompet, format_func=f_dompet(), key=f"{base}_dompet")
    ada_titik = any(titik_dari(x) for x in D["toko"])
    if ada_titik:
        _isi_toko_terdekat(f"{base}_gps", f"{base}_toko")
    tops = [""] + [x["id"] for x in sorted(D["toko"], key=lambda x: (not x.get("favorit"), x["nama"].lower()))]
    if st.session_state.get(f"{base}_toko") not in tops:
        st.session_state.pop(f"{base}_toko", None)
    toko = c4.selectbox("Toko / tempat beli", tops, index=tops.index(toko_awal) if toko_awal in tops else 0,
                        format_func=f_toko(), key=f"{base}_toko")
    if ada_titik:
        with c4:
            tombol_gps(f"{base}_gps", "📍 Pilih toko terdekat")
    lokasi = st.text_input("Lokasi", value=(toko_dari(toko) or {}).get("lokasi", ""), max_chars=80, key=f"{base}_lok_{toko}",
                           placeholder="Contoh: Jl. Merdeka, Bandung")
    pops = [""] + [p["id"] for p in D["platform"]]
    if ocr and ocr.get("platform_id") and f"{base}_plat" not in st.session_state:
        st.session_state[f"{base}_plat"] = ocr["platform_id"]
    if st.session_state.get(f"{base}_plat") not in pops:
        st.session_state.pop(f"{base}_plat", None)
    platform = st.selectbox("Beli online lewat (opsional)", pops, format_func=f_platform(), key=f"{base}_plat",
                            help="Pilih GoFood, ShopeeFood, dan sebagainya bila beli lewat aplikasi. Berlaku untuk seluruh struk ini.")
    alasan = (ocr or {}).get("platform_alasan")
    if platform:
        st.caption(f"🛵 **Online** lewat {nama_platform(platform)}" + (f" · terisi otomatis: {alasan}. Salah? Ubah di atas, pilihanmu diingat untuk toko ini." if alasan and (ocr or {}).get("platform_id") == platform else ""))
    else:
        st.caption("🏪 **Beli langsung (offline)**" + (f" · {alasan}" if alasan else ""))
    saran = kebiasaan_toko(toko)
    if saran and saran[0] and saran[0] != platform and not (ocr or {}).get("platform_id"):
        st.button(f"Toko ini biasanya lewat {nama_platform(saran[0])} ({saran[1]}x), pakai", key=f"{base}_saranplat", on_click=atur, args=(f"{base}_plat", saran[0]))
    st.markdown("**Barang di struk**")
    st.caption("Pilih Barang dari daftar, atau kosongkan lalu pilih Kategori. Harga kosong memakai harga terakhir barang.")
    df = editor_kartu(f"{base}_tbl", ke_tabel(ocr) if ocr else None)
    baris_ok, _ = baca_baris(df)
    jumlah_struk = total_cepat(df)
    if ocr and ocr.get("potongan") and f"{base}_pot" not in st.session_state:
        st.session_state[f"{base}_pot"] = int(ocr["potongan"])
    potongan = st.number_input("Potongan seluruh struk (Rp), opsional", min_value=0, step=500, key=f"{base}_pot",
                               help="Voucher atau diskon total di struk. Dibagi ke tiap barang sebanding harganya, jadi tercatat sebagai diskon.")
    if potongan:
        st.caption(f"Jumlah barang {rp(jumlah_struk)}, dikurangi potongan {rp(min(potongan, jumlah_struk))}.")
        jumlah_struk = max(0, jumlah_struk - int(potongan))
    dasar_ppn = jumlah_struk
    ppn = st.number_input("PPN / pajak / biaya lain (Rp), opsional", min_value=0, step=500, key=f"{base}_ppn",
                          help="Isi HANYA kalau PPN ditambahkan di luar harga barang (total di struk lebih besar dari jumlah barang). Di minimarket seperti Alfamart dan Indomaret, harga biasanya sudah termasuk PPN, dan baris 'PPN' di struk hanya rincian.")
    sudah_termasuk = bool(ocr and ocr.get("total") and abs(ocr["total"] - dasar_ppn) <= 1 and dasar_ppn > 0)
    if sudah_termasuk and not ppn:
        st.success(f"Total di struk ({rp(ocr['total'])}) sama dengan jumlah barang, jadi PPN sudah termasuk di harga. Tidak perlu diisi. "
                   f"(PPN yang terkandung kira-kira {rp(round(dasar_ppn * 11 / 111))}.)")
    elif ppn and ocr and ocr.get("total") and dasar_ppn + int(ppn) != ocr["total"] and abs(ocr["total"] - dasar_ppn) <= 1:
        st.warning("Total di struk sudah sama dengan jumlah barang sebelum PPN diisi. Kemungkinan PPN sudah termasuk di harga: kosongkan kolom PPN.")
    cb1, cb2 = st.columns(2)
    cb1.button("Tambah 11% (harga belum termasuk PPN)", key=f"{base}_ppn11", on_click=atur, args=(f"{base}_ppn", round(dasar_ppn * 0.11)), disabled=dasar_ppn <= 0, width="stretch")
    if ocr and ocr.get("total") and ocr["total"] > dasar_ppn > 0:
        cb2.button(f"Pakai selisih struk ({rp(ocr['total'] - dasar_ppn)})", key=f"{base}_ppnsel", on_click=atur,
                   args=(f"{base}_ppn", int(ocr["total"] - dasar_ppn)), width="stretch")
    cara_ppn = "bagi"
    if ppn:
        cara_ppn = st.radio("Catat PPN sebagai", ["bagi", "baris"], horizontal=True, key=f"{base}_ppncara",
                            format_func=lambda c: "Dibagi ke harga tiap barang" if c == "bagi" else "Satu baris PPN sendiri",
                            help="Dibagi: harga tiap barang jadi sudah termasuk PPN (harga tercatat = harga yang benar-benar dibayar). "
                                 "Satu baris: harga barang tetap sesuai struk, PPN jadi baris tersendiri.")
        st.caption(f"Ditambah PPN {rp(ppn)}.")
        jumlah_struk += int(ppn)
    baris_biaya_online = []
    if platform:
        st.markdown("**Biaya pesanan online**")
        st.caption("Dicatat sebagai baris sendiri (kategori Biaya pesan online) supaya harga barang tetap bersih. Kosongkan yang tidak ada.")
        if ocr and ocr.get("biaya"):
            for kk in ("ong", "lay", "kms", "rst", "asu", "lain", "dso"):
                if ocr["biaya"].get(kk) and f"{base}_by_{kk}" not in st.session_state:
                    st.session_state[f"{base}_by_{kk}"] = int(ocr["biaya"][kk])
        b1, b2 = st.columns(2)
        ong = b1.number_input("Ongkir (Rp)", min_value=0, step=500, key=f"{base}_by_ong")
        lay = b2.number_input("Biaya layanan / admin (Rp)", min_value=0, step=500, key=f"{base}_by_lay")
        b3, b4 = st.columns(2)
        kms = b3.number_input("Biaya pengemasan (Rp)", min_value=0, step=500, key=f"{base}_by_kms")
        rst = b4.number_input("Biaya tambahan resto (Rp)", min_value=0, step=500, key=f"{base}_by_rst")
        b5, b6 = st.columns(2)
        asu = b5.number_input("Asuransi (Rp)", min_value=0, step=500, key=f"{base}_by_asu")
        lain_b = b6.number_input("Biaya lain (Rp)", min_value=0, step=500, key=f"{base}_by_lain")
        dso = st.number_input("Diskon ongkir (Rp)", min_value=0, step=500, key=f"{base}_by_dso",
                              help="Isi hanya bila ongkir yang kamu isi di atas belum dipotong. Kalau di aplikasi ongkirnya sudah dicoret (misalnya Rp10.000 jadi Rp9.000), isi ongkir dengan angka akhir (Rp9.000) dan kosongkan ini. Mengurangi ongkir saja, tidak mengurangi harga barang.")
        baris_biaya_online = baris_biaya(ong, lay, asu, lain_b, dso, kms, rst)
        total_biaya = sum(x["harga"] for x in baris_biaya_online)
        if dso > ong:
            st.caption("Diskon ongkir lebih besar dari ongkir; yang dipakai hanya sebesar ongkir.")
        if total_biaya:
            st.caption(f"Biaya pesanan {rp(total_biaya)}.")
        jumlah_struk += total_biaya
    st.markdown(f"**Total struk: {rp(jumlah_struk)}** · {len(baris_ok)} barang")
    if ocr and ocr.get("dipindah"):
        st.caption("Dipindah dari daftar barang: " + "; ".join(ocr["dipindah"]) + ".")
    if ocr and ocr.get("total") and baris_ok and jumlah_struk > ocr["total"]:
        lebih = jumlah_struk - int(ocr["total"])
        st.button(f"Total lebih besar {rp(lebih)} dari struk: pakai sebagai potongan (voucher/diskon)", key=f"{base}_selpot",
                  on_click=atur, args=(f"{base}_pot", int(potongan) + lebih))
    if ocr and ocr.get("total"):
        if ocr["total"] == jumlah_struk:
            st.caption(f"✅ Cocok dengan total di struk ({rp(ocr['total'])}).")
        else:
            st.warning(f"Total di struk {rp(ocr['total'])}, jumlah barang di atas {rp(jumlah_struk)}. "
                       "Mungkin ada barang yang belum terbaca, atau harga dan banyaknya salah baca. Diskon atau pajak juga bisa membuat selisih.")
    import hashlib
    foto_hash = hashlib.sha1(berkas.getvalue()).hexdigest() if berkas is not None else ""
    dobel = struk_serupa(tgl.isoformat(), toko, jumlah_struk, foto_hash) if baris_ok else None
    lanjut = True
    if dobel:
        sama_foto = foto_hash and dobel[0].get("foto_hash") == foto_hash
        st.warning(f"⚠️ Mungkin struk dobel: sudah ada struk {'dengan foto yang sama' if sama_foto else 'serupa'} "
                   f"({teks_toko(dobel[0]) or 'tanpa toko'}, {fmt_iso(dobel[0]['tgl'])}, "
                   f"{rp(sum(int(x['jumlah']) for x in dobel))}, {len(dobel)} barang).")
        lanjut = st.checkbox("Ini struk yang berbeda, tetap simpan", key=f"{base}_lanjut")
    if st.button("Simpan struk", type="primary", key=f"{base}_simpan"):
        baris, salah = baca_baris(df)
        if salah:
            st.error("\n\n".join(salah))
        elif not baris:
            st.error("Isi minimal satu barang.")
        elif not lanjut:
            st.error("Struk ini kemungkinan dobel. Centang pilihan di atas bila memang struk yang berbeda.")
        else:
            struk = proses_foto(berkas, False, "", "struk")
            baris = terapkan_potongan(baris, potongan)
            if ppn:
                baris = terapkan_tambahan(baris, ppn) if cara_ppn == "bagi" else baris + [baris_pajak(baris, ppn)]
            n_belajar = pelajari(ocr, baris, toko) if ocr else 0
            if baris_biaya_online:
                pastikan_kategori_biaya()
                baris = baris + baris_biaya_online
            simpan_struk(baris, tgl, w.strftime("%H:%M"), dari, toko, lokasi.strip(), struk, foto_hash=foto_hash, platform=platform)
            catat("tambah", ringkas_struk(baris, toko))
            selesai_simpan(f"Struk dicatat: {len(baris)} barang" + (f" · {n_belajar} koreksi dipelajari" if n_belajar else "") + (f" · {teks_jatah()}" if tgl == hari_ini() and teks_jatah() else ""), struk_ocr=None, struk_up_n=n_up + 1)


TPL_KUNCI = ("jenis", "dompet", "kategori", "jumlah", "catatan", "ke", "biaya", "barang", "qty", "harga_satuan", "harga_normal", "toko", "platform", "lokasi")


def _asal_salin():
    """Sumber isian salin: transaksi, atau templat bila kuncinya diawali 'tpl:'."""
    k = st.session_state.get("salin_tx") or ""
    if k.startswith("tpl:"):
        return next((x for x in D["templat"] if x["id"] == k[4:]), None), True
    return next((x for x in D["transaksi"] if x["id"] == k), None), False


def _catat_dari_templat(tp: dict):
    """Catat langsung dari templat: tanggal hari ini, jam sekarang."""
    if not dompet_dari(tp["dompet"]):
        st.error("Dompet pada templat ini sudah tidak ada. Hapus templatnya lalu buat lagi.")
        return
    extra = {k: tp[k] for k in ("barang", "qty", "harga_satuan", "harga_normal", "toko", "platform", "lokasi") if tp.get(k)}
    t = tambah_transaksi(tp["jenis"], hari_ini(), tp["jumlah"], tp["dompet"], tp.get("kategori", ""), tp.get("catatan", ""),
                         tp.get("ke", ""), tp.get("biaya", 0), waktu=sekarang().strftime("%H:%M"), **extra)
    catat("tambah", f"{ringkas_teks(t)} (dari templat {tp['nama']})")
    selesai_simpan(f"Dicatat dari templat {tp['nama']}: {rp(tp['jumlah'])}")


def _panel_templat(jenis: str):
    daftar = [x for x in D["templat"] if x["jenis"] == jenis]
    if not daftar:
        return
    with st.expander(f"⚡ Templat ({len(daftar)})"):
        st.caption("Catat sekarang memakai tanggal hari ini. Isi form bila ada yang ingin diubah dulu.")
        for tp in daftar:
            with st.container(border=True, key=f"kartu_g_tpl_{tp['id']}"):
                st.markdown(f"**{e(tp['nama'])}** · {rp(tp['jumlah'])}")
                st.caption(ringkas_teks(tp))
                a, b, c = st.columns(3)
                a.button("Catat sekarang", key=f"tpl_cat_{tp['id']}", type="primary", on_click=_catat_dari_templat, args=(tp,))
                b.button("Isi form", key=f"tpl_isi_{tp['id']}", on_click=atur, args=("salin_tx", "tpl:" + tp["id"]))
                if c.button("Hapus", key=f"tpl_del_{tp['id']}"):
                    D["templat"] = [x for x in D["templat"] if x["id"] != tp["id"]]
                    catat("tambah", f"Hapus templat {tp['nama']}")
                    selesai_simpan("Templat dihapus.")


def _simpan_templat(asal: dict):
    """Form kecil: simpan transaksi yang sedang disalin sebagai templat."""
    with st.expander("⭐ Simpan sebagai templat"):
        awal = (asal.get("catatan") or nama_kat(asal.get("kategori")) or "Templat")[:40]
        nama = st.text_input("Nama templat", value=awal, max_chars=40, key=f"tpl_nama_{asal['id']}")
        if st.button("Simpan templat", key=f"tpl_simpan_{asal['id']}"):
            if not nama.strip():
                st.error("Isi nama templat.")
            elif any(x["nama"].lower() == nama.strip().lower() and x["jenis"] == asal["jenis"] for x in D["templat"]):
                st.error("Sudah ada templat dengan nama itu.")
            else:
                D["templat"].append({"id": baru_id(), "nama": nama.strip(), **{k: asal[k] for k in TPL_KUNCI if asal.get(k)}})
                catat("tambah", f"Buat templat {nama.strip()}")
                selesai_simpan(f"Templat {nama.strip()} disimpan.")


def halaman_catat():
    if hanya_lihat():
        st.info("Akun ini hanya bisa melihat.")
        return
    with st.container(key="kartu_g_catat"):
        st.session_state.setdefault("tr_jenis", "keluar")
        jenis = st.radio("Jenis", list(JENIS), format_func=JENIS.get, horizontal=True, key="tr_jenis",
                         label_visibility="collapsed")
        kunci = f"f_catat_{jenis}_{versi()}"
        struk_mode = False
        if jenis == "keluar":
            cara = st.radio("Cara catat", ["satu", "struk", "patungan"], horizontal=True, key="tr_mode",
                            format_func=lambda m: {"satu": "Satu barang", "struk": "Satu struk, banyak barang", "patungan": "Patungan"}[m])
            struk_mode = cara == "struk"
        if jenis == "keluar" and st.session_state.get("tr_mode") == "patungan":
            from keuangan.patungan import form_patungan
            form_patungan()
            isi = None
        elif struk_mode:
            form_struk()
            isi = None
        else:
            awal_salin = {}
            _panel_templat(jenis)
            asal, dari_templat = _asal_salin()
            if asal and asal["jenis"] == jenis:
                awal_salin = {k: v for k, v in asal.items() if k not in ("id", "tgl", "waktu", "struk", "grup", "dibuat", "oleh", "nama")}
                st.info(f"{'Memakai templat ' + asal['nama'] if dari_templat else 'Menyalin transaksi'}: {ringkas_teks(asal)}. "
                        "Tanggal dan jam diganti ke sekarang; ubah bagian yang berbeda lalu simpan.")
                st.button("Batal menyalin", key="batal_salin", on_click=atur, args=("salin_tx", None))
                if not dari_templat:
                    _simpan_templat(asal)
            if not awal_salin:
                from keuangan.tangkap import panel_tangkap
                panel_tangkap()
                panel_favorit(kunci, jenis)
            isi = form_transaksi(kunci, jenis, awal=awal_salin, tombol="Simpan transaksi", bersih=True)
        if isi:
            struk = proses_foto(isi["struk_berkas"], False, "", "struk")
            ph = peringatan_harga(isi["barang"], isi["harga_satuan"]) if jenis == "keluar" and isi["barang"] else None
            t = tambah_transaksi(jenis, isi["tgl"], isi["jumlah"], isi["dompet"], isi["kategori"], isi["catatan"],
                                 isi["ke"], isi["biaya"], barang=isi["barang"], qty=isi["qty"], harga_satuan=isi["harga_satuan"],
                                 harga_normal=isi["harga_normal"], toko=isi["toko"], platform=isi["platform"], lokasi=isi["lokasi"], waktu=isi["waktu"], struk=struk)
            catat("tambah", ringkas_teks(t))
            selesai_simpan(f"Transaksi dicatat: {JENIS[jenis].lower()} {rp(isi['jumlah'])}"
                           + (f" ({teks_barang(t)})" if teks_barang(t) else "")
                           + (f" · {'⚠️' if ph[0] == 'mahal' else '✅'} {ph[1]}" if ph else "")
                           + (f" · {teks_jatah()}" if jenis == "keluar" and isi["tgl"] == hari_ini() and teks_jatah() else ""), salin_tx=None)
    st.markdown("**Terakhir dicatat**")
    terakhir = sorted(D["transaksi"], key=kunci_urut, reverse=True)[:5]
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
        c4, c6 = st.columns(2)
        kat = c4.selectbox("Kategori", ["semua"] + [k["id"] for k in D["kategori"]], key="tr_kat",
                           format_func=f_kat({"semua": "Semua kategori"}))
        tk = c6.selectbox("Toko", ["semua"] + [x["id"] for x in D["toko"]], key="tr_toko",
                          format_func=f_toko({"semua": "Semua toko"}))
        plat = st.selectbox("Beli online", ["semua", "online", "offline"] + [p["id"] for p in D["platform"]], key="tr_plat",
                            format_func=f_platform({"semua": "Semua (online dan offline)", "online": "Semua yang online", "offline": "Hanya offline"}))
        q = st.text_input("Cari catatan, kategori, barang, toko, atau lokasi", key="tr_q", placeholder="Ketik kata kunci").strip().lower()
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
        if tk != "semua" and t.get("toko") != tk:
            continue
        if plat == "online" and not t.get("platform"):
            continue
        if plat == "offline" and (t.get("platform") or t["jenis"] != "keluar"):
            continue
        if plat not in ("semua", "online", "offline") and t.get("platform") != plat:
            continue
        if q and q not in f'{t.get("catatan", "")} {nama_kat(t.get("kategori"))} {nama_dompet(t["dompet"])} {teks_barang(t)} {teks_toko(t)} {nama_platform(t.get("platform"))}'.lower():
            continue
        hasil.append(t)
    return sorted(hasil, key=kunci_urut, reverse=True)


def _hapus(t: dict):
    D["transaksi"] = [x for x in D["transaksi"] if x["id"] != t["id"]]
    D["sampah"].append({"id": baru_id(), "transaksi": t, "dihapus": hari_ini().isoformat()})
    if t.get("barang"):
        perbarui_harga_barang(t["barang"])
    catat("hapus", ringkas_teks(t))
    selesai_simpan("Transaksi dihapus (ada di Tempat sampah).", hapus_tx=None)


def _tampil_tx(t: dict, edit_id, hapus_id, foto: bool = True):
    """Satu transaksi: kartu, tombol Ubah/Salin/Hapus, dan form ubah bila sedang diubah."""
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
                    if isi["harga_normal"]:
                        t["harga_normal"] = isi["harga_normal"]
                    else:
                        t.pop("harga_normal", None)
                else:
                    for kk in ("barang", "qty", "harga_satuan", "harga_normal"):
                        t.pop(kk, None)
                    if isi["qty"]:
                        t["qty"], t["harga_satuan"] = isi["qty"], isi["harga_satuan"]
                if t["jenis"] == "transfer":
                    t["ke"], t["biaya"] = isi["ke"], isi["biaya"]
                else:
                    t["kategori"] = isi["kategori"]
                    isi["struk"] = proses_foto(isi["struk_berkas"], isi["struk_hapus"], t.get("struk", ""), "struk")
                    for kk in ("toko", "platform", "lokasi", "waktu", "struk"):
                        if isi[kk]:
                            t[kk] = isi[kk]
                        else:
                            t.pop(kk, None)
                for bid in {barang_lama, t.get("barang")} - {None, ""}:
                    perbarui_harga_barang(bid)
                catat("ubah", f"{lama} → {ringkas_teks(t)}")
                selesai_simpan("Transaksi diubah.", edit_tx=None)
        return
    with st.container(key=f"tx_{t['id']}"):
        st.markdown(baris_transaksi(t), unsafe_allow_html=True)
        if not hanya_lihat():
            with st.container(key=f"aksi_{t['id']}"):
                c = st.columns(3)
                c[0].button("Ubah", key=f"kedit_{t['id']}", on_click=atur, args=("edit_tx", t["id"]))
                c[1].button("Salin", key=f"ksalin_{t['id']}", on_click=salin_transaksi, args=(t["id"],))
                c[2].button("Hapus", key=f"khapus_{t['id']}", on_click=atur, args=("hapus_tx", t["id"]))
        if t.get("struk") and foto and st.session_state.get("tr_struk"):
            from keuangan.penyimpanan import ambil_foto
            img = ambil_foto(t["struk"])
            if img:
                st.image(img, width=260, caption="Struk")
        if hapus_id == t["id"]:
            st.warning(f"Hapus transaksi ini? ({ringkas_teks(t)}) Bisa dipulihkan dari Tempat sampah selama 30 hari.")
            a, b, _ = st.columns([1, 1, 4])
            if a.button("Ya, hapus", key=f"ya_h_{t['id']}", type="primary"):
                _hapus(t)
            b.button("Batal", key=f"batal_h_{t['id']}", on_click=atur, args=("hapus_tx", None))


def _hapus_struk(g: str):
    """Pindahkan semua barang satu struk ke Tempat sampah sekaligus."""
    semua = [x for x in D["transaksi"] if x.get("grup") == g]
    if not semua:
        return
    D["transaksi"] = [x for x in D["transaksi"] if x.get("grup") != g]
    for x in semua:
        D["sampah"].append({"id": baru_id(), "transaksi": x, "dihapus": hari_ini().isoformat()})
    for b in {x["barang"] for x in semua if x.get("barang")}:
        perbarui_harga_barang(b)
    catat("hapus", f"Struk {len(semua)} barang {rp(sum(int(x['jumlah']) for x in semua))}"
                   + (f" di {teks_toko(semua[0])}" if teks_toko(semua[0]) else ""))
    selesai_simpan(f"Struk dihapus: {len(semua)} barang (ada di Tempat sampah).", hapus_grup=None)


def _simpan_foto_struk(g: str, berkas, hapus: bool):
    """Pasang/ganti/hapus foto struk untuk SEMUA barang di satu struk."""
    import hashlib
    semua = [x for x in D["transaksi"] if x.get("grup") == g]
    if not semua:
        return
    lama = {x["struk"] for x in semua if x.get("struk")}
    if berkas is not None:
        data = berkas.getvalue()
        baru = proses_foto(berkas, False, "", "struk")
        if not baru:
            return
        for i in lama:
            hapus_foto_bebas(i)
        h = hashlib.sha1(data).hexdigest()
        for x in semua:
            x["struk"], x["foto_hash"] = baru, h
        pesan = "Foto struk dipasang untuk semua barang."
    elif hapus:
        for i in lama:
            hapus_foto_bebas(i)
        for x in semua:
            x.pop("struk", None)
            x.pop("foto_hash", None)
        pesan = "Foto struk dihapus."
    else:
        return
    catat("ubah", f"{pesan[:-1]} ({len(semua)} barang)")
    selesai_simpan(pesan)


def _kartu_struk(isi: list, edit_id, hapus_id):
    """Satu kartu untuk satu struk (beberapa barang); barangnya bisa dibuka."""
    isi = sorted(isi, key=lambda x: x.get("dibuat", ""))
    t0 = isi[0]
    total = sum(x["jumlah"] for x in isi)
    hemat = 0
    for x in isi:
        d = info_diskon(x)
        if d:
            hemat += d[1] * (x.get("qty") or 1)
    nama = teks_toko(t0) or "Struk belanja"
    waktu = f" · {t0['waktu']}" if t0.get("waktu") else ""
    with st.container(key=f"tx_g_{t0['grup']}"):
        st.markdown(
            f'<div class="rt"><div class="ic keluar">🧾</div><div class="isi"><div class="jd">{e(nama)}</div>'
            f'<div class="mt">{fmt_iso(t0["tgl"])}{waktu} · {e(nama_dompet(t0["dompet"]))}{" · 🛵 " + e(nama_platform(t0.get("platform"))) if t0.get("platform") else ""}<br>{len(isi)} barang'
            f'{" · 🏷️ hemat " + rp(round(hemat)) if hemat else ""}</div></div>'
            f'<div class="nom keluar">{rp(total)}</div></div>', unsafe_allow_html=True)
        if t0.get("struk") and st.session_state.get("tr_struk"):
            from keuangan.penyimpanan import ambil_foto
            img = ambil_foto(t0["struk"])
            if img:
                st.image(img, width=260, caption="Struk")
        buka = any(x["id"] in (edit_id, hapus_id) for x in isi)
        with st.expander(f"Lihat {len(isi)} barang", expanded=buka):
            for x in isi:
                _tampil_tx(x, edit_id, hapus_id, foto=False)
        if not hanya_lihat():
            g = t0["grup"]
            ada = bool(t0.get("struk"))
            with st.expander("📷 Ganti foto struk" if ada else "📷 Tambah foto struk (untuk semua barang)"):
                f = st.file_uploader("Foto struk", type=["jpg", "jpeg", "png", "webp"],
                                     key=f"fs_{g}_{versi()}", label_visibility="collapsed")
                a1, a2 = st.columns(2)
                if a1.button("Simpan foto", key=f"fs_ok_{g}_{versi()}", disabled=f is None, type="primary"):
                    _simpan_foto_struk(g, f, False)
                if ada and a2.button("Hapus foto", key=f"fs_del_{g}_{versi()}"):
                    _simpan_foto_struk(g, None, True)
            if st.session_state.get("hapus_grup") == g:
                semua = [x for x in D["transaksi"] if x.get("grup") == g]
                st.warning(f"Hapus seluruh struk ini ({len(semua)} barang, {rp(sum(int(x['jumlah']) for x in semua))})? "
                           "Semua barangnya masuk Tempat sampah.")
                a, b, _ = st.columns([2, 1, 2])
                if a.button("Ya, hapus struk", key=f"ya_grup_{g}", type="primary"):
                    _hapus_struk(g)
                b.button("Batal", key=f"batal_grup_{g}", on_click=atur, args=("hapus_grup", None))
            else:
                st.button("🗑 Hapus seluruh struk", key=f"hapus_grup_{g}", on_click=atur, args=("hapus_grup", g))


def _satuan_tampil(hasil: list) -> list:
    """Kelompokkan transaksi satu struk (grup sama, minimal 2) jadi satu satuan tampil."""
    per = {}
    for t in hasil:
        if t.get("grup"):
            per.setdefault(t["grup"], []).append(t)
    satuan, terlihat = [], set()
    for t in hasil:
        g = t.get("grup")
        if g and len(per[g]) > 1:
            if g not in terlihat:
                terlihat.add(g)
                satuan.append(per[g])
        else:
            satuan.append([t])
    return satuan


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
    if not hanya_lihat():
        from keuangan.massal import panel_massal
        panel_massal(hasil)
    if any(x.get("struk") for x in hasil):
        st.toggle("Tampilkan foto struk", key="tr_struk")
    batas = st.session_state.get("tr_batas", HALAMAN_ISI)
    edit_id, hapus_id = st.session_state.get("edit_tx"), st.session_state.get("hapus_tx")
    satuan = _satuan_tampil(hasil)
    for u in satuan[:batas]:
        if len(u) > 1:
            _kartu_struk(u, edit_id, hapus_id)
        else:
            _tampil_tx(u[0], edit_id, hapus_id)
    if len(satuan) > batas:
        st.write("")
        if st.button(f"Tampilkan lebih banyak ({len(satuan) - batas} lagi)", key="tr_lagi"):
            st.session_state.tr_batas = batas + HALAMAN_ISI
            st.rerun()
