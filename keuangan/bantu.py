"""Pembantu data: saldo, ringkasan bulanan, tanggal berulang, pencatatan aktivitas, dan komponen tampilan kecil."""
import calendar
import html
from datetime import date, timedelta

import streamlit as st

from keuangan.inti import (
    D, JENIS, MAKS_AKTIVITAS, SEP, TANPA_KAT, baru_id, fmt_iso, hari_ini, iso_ke_date, nama_bulan, pengguna_nama, rp,
    sekarang,
)
from keuangan.penyimpanan import commit

e = html.escape


# ---------------------------------------------------------------- keadaan halaman
def atur(kunci: str, nilai):
    st.session_state[kunci] = nilai


def pindah_halaman(h: str):
    """Ganti menu sekaligus tutup form/konfirmasi yang masih terbuka."""
    st.session_state.halaman = h
    for k in [k for k in st.session_state if str(k).startswith(("tb_", "edit_", "hapus_", "bayar_f", "tr_"))]:
        st.session_state.pop(k, None)


def versi() -> int:
    return st.session_state.get("ver", 0)


def selesai_simpan(pesan: str, **setelah):
    """Simpan ke penyimpanan. Kalau berhasil, atur keadaan halaman lalu muat ulang."""
    if commit(pesan):
        for k, v in setelah.items():
            st.session_state[k] = v
        st.session_state.ver = versi() + 1
        st.rerun()


def catat(jenis: str, rincian: str):
    """Tambah satu baris riwayat aktivitas. Dipanggil sebelum selesai_simpan()."""
    log = D["aktivitas"]
    log.append({"id": baru_id(), "waktu": sekarang().strftime("%Y-%m-%d %H:%M"), "oleh": pengguna_nama(),
                "jenis": jenis, "rincian": rincian})
    del log[:-MAKS_AKTIVITAS]


# ---------------------------------------------------------------- dompet dan kategori
def dompet_aktif() -> list:
    return [d for d in D["dompet"] if not d.get("arsip")]


def dompet_dari(id_):
    return next((d for d in D["dompet"] if d["id"] == id_), None)


def nama_dompet(id_) -> str:
    d = dompet_dari(id_)
    return d["nama"] if d else "(dompet dihapus)"


def f_dompet(tambahan: dict | None = None):
    """Fungsi label untuk selectbox: kamus dibuat saat render, tidak membaca session state saat dipanggil."""
    m = {d["id"]: d["nama"] for d in D["dompet"]}
    m.update(tambahan or {})
    return lambda i: m.get(i, "(dompet dihapus)")


def kat_dari(id_):
    return next((k for k in D["kategori"] if k["id"] == id_), None)


def anak_dari(id_) -> list:
    return [k for k in D["kategori"] if k.get("induk") == id_]


def turunan(id_) -> set:
    """Kategori itu sendiri ditambah sub kategorinya."""
    return {id_} | {k["id"] for k in anak_dari(id_)}


def akar(id_) -> str:
    """Id kategori utama dari sebuah kategori (dirinya sendiri kalau sudah utama)."""
    k = kat_dari(id_)
    return k["induk"] if k and k.get("induk") and kat_dari(k["induk"]) else id_


def nama_kat(id_) -> str:
    """'Rumah' untuk kategori utama, 'Rumah › Listrik' untuk sub kategori."""
    k = kat_dari(id_)
    if not k:
        return TANPA_KAT
    p = kat_dari(k.get("induk"))
    return f'{p["nama"]}{SEP}{k["nama"]}' if p else k["nama"]


def f_kat(tambahan: dict | None = None):
    m = {k["id"]: nama_kat(k["id"]) for k in D["kategori"]}
    m.update(tambahan or {})
    return lambda i: m.get(i, "(kategori dihapus)")


def kategori_utama(jenis: str) -> list:
    return [k for k in D["kategori"] if k["jenis"] == jenis and not (k.get("induk") and kat_dari(k["induk"]))]


def kategori_jenis(jenis: str) -> list:
    """Semua kategori satu jenis, berurutan: kategori utama lalu sub kategorinya."""
    hasil = []
    for p in kategori_utama(jenis):
        hasil.append(p)
        hasil += sorted(anak_dari(p["id"]), key=lambda k: k["nama"].lower())
    return hasil


