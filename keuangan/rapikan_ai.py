"""Rapikan hasil impor dengan bantuan AI: nama toko ganda, kategori datar hasil impor, dan catatan transaksi yang mentah.
Semua usulan ditampilkan dulu dan hanya diterapkan setelah dicentang dan disetujui."""
import json

import streamlit as st

from keuangan.ai import gerbang, json_dari, kirim_dengan_pratinjau, samarkan
from keuangan.ai_fitur import PERAN, _daftar
from keuangan.bantu import anak_dari, arti_kategori, catat, e, kat_dari, nama_kat, selesai_simpan, toko_dari, versi
from keuangan.inti import D

MAKS_TOKO, MAKS_KAT, MAKS_CATATAN = 120, 60, 80
MERAH_IMPOR = ("🏷️", "#9aa0a6")  # ikon dan warna kategori yang dibuat otomatis oleh impor


# ================================================================ toko
def paket_toko() -> dict:
    semua = sorted(D["toko"], key=lambda x: x["nama"].lower())[:MAKS_TOKO]
    samar = 0
    baris = []
    for i, x in enumerate(semua):
        m, n = samarkan(x["nama"])
        samar += n
        baris.append({"i": i, "nama": m[:60]})
    sistem = (PERAN + 'Tiap baris adalah nama toko. Kelompokkan nama yang merujuk ke toko atau merek yang sama (beda tulisan, huruf besar, nomor atau kode cabang). '
              'Balas daftar JSON: [{"nama_rapi": nama toko yang bersih tanpa nomor cabang, huruf kapital di awal tiap kata kecuali singkatan, "i": [nomor baris]}]. '
              "Satu nama yang hanya perlu dirapikan tulisannya boleh berdiri sendiri. Jangan gabungkan toko yang berbeda merek. Lewati nama yang sudah rapi dan tidak punya kembaran.")
    return {"sistem": sistem, "pengguna": json.dumps({"toko": baris}, ensure_ascii=False, indent=1), "ringkas": f"{len(baris)} nama toko (tanpa transaksi dan nominal)",
            "samar": samar, "item": len(baris), "maks": 3000, "asal": [x["id"] for x in semua]}


def terapkan_toko(teks: str, paket: dict) -> list:
    """[{"nama": rapi, "ids": [id toko]}] yang lolos saringan: nomor harus ada, satu nomor tidak boleh dipakai dua kelompok."""
    asal, terpakai, hasil = paket["asal"], set(), []
    for g in _daftar(json_dari(teks)):
        if not isinstance(g, dict) or not isinstance(g.get("i"), list):
            continue
        ids = []
        for n in g["i"]:
            if isinstance(n, int) and 0 <= n < len(asal) and n not in terpakai:
                ids.append(asal[n])
                terpakai.add(n)
        nama = " ".join(str(g.get("nama_rapi") or "").split())[:60]
        if ids and nama:
            hasil.append({"nama": nama, "ids": ids})
    return [g for g in hasil if len(g["ids"]) > 1 or (toko_dari(g["ids"][0]) or {}).get("nama") != g["nama"]]


def _punya_lokasi(x: dict) -> bool:
    return bool(x.get("lokasi") or x.get("lat") or x.get("titik"))


def gabung_toko(ids: list, nama: str):
    """Pertahankan toko pertama (nama diganti nama rapi), pindahkan semua rujukan dari toko lain, lalu hapus yang lain."""
    utama, lain = ids[0], set(ids[1:])
    for t in D["transaksi"]:
        if t.get("toko") in lain:
            t["toko"] = utama
    for a in D["anggaran"]:
        if a.get("tipe") == "toko" and a.get("target") in lain:
            a["target"] = utama
    for l in D["belanja"]:
        if l.get("toko") in lain:
            l["toko"] = utama
    k = toko_dari(utama)
    if k:
        k["nama"] = nama
    D["toko"] = [x for x in D["toko"] if x["id"] not in lain]


# ================================================================ kategori
def kandidat_kategori(semua_datar: bool = False) -> list:
    """Kategori utama tanpa sub. Bawaan hanya yang dibuat otomatis oleh impor (ikon dan warna bawaan)."""
    hasil = []
    for k in D["kategori"]:
        if k.get("induk") or anak_dari(k["id"]):
            continue
        if semua_datar or (k.get("ikon") == MERAH_IMPOR[0] and k.get("warna") == MERAH_IMPOR[1]):
            hasil.append(k)
    return sorted(hasil, key=lambda k: k["nama"].lower())[:MAKS_KAT]


