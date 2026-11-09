"""Satu struk, banyak barang. Dipakai oleh Catat transaksi (mode struk) dan Daftar belanja.

Satu struk disimpan sebagai beberapa transaksi pengeluaran biasa yang berbagi `grup`, tanggal, waktu, toko,
lokasi, dompet, dan foto struk. Jadi laporan per kategori, barang, dan toko tetap bekerja tanpa perubahan.
"""
import pandas as pd
import streamlit as st

from keuangan.bantu import kat_dari, nama_kat, perbarui_harga_barang, tambah_transaksi, transaksi_barang, toko_dari, barang_dari
from keuangan.inti import D, baru_id, rp

KOLOM = ["Barang", "Kategori", "Keterangan", "Banyaknya", "Harga satuan"]


# ---------------------------------------------------------------- pemetaan label
def peta_barang():
    """({label: id}, {id: label}) untuk barang di kategori pengeluaran."""
    ke_id, ke_label = {}, {}
    for b in sorted(D["barang"], key=lambda b: b["nama"].lower()):
        k = kat_dari(b["kategori"])
        if k and k["jenis"] != "keluar":
            continue
        lab = b["nama"] + (f' ({k["nama"]})' if k else "")
        if lab in ke_id:
            lab += f' #{b["id"][:4]}'
        ke_id[lab], ke_label[b["id"]] = b["id"], lab
    return ke_id, ke_label


def peta_kategori():
    """({label: id}, {id: label}) untuk kategori pengeluaran (induk dan sub)."""
    ke_id, ke_label = {}, {}
    for k in sorted([k for k in D["kategori"] if k["jenis"] == "keluar"], key=lambda k: nama_kat(k["id"]).lower()):
        lab = nama_kat(k["id"])
        ke_id[lab], ke_label[k["id"]] = k["id"], lab
    return ke_id, ke_label


def termurah(barang_id: str):
    """(nama toko, harga satuan) terendah dari harga terakhir di tiap toko, atau None."""
    per = {}
    for t in transaksi_barang(barang_id):  # terbaru dulu
        if t.get("toko") and t.get("harga_satuan") and t["toko"] not in per:
            per[t["toko"]] = int(t["harga_satuan"])
    if not per:
        return None
    k = min(per, key=per.get)
    return (toko_dari(k) or {}).get("nama", "?"), per[k]


# ---------------------------------------------------------------- editor tabel
def tabel_kosong(n: int = 3) -> pd.DataFrame:
    return pd.DataFrame({"Barang": [None] * n, "Kategori": [None] * n, "Keterangan": [""] * n,
                         "Banyaknya": [1.0] * n, "Harga satuan": pd.array([None] * n, dtype="Int64")})


def editor_baris(df: pd.DataFrame, key: str, nonaktif=()):
    """data_editor untuk baris struk. Kembalikan DataFrame hasil sunting."""
    _, lab_b = peta_barang()
    _, lab_k = peta_kategori()
    return st.data_editor(
        df, key=key, num_rows="dynamic", hide_index=True, width="stretch", disabled=list(nonaktif),
        column_order=KOLOM,
        column_config={
            "Barang": st.column_config.SelectboxColumn("Barang", options=list(peta_barang()[0]), help="Pilih dari daftar barang, atau kosongkan lalu isi Kategori."),
            "Kategori": st.column_config.SelectboxColumn("Kategori", options=list(peta_kategori()[0]), help="Wajib kalau Barang kosong."),
            "Keterangan": st.column_config.TextColumn("Keterangan", max_chars=60),
            "Banyaknya": st.column_config.NumberColumn("Banyaknya", min_value=0.01, step=1.0, default=1.0, format="%g"),
            "Harga satuan": st.column_config.NumberColumn("Harga satuan", min_value=0, step=100, format="%d",
                                                          help="Kosongkan untuk memakai harga terakhir barang."),
        })


def _kosong(v) -> bool:
    return v is None or (not isinstance(v, str) and pd.isna(v)) or (isinstance(v, str) and not v.strip())


def baca_baris(df: pd.DataFrame):
    """Ubah tabel hasil sunting jadi (baris, daftar_kesalahan). Baris kosong dilewati."""
    id_b, _ = peta_barang()
    id_k, _ = peta_kategori()
    baris, salah = [], []
    for n, r in enumerate(df.to_dict("records"), start=1):
        if all(_kosong(r.get(c)) for c in ("Barang", "Kategori", "Keterangan", "Harga satuan")):
            continue
        b = id_b.get(r.get("Barang")) if not _kosong(r.get("Barang")) else ""
        kat = ""
        if b:
            kat = barang_dari(b)["kategori"]
        elif not _kosong(r.get("Kategori")):
            kat = id_k.get(r["Kategori"], "")
        if not kat:
            salah.append(f"Baris {n}: pilih Barang atau Kategori.")
            continue
        qty = 1.0 if _kosong(r.get("Banyaknya")) else float(r["Banyaknya"])
        harga = 0 if _kosong(r.get("Harga satuan")) else int(round(float(r["Harga satuan"])))
        if not harga and b:
            harga = int(barang_dari(b).get("harga", 0) or 0)
        if qty <= 0:
            salah.append(f"Baris {n}: banyaknya harus lebih dari 0.")
        elif harga <= 0:
            salah.append(f"Baris {n}: isi harga satuan.")
        else:
            baris.append({"barang": b, "kategori": kat, "ket": "" if _kosong(r.get("Keterangan")) else str(r["Keterangan"]).strip(),
                          "qty": qty, "harga": harga})
    return baris, salah


def total_baris(baris: list) -> int:
    return sum(int(round(x["qty"] * x["harga"])) for x in baris)


def total_cepat(df: pd.DataFrame) -> int:
    """Total yang tampil langsung saat mengetik; baris bermasalah diabaikan."""
    baris, _ = baca_baris(df)
    return total_baris(baris)


# ---------------------------------------------------------------- simpan
def simpan_struk(baris: list, tgl, waktu: str, dompet: str, toko: str, lokasi: str, struk: str, catatan: str = "") -> list:
    """Buat satu transaksi pengeluaran per baris. Pemanggil yang menulis riwayat dan commit."""
    grup = baru_id()
    hasil = []
    for x in baris:
        qty = int(x["qty"]) if float(x["qty"]).is_integer() else x["qty"]
        hasil.append(tambah_transaksi(
            "keluar", tgl, round(x["qty"] * x["harga"]), dompet, x["kategori"], x["ket"] or catatan,
            barang=x["barang"], qty=qty if x["barang"] else 0, harga_satuan=x["harga"] if x["barang"] else 0,
            toko=toko, lokasi=lokasi, waktu=waktu, struk=struk, grup=grup))
    for x in baris:
        if x["barang"]:
            perbarui_harga_barang(x["barang"])
    return hasil


def ringkas_struk(baris: list, toko: str) -> str:
    t = toko_dari(toko)
    return f"Struk {len(baris)} barang {rp(total_baris(baris))}" + (f" di {t['nama']}" if t else "")