def ikon_kat(id_) -> str:
    """Bulatan berwarna berisi ikon kategori, untuk dipasang di HTML."""
    k = kat_dari(id_)
    if not k:
        return ""
    return f'<span class="kc" style="background:{e(k.get("warna", "#9aa0a6"))}">{e(k.get("ikon", "🏷️"))}</span>'


def kat_pertama(jenis: str, pilihan: str = ""):
    """Id kategori pilihan kalau ada, kalau tidak kategori pertama dengan jenis itu."""
    if kat_dari(pilihan):
        return pilihan
    daftar = kategori_jenis(jenis)
    return daftar[0]["id"] if daftar else ""


# ---------------------------------------------------------------- barang / produk
def barang_dari(id_):
    return next((b for b in D["barang"] if b["id"] == id_), None)


def barang_dalam(kat: str) -> list:
    """Barang milik kategori itu dan sub kategorinya, urut nama."""
    ids = turunan(kat)
    return sorted([b for b in D["barang"] if b["kategori"] in ids], key=lambda b: b["nama"].lower())


def f_barang(kat: str = ""):
    """Label pilihan barang. Kalau barang berada di sub kategori lain dari `kat`, nama sub ditambahkan."""
    m = {}
    for b in D["barang"]:
        k = kat_dari(b["kategori"])
        m[b["id"]] = b["nama"] if b["kategori"] == kat or not k else f'{b["nama"]} ({k["nama"]})'
    m[""] = "(tanpa barang)"
    return lambda i: m.get(i, "(barang dihapus)")


def kunci_urut(t: dict):
    """Urutan kronologis: tanggal, lalu jam beli, lalu saat dicatat."""
    return (t["tgl"], t.get("waktu", "") or "", t.get("dibuat", ""))


def transaksi_barang(id_) -> list:
    """Transaksi yang memakai barang ini, terbaru dulu."""
    return sorted([t for t in D["transaksi"] if t.get("barang") == id_], key=kunci_urut, reverse=True)


# ---------------------------------------------------------------- toko / tempat beli
def toko_dari(id_):
    return next((x for x in D["toko"] if x["id"] == id_), None)


def f_toko(tambahan: dict | None = None):
    m = {x["id"]: x["nama"] + (f' · {x["lokasi"]}' if x.get("lokasi") else "") for x in D["toko"]}
    m[""] = "(tanpa toko)"
    m.update(tambahan or {})
    return lambda i: m.get(i, "(toko dihapus)")


def transaksi_toko(id_) -> list:
    return sorted([t for t in D["transaksi"] if t.get("toko") == id_], key=kunci_urut, reverse=True)


def teks_toko(t: dict) -> str:
    """'Indomaret (Jl. Merdeka)' atau hanya lokasi / hanya toko; '' bila keduanya kosong."""
    x = toko_dari(t.get("toko"))
    nama = x["nama"] if x else ""
    lok = t.get("lokasi", "")
    return f"{nama} ({lok})" if nama and lok else nama or lok


def perbarui_harga_barang(id_):
    """Harga barang = harga satuan pada transaksi terbarunya."""
    b = barang_dari(id_)
    ada = [t for t in transaksi_barang(id_) if t.get("harga_satuan")]
    if b and ada:
        b["harga"] = int(round(ada[0]["harga_satuan"]))


def teks_barang(t: dict) -> str:
    """'Indomie × 5 bungkus' atau '' bila transaksi tanpa barang."""
    b = barang_dari(t.get("barang"))
    if not b:
        return ""
    q = t.get("qty") or 1
    q = int(q) if float(q).is_integer() else q
    return f'{b["nama"]} × {q}' + (f' {b["satuan"]}' if b.get("satuan") else "")


def saldo_dompet(id_, sampai: str | None = None) -> int:
    """Saldo awal ditambah semua transaksi (sampai tanggal `sampai` bila diisi)."""
    d = dompet_dari(id_)
    if not d:
        return 0
    s = int(d.get("saldo_awal", 0) or 0)
    for t in D["transaksi"]:
        if sampai and t["tgl"] > sampai:
            continue
        j = int(t["jumlah"])
        if t["jenis"] == "masuk" and t["dompet"] == id_:
            s += j
        elif t["jenis"] == "keluar" and t["dompet"] == id_:
            s -= j
        elif t["jenis"] == "transfer":
            if t["dompet"] == id_:
                s -= j + int(t.get("biaya", 0) or 0)
            if t.get("ke") == id_:
                s += j
    return s


def total_saldo() -> int:
    return sum(saldo_dompet(d["id"]) for d in D["dompet"] if not d.get("arsip"))


