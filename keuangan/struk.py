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


# ---------------------------------------------------------------- editor berbentuk kartu (ramah HP)
def editor_kartu(kunci: str, awal: pd.DataFrame | None = None, tetap: bool = False) -> pd.DataFrame:
    """Satu kartu per barang: pilih Barang (atau Kategori), banyaknya, harga. Kembalikan DataFrame berkolom KOLOM
    supaya bisa dibaca baca_baris(). `tetap` = barang dan kategori hasil isian awal tidak bisa diganti."""
    id_b, lab_b = peta_barang()
    id_k, lab_k = peta_kategori()
    sk = f"{kunci}_ids"
    if sk not in st.session_state:
        n = 0
        ids = []
        for r in (awal.to_dict("records") if awal is not None and len(awal) else [{}]):
            ids.append(n)
            st.session_state[f"{kunci}_{n}_brg"] = r.get("Barang") if r.get("Barang") in id_b else ""
            st.session_state[f"{kunci}_{n}_kat"] = r.get("Kategori") if r.get("Kategori") in id_k else ""
            st.session_state[f"{kunci}_{n}_ket"] = r.get("Keterangan") if isinstance(r.get("Keterangan"), str) else ""
            st.session_state[f"{kunci}_{n}_qty"] = float(r["Banyaknya"]) if not _kosong(r.get("Banyaknya")) else 1.0
            st.session_state[f"{kunci}_{n}_hrg"] = int(r["Harga satuan"]) if not _kosong(r.get("Harga satuan")) else 0
            n += 1
        st.session_state[sk] = ids
        st.session_state[f"{kunci}_next"] = n
    ids = st.session_state[sk]
    opsi_b = [""] + list(id_b)
    opsi_k = [""] + list(id_k)
    baris = []
    hapus = None
    for no, rid in enumerate(ids, start=1):
        k = f"{kunci}_{rid}"
        for suf, ops in (("brg", opsi_b), ("kat", opsi_k)):
            if st.session_state.get(f"{k}_{suf}") not in ops:
                st.session_state[f"{k}_{suf}"] = ""
        with st.container(border=True, key=f"kartu_g_item_{k}"):
            h1, h2 = st.columns([6, 1])
            h1.markdown(f"**Barang {no}**")
            if not tetap and len(ids) > 1 and h2.button("🗑", key=f"{k}_del", help="Hapus barang ini"):
                hapus = rid
            brg = st.selectbox("Barang", opsi_b, key=f"{k}_brg", disabled=tetap and bool(st.session_state.get(f"{k}_brg")),
                               format_func=lambda i: i or "(pilih dari daftar barang)")
            kat = ket = ""
            if not brg:
                kat = st.selectbox("Kategori (untuk barang di luar daftar)", opsi_k, key=f"{k}_kat",
                                   disabled=tetap and bool(st.session_state.get(f"{k}_kat")),
                                   format_func=lambda i: i or "(pilih kategori)")
                ket = st.text_input("Nama / keterangan", key=f"{k}_ket", max_chars=60)
            c1, c2 = st.columns(2)
            qty = c1.number_input("Banyaknya", min_value=0.0, step=1.0, format="%g", key=f"{k}_qty")
            hrg = c2.number_input("Harga satuan (Rp)", min_value=0, step=500, key=f"{k}_hrg")
            b = barang_dari(id_b.get(brg)) if brg else None
            efektif = int(hrg) or int((b or {}).get("harga", 0) or 0)
            if b and not hrg:
                st.caption(f"Harga kosong, memakai harga terakhir {rp(efektif)}.")
            if efektif and qty:
                st.caption(f"Subtotal: {rp(round(qty * efektif))}")
        baris.append({"Barang": brg or None, "Kategori": kat or None, "Keterangan": ket,
                      "Banyaknya": qty, "Harga satuan": int(hrg) if hrg else None})
    if hapus is not None:
        st.session_state[sk] = [i for i in ids if i != hapus]
        st.rerun()
    if not tetap and st.button("➕ Tambah barang", key=f"{kunci}_tambah"):
        st.session_state[f"{kunci}_{st.session_state[f'{kunci}_next']}_qty"] = 1.0
        st.session_state[sk] = ids + [st.session_state[f"{kunci}_next"]]
        st.session_state[f"{kunci}_next"] += 1
        st.rerun()
    df = pd.DataFrame(baris, columns=KOLOM)
    df["Harga satuan"] = df["Harga satuan"].astype("Int64")
    return df