def _tujuan(jenis: str, kecuali: set) -> list:
    return [nama_kat(k["id"]) for k in D["kategori"] if k["jenis"] == jenis and k["id"] not in kecuali]


def paket_kategori(kand: list) -> dict:
    ids = {k["id"] for k in kand}
    isi = {"kategori_impor": [{"i": i, "nama": k["nama"], "jenis": k["jenis"]} for i, k in enumerate(kand)],
           "tujuan_keluar": _tujuan("keluar", ids), "tujuan_masuk": _tujuan("masuk", ids), "arti_kategori": arti_kategori()}
    sistem = (PERAN + 'kategori_impor adalah kategori yang dibuat otomatis saat impor dari aplikasi lain. Cocokkan tiap kategori dengan SATU nama kategori tujuan yang paling tepat '
              '(tujuan_keluar bila jenisnya keluar, tujuan_masuk bila masuk), memakai arti_kategori bila ada. '
              'Balas daftar JSON: [{"i": nomor, "tujuan": nama PERSIS dari daftar tujuan, atau null bila tidak ada yang cocok}]. Jangan memaksa; pakai null bila ragu.')
    return {"sistem": sistem, "pengguna": json.dumps(isi, ensure_ascii=False, indent=1), "ringkas": f"{len(kand)} nama kategori hasil impor dan daftar nama kategori Anda",
            "samar": 0, "item": len(kand), "maks": 3000, "asal": [k["id"] for k in kand]}


def terapkan_kategori(teks: str, paket: dict) -> list:
    """[(id sumber, id tujuan)]; nama tujuan harus persis ada dan sejenis."""
    hasil = []
    for x in _daftar(json_dari(teks)):
        if not (isinstance(x, dict) and isinstance(x.get("i"), int) and 0 <= x["i"] < len(paket["asal"])):
            continue
        sumber = kat_dari(paket["asal"][x["i"]])
        n = str(x.get("tujuan") or "").strip().lower()
        tujuan = next((k for k in D["kategori"] if n and nama_kat(k["id"]).lower() == n and sumber and k["jenis"] == sumber["jenis"] and k["id"] != sumber["id"]), None)
        if sumber and tujuan:
            hasil.append((sumber["id"], tujuan["id"]))
    return hasil


def gabung_kategori(sumber: str, tujuan: str):
    for t in D["transaksi"]:
        if t.get("kategori") == sumber:
            t["kategori"] = tujuan
    for t in D["tagihan"]:
        if t["kategori"] == sumber:
            t["kategori"] = tujuan
    for b in D["barang"]:
        if b["kategori"] == sumber:
            b["kategori"] = tujuan
    ada = {x["kategori"] for x in D["anggaran"] if x["kategori"] != sumber}
    D["anggaran"] = [x for x in D["anggaran"] if x["kategori"] != sumber or tujuan not in ada]
    for x in D["anggaran"]:
        if x["kategori"] == sumber:
            x["kategori"] = tujuan
    for a in D.get("amplop", []):
        a["kategori"] = [tujuan if k == sumber else k for k in a.get("kategori", [])]
    D["kategori"] = [x for x in D["kategori"] if x["id"] != sumber]


# ================================================================ catatan
def calon_catatan(semua: bool = False) -> list:
    """Catatan unik (belum rapi) dari transaksi hasil impor, atau dari semua transaksi bila diminta."""
    sudah, hasil = set(), []
    for t in D["transaksi"]:
        c = str(t.get("catatan") or "").strip()
        if not c or t.get("barang") or t.get("catatan_asli") or c in sudah:
            continue
        if not semua and t.get("oleh") != "impor":
            continue
        sudah.add(c)
        hasil.append(c)
    return hasil[:MAKS_CATATAN]