# ---------------------------------------------------------------- bulan dan ringkasan
def ym_ini() -> str:
    return hari_ini().strftime("%Y-%m")


def geser_bulan(ym: str, n: int) -> str:
    t, b = int(ym[:4]), int(ym[5:7])
    i = t * 12 + (b - 1) + n
    return f"{i // 12:04d}-{i % 12 + 1:02d}"


def daftar_bulan() -> list:
    """Semua bulan dari transaksi paling awal sampai bulan ini (terbaru dulu)."""
    ada = [t["tgl"][:7] for t in D["transaksi"]]
    awal = min(ada + [ym_ini()])
    hasil, b = [], ym_ini()
    while b >= awal:
        hasil.append(b)
        b = geser_bulan(b, -1)
    return hasil


def pilih_bulan(kunci: str, label: str = "Bulan") -> str:
    if kunci not in st.session_state or st.session_state[kunci] not in daftar_bulan():
        st.session_state[kunci] = ym_ini()
    return st.selectbox(label, daftar_bulan(), key=kunci, format_func=nama_bulan)


def transaksi_bulan(ym: str) -> list:
    return [t for t in D["transaksi"] if t["tgl"][:7] == ym]


def ringkas_bulan(ym: str):
    masuk = sum(int(t["jumlah"]) for t in transaksi_bulan(ym) if t["jenis"] == "masuk")
    keluar = sum(int(t["jumlah"]) for t in transaksi_bulan(ym) if t["jenis"] == "keluar")
    biaya = sum(int(t.get("biaya", 0) or 0) for t in transaksi_bulan(ym) if t["jenis"] == "transfer")
    return masuk, keluar + biaya


def per_kategori(ym: str, jenis: str = "keluar", gabung: bool = False) -> dict:
    """{id kategori: total} untuk satu bulan, terbesar dulu. gabung=True menjumlahkan sub kategori ke kategori utamanya."""
    h = {}
    for t in transaksi_bulan(ym):
        if t["jenis"] == jenis:
            k = akar(t.get("kategori", "")) if gabung else t.get("kategori", "")
            h[k] = h.get(k, 0) + int(t["jumlah"])
    return dict(sorted(h.items(), key=lambda x: -x[1]))


# ---------------------------------------------------------------- tanggal berulang
TIAP = {"mingguan": "Tiap minggu", "bulanan": "Tiap bulan", "tiga_bulan": "Tiap 3 bulan",
        "tahunan": "Tiap tahun", "sekali": "Sekali saja"}


def maju_tgl(d: date, tiap: str) -> date:
    """Tanggal jatuh tempo berikutnya. Tanggal 31 di bulan pendek jatuh di hari terakhir bulan itu."""
    if tiap == "mingguan":
        return d + timedelta(days=7)
    n = {"bulanan": 1, "tiga_bulan": 3, "tahunan": 12}.get(tiap, 1)
    i = d.year * 12 + d.month - 1 + n
    t, b = divmod(i, 12)
    b += 1
    return date(t, b, min(d.day, calendar.monthrange(t, b)[1]))


# ---------------------------------------------------------------- tampilan kecil
def kartu_stat(judul: str, nilai: str, ket: str = "", kelas: str = "") -> str:
    return (f'<div class="sc-stat"><div class="sc-lab">{e(judul)}</div>'
            f'<div class="sc-val {kelas}" style="font-size:1.35rem">{e(nilai)}</div>'
            f'<div class="sc-ket">{e(ket)}</div></div>')


def deretan_stat(*kartu: str):
    st.markdown('<div class="statcard">' + "".join(kartu) + "</div>", unsafe_allow_html=True)


def batang(pakai: float, batas: float, tebal: str = "") -> str:
    """Batang kemajuan. Warna berubah jadi kuning di 80% dan merah kalau lewat 100% (kecuali `tebal` diisi)."""
    persen = (pakai / batas * 100) if batas else 0
    k = tebal or ("b" if persen > 100 else "w" if persen >= 80 else "")
    return f'<div class="bar {k}"><i style="width:{min(persen, 100):.1f}%"></i></div>'


def baris_transaksi(t: dict) -> str:
    """Satu baris transaksi sebagai HTML (ikon, judul, keterangan, nominal)."""
    j = t["jenis"]
    if j == "transfer":
        judul = t.get("catatan") or "Transfer"
        meta = f'{fmt_iso(t["tgl"])} · {nama_dompet(t["dompet"])} → {nama_dompet(t.get("ke"))}'
        if t.get("biaya"):
            meta += f' · biaya {rp(t["biaya"])}'
        ikon, nom = "⇄", rp(t["jumlah"])
    else:
        judul = t.get("catatan") or teks_barang(t) or nama_kat(t.get("kategori"))
        meta = f'{fmt_iso(t["tgl"])}{" " + t["waktu"] if t.get("waktu") else ""} · {nama_dompet(t["dompet"])} · {nama_kat(t.get("kategori"))}'
        if t.get("catatan") and teks_barang(t):
            meta += f' · {teks_barang(t)}'
        if teks_toko(t):
            meta += f' · {teks_toko(t)}'
        ikon = "↓" if j == "masuk" else "↑"
        nom = ("+" if j == "masuk" else "-") + rp(t["jumlah"])
    k = kat_dari(t.get("kategori")) if j != "transfer" else None
    kotak = (f'<div class="ic kat" style="background:{e(k.get("warna", "#9aa0a6"))}">{e(k.get("ikon", "🏷️"))}</div>' if k
             else f'<div class="ic {j}">{ikon}</div>')
    return (f'<div class="rt">{kotak}<div class="isi"><div class="jd">{e(judul)}</div>'
            f'<div class="mt">{e(meta)}</div></div><div class="nom {j}">{e(nom)}</div></div>')


def tambah_transaksi(jenis, tgl, jumlah, dompet, kategori="", catatan="", ke="", biaya=0, **kait) -> dict:
    t = {"id": baru_id(), "jenis": jenis, "tgl": tgl.isoformat() if isinstance(tgl, date) else tgl,
         "jumlah": int(jumlah), "dompet": dompet, "kategori": kategori, "catatan": (catatan or "").strip(),
         "dibuat": sekarang().strftime("%Y-%m-%d %H:%M:%S.%f"), "oleh": pengguna_nama()}
    if jenis == "transfer":
        t["ke"], t["biaya"] = ke, int(biaya or 0)
    t.update({k: v for k, v in kait.items() if v})
    D["transaksi"].append(t)
    if t.get("barang"):
        perbarui_harga_barang(t["barang"])
    return t


def ringkas_teks(t: dict) -> str:
    """Satu kalimat untuk riwayat aktivitas."""
    isi = f'{JENIS[t["jenis"]]} {rp(t["jumlah"])}'
    if t["jenis"] == "transfer":
        return f'{isi}, {nama_dompet(t["dompet"])} → {nama_dompet(t.get("ke"))}'
    return (f'{isi}, {nama_kat(t.get("kategori"))}, {nama_dompet(t["dompet"])}' + (f", {teks_barang(t)}" if teks_barang(t) else "")
            + (f", di {teks_toko(t)}" if teks_toko(t) else "") + (f' ("{t["catatan"]}")' if t.get("catatan") else ""))


def pilih_kategori(kunci: str, jenis: str, awal: str = "", kolom=None, tampil_sub: bool = True) -> str:
    """Dua kotak terpisah: Kategori (utama) lalu Sub kategori. Kembalikan id kategori efektif
    (sub kalau dipilih, kalau tidak kategori utama). Dipakai di luar st.form agar sub ikut berubah."""
    utama = [k["id"] for k in kategori_utama(jenis)]
    if not utama:
        return ""
    a = akar(awal) if kat_dari(awal) else ""
    sub_awal = awal if a and a != awal else ""
    c1, c2 = kolom or st.columns(2)
    if st.session_state.get(f"{kunci}_kat") not in utama:
        st.session_state.pop(f"{kunci}_kat", None)
    kat = c1.selectbox("Kategori", utama, index=utama.index(a) if a in utama else 0, format_func=f_kat(), key=f"{kunci}_kat")
    if not tampil_sub:
        return kat
    anak = [""] + [k["id"] for k in sorted(anak_dari(kat), key=lambda k: k["nama"].lower())]
    if st.session_state.get(f"{kunci}_sub") not in anak:
        st.session_state.pop(f"{kunci}_sub", None)
    nama_sub = {k["id"]: k["nama"] for k in anak_dari(kat)}
    nama_sub[""] = "(tanpa sub kategori)"
    sub = c2.selectbox("Sub kategori", anak, index=anak.index(sub_awal) if sub_awal in anak else 0,
                       format_func=lambda i: nama_sub.get(i, "(dihapus)"), key=f"{kunci}_sub")
    return sub or kat