def paket_catatan(catatan: list) -> dict:
    unik, asal, samar = [], {}, 0
    for c in catatan:
        m, n = samarkan(c, ketat=True, kecuali=[x["nama"] for x in D["toko"]])
        samar += n
        asal[len(unik)] = c
        unik.append({"i": len(unik), "teks": m[:120]})
    sistem = (PERAN + 'Tiap baris adalah catatan transaksi dari aplikasi keuangan lain. Rapikan jadi keterangan singkat yang seragam: maksimal 60 huruf, huruf kapital di awal kata penting, '
              'buang emoji, kode, nomor referensi, dan tanda baca berlebih, pertahankan arti aslinya. Bila memuat beberapa barang, tulis dipisah koma. '
              'Balas daftar JSON: [{"i": nomor, "catatan": hasil rapi}]. Jangan menambah informasi yang tidak ada. Bila sudah rapi, kembalikan sama persis.')
    return {"sistem": sistem, "pengguna": json.dumps({"catatan": unik}, ensure_ascii=False, indent=1), "ringkas": f"{len(unik)} catatan unik (tanpa nominal, tanggal, dan toko)",
            "samar": samar, "item": len(unik), "maks": 3000, "asal": asal}


def terapkan_catatan(teks: str, paket: dict) -> list:
    """[(catatan asli, catatan rapi)] hanya yang berubah; panjang dibatasi dan teks tersamar dari AI tidak boleh menimpa data asli."""
    hasil = []
    for x in _daftar(json_dari(teks)):
        if not (isinstance(x, dict) and isinstance(x.get("i"), int) and x["i"] in paket["asal"]):
            continue
        baru = " ".join(str(x.get("catatan") or "").split())[:60]
        lama = paket["asal"][x["i"]]
        if baru and baru != lama and "[" not in baru:  # penanda samaran seperti [no] berarti AI menyalin teks yang disamarkan
            hasil.append((lama, baru))
    return hasil


def tulis_catatan(pilihan: list):
    peta = dict(pilihan)
    for t in D["transaksi"]:
        c = str(t.get("catatan") or "").strip()
        if c in peta and not t.get("catatan_asli"):
            t["catatan_asli"] = c
            t["catatan"] = peta[c]


# ================================================================ halaman
def _tab_toko():
    st.caption("Mencari nama toko yang sama tetapi tertulis berbeda (misalnya Indomaret dan INDOMARET 1234), lalu menyatukannya. Transaksi, anggaran toko, dan daftar belanja ikut dipindah.")
    if len(D["toko"]) < 1:
        st.info("Belum ada toko.")
        return
    sk = "rp_toko"
    if gerbang("rapikan", "toko"):
        paket = paket_toko()
        jawab = kirim_dengan_pratinjau("rapikan", paket, "toko", bentuk_json=True)
        if jawab is not None:
            try:
                st.session_state[sk] = terapkan_toko(jawab, paket)
            except RuntimeError as ex:
                st.error(str(ex))
            else:
                st.rerun()
    usul = st.session_state.get(sk)
    if usul is None:
        return
    if not usul:
        st.success("AI tidak menemukan nama toko yang perlu disatukan atau dirapikan.")
        return
    pilih = []
    for n, g in enumerate(usul):
        x = [toko_dari(i) for i in g["ids"] if toko_dari(i)]
        if not x:
            continue
        lokasi_beda = len(x) > 1 and sum(1 for y in x if _punya_lokasi(y)) > 1
        with st.container(border=True):
            ya = st.checkbox(f"Jadikan **{g['nama']}**", value=not lokasi_beda, key=f"rp_t_{n}_{versi()}")
            st.caption(" · ".join(y["nama"] for y in x) + (" · beberapa punya lokasi sendiri, menggabungkan akan menghapus lokasi cabang lain" if lokasi_beda else ""))
        if ya:
            pilih.append(g)
    if st.button(f"Terapkan {len(pilih)} usulan toko", type="primary", disabled=not pilih, key=f"rp_t_ok_{versi()}"):
        for g in pilih:
            ids = [i for i in g["ids"] if toko_dari(i)]
            if ids:
                gabung_toko(ids, g["nama"])
        catat("perawatan", f"Rapikan toko dengan AI: {len(pilih)} usulan")
        st.session_state.pop(sk, None)
        selesai_simpan(f"{len(pilih)} usulan toko diterapkan.")


def _tab_kategori():
    st.caption("Kategori yang dibuat otomatis saat impor biasanya datar dan mirip yang sudah ada. AI mengusulkan menggabungkannya ke kategori atau sub kategori Anda. Transaksi, tagihan, anggaran, dan amplop ikut dipindah.")
    semua = st.checkbox("Sertakan semua kategori utama yang belum punya sub", key="rp_k_semua")
    kand = kandidat_kategori(semua)
    if not kand:
        st.info("Tidak ada kategori hasil impor yang perlu dirapikan.")
        return
    sk = "rp_kat"
    if gerbang("rapikan", "kat"):
        paket = paket_kategori(kand)
        jawab = kirim_dengan_pratinjau("rapikan", paket, "kat", bentuk_json=True)
        if jawab is not None:
            try:
                st.session_state[sk] = terapkan_kategori(jawab, paket)
            except RuntimeError as ex:
                st.error(str(ex))
            else:
                st.rerun()
    usul = st.session_state.get(sk)
    if usul is None:
        return
    usul = [(s, t) for s, t in usul if kat_dari(s) and kat_dari(t)]
    if not usul:
        st.success("AI tidak menemukan kategori yang cocok digabungkan.")
        return
    pilih = []
    for n, (s, t) in enumerate(usul):
        pakai = sum(1 for x in D["transaksi"] if x.get("kategori") == s)
        with st.container(border=True):
            if st.checkbox(f"**{kat_dari(s)['nama']}** gabung ke **{nama_kat(t)}**", value=True, key=f"rp_k_{n}_{versi()}"):
                pilih.append((s, t))
            st.caption(f"{pakai} transaksi dipindah, lalu kategori {kat_dari(s)['nama']} dihapus")
    if st.button(f"Terapkan {len(pilih)} penggabungan", type="primary", disabled=not pilih, key=f"rp_k_ok_{versi()}"):
        for s, t in pilih:
            if kat_dari(s) and kat_dari(t):
                catat("kategori", f"Gabung kategori {nama_kat(s)} ke {nama_kat(t)} (rapikan AI)")
                gabung_kategori(s, t)
        st.session_state.pop(sk, None)
        selesai_simpan(f"{len(pilih)} kategori digabung.")


def _tab_catatan():
    st.caption("Merapikan catatan mentah (emoji, kode, huruf kapital semua, beberapa barang dalam satu baris) jadi keterangan singkat. Catatan asli disimpan di transaksi, jadi tidak hilang. "
               "Satu catatan berisi beberapa barang hanya ditulis ulang dipisah koma; transaksinya tidak dipecah karena nominal per barang tidak diketahui.")
    semua = st.checkbox("Sertakan transaksi yang bukan hasil impor", key="rp_c_semua")
    calon = calon_catatan(semua)
    if not calon:
        st.info("Tidak ada catatan yang perlu dirapikan.")
        return
    sk = "rp_cat"
    if gerbang("rapikan", "cat"):
        paket = paket_catatan(calon)
        jawab = kirim_dengan_pratinjau("rapikan", paket, "cat", bentuk_json=True)
        if jawab is not None:
            try:
                st.session_state[sk] = terapkan_catatan(jawab, paket)
            except RuntimeError as ex:
                st.error(str(ex))
            else:
                st.rerun()
    usul = st.session_state.get(sk)
    if usul is None:
        return
    if not usul:
        st.success("Semua catatan sudah rapi menurut AI.")
        return
    pilih = []
    for n, (lama, baru) in enumerate(usul):
        pakai = sum(1 for t in D["transaksi"] if str(t.get("catatan") or "").strip() == lama)
        with st.container(border=True):
            if st.checkbox(f"{baru}", value=True, key=f"rp_c_{n}_{versi()}"):
                pilih.append((lama, baru))
            st.caption(f"Sekarang: {lama} · {pakai} transaksi")
    if st.button(f"Terapkan {len(pilih)} catatan", type="primary", disabled=not pilih, key=f"rp_c_ok_{versi()}"):
        tulis_catatan(pilih)
        catat("perawatan", f"Rapikan catatan dengan AI: {len(pilih)} catatan")
        st.session_state.pop(sk, None)
        selesai_simpan(f"{len(pilih)} catatan dirapikan.")


def halaman_rapikan():
    st.caption("Bantuan AI untuk merapikan data yang berantakan setelah impor dari aplikasi lain. Yang dikirim hanya teksnya (nama toko, nama kategori, atau catatan) tanpa nominal, tanggal, dan dompet. Tidak ada yang berubah sebelum Anda mencentang dan menekan Terapkan.")
    t1, t2, t3 = st.tabs(["Toko", "Kategori", "Catatan"])
    with t1:
        _tab_toko()
    with t2:
        _tab_kategori()
    with t3:
        _tab_catatan()
