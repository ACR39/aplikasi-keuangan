"""Pemeriksa data: temukan transaksi yang janggal (barang hilang, kategori tak cocok, jumlah tak sinkron, rujukan terhapus) dan perbaiki."""
import streamlit as st

from keuangan.bantu import barang_dari, catat, dompet_dari, e, kat_dari, nama_kat, ringkas_teks, selesai_simpan, toko_dari, versi
from keuangan.inti import D, fmt_iso
from keuangan.mutasi import _norm

JENIS_MASALAH = {
    "barang_hilang": "Catatan menyebut barang, tapi barangnya kosong",
    "kategori_beda": "Kategori tidak sama dengan kategori barangnya",
    "jumlah_beda": "Jumlah tidak sama dengan banyaknya × harga satuan",
    "rujukan": "Merujuk ke barang atau toko yang sudah dihapus",
}


def temukan() -> list:
    """[{id, jenis, tx, saran}] saran = dict perubahan otomatis (kosong bila tidak ada perbaikan otomatis)."""
    hasil = []
    barang = [(b, _norm(b["nama"])) for b in D["barang"] if len(_norm(b["nama"])) >= 4]
    for t in D["transaksi"]:
        if t["jenis"] == "transfer":
            continue
        b = barang_dari(t.get("barang"))
        if t.get("barang") and not b:
            hasil.append({"jenis": "rujukan", "tx": t, "saran": {"hapus": ["barang", "qty", "harga_satuan", "harga_normal"]}})
        if t.get("toko") and not toko_dari(t["toko"]):
            hasil.append({"jenis": "rujukan", "tx": t, "saran": {"hapus": ["toko"]}})
        if not b and t.get("catatan") and not t.get("grup"):
            n = _norm(t["catatan"])
            cocok = next((x for x, nb in sorted(barang, key=lambda y: -len(y[1])) if nb in n and (kat_dari(x["kategori"]) or {}).get("jenis") == t["jenis"]), None)
            if cocok:
                hasil.append({"jenis": "barang_hilang", "tx": t, "saran": {"set": {"barang": cocok["id"], "qty": 1.0, "harga_satuan": int(t["jumlah"])},
                                                                             "info": f"Pasang barang “{cocok['nama']}”"}})
        if b and t.get("kategori") != b["kategori"] and kat_dari(b["kategori"]) and not t.get("grup"):
            hasil.append({"jenis": "kategori_beda", "tx": t, "saran": {"set": {"kategori": b["kategori"]},
                                                                         "info": f"Ganti kategori ke {nama_kat(b['kategori'])}"}})
        if t.get("qty") and t.get("harga_satuan") and abs(round(float(t["qty"]) * int(t["harga_satuan"])) - int(t["jumlah"])) > 1 and not t.get("grup"):
            hasil.append({"jenis": "jumlah_beda", "tx": t, "saran": {"set": {"jumlah": int(round(float(t["qty"]) * int(t["harga_satuan"])))},
                                                                       "info": f"Jumlah jadi {int(round(float(t['qty']) * int(t['harga_satuan']))):,}".replace(",", ".")}})
    for i, m in enumerate(hasil):
        m["id"] = f"{m['jenis']}:{m['tx']['id']}:{i}"
    return hasil


def terapkan(m: dict):
    t, s = m["tx"], m["saran"]
    for k, v in s.get("set", {}).items():
        t[k] = v
    for k in s.get("hapus", []):
        t.pop(k, None)


def _perbaiki(ids: list, semua: list):
    n = 0
    for m in semua:
        if m["id"] in ids:
            terapkan(m)
            n += 1
    catat("ubah", f"Pemeriksa data: {n} transaksi diperbaiki")
    selesai_simpan(f"{n} masalah diperbaiki.")


def halaman_periksa():
    semua = temukan()
    st.caption("Mencari transaksi yang janggal. Perbaikan hanya mengubah data yang jelas salah; yang lain tetap kamu putuskan sendiri lewat Ubah di Daftar transaksi.")
    if not semua:
        st.success("Tidak ada masalah. Datamu bersih ")
        return
    c = {k: sum(1 for m in semua if m["jenis"] == k) for k in JENIS_MASALAH}
    st.markdown(" · ".join(f"**{n}** {JENIS_MASALAH[k].lower()}" for k, n in c.items() if n))
    ids_ok = [m["id"] for m in semua if m["saran"] and m["jenis"] in ("jumlah_beda", "rujukan")]  # tebakan lain diputuskan satu per satu
    st.button(f"Perbaiki yang pasti benar ({len(ids_ok)})", type="primary", key="pr_semua", disabled=not ids_ok, on_click=_perbaiki, args=(ids_ok, semua))
    jenis = st.selectbox("Tampilkan", ["semua"] + [k for k, n in c.items() if n], format_func=lambda k: "Semua masalah" if k == "semua" else JENIS_MASALAH[k], key="pr_jenis")
    for m in [x for x in semua if jenis in ("semua", x["jenis"])][:60]:
        t = m["tx"]
        with st.container(key=f"kartu_g_pr_{m['id']}"):
            st.markdown(f"**{JENIS_MASALAH[m['jenis']]}**")
            st.caption(f"{fmt_iso(t['tgl'])} · {ringkas_teks(t)}" + (f" · catatan: {t['catatan']}" if t.get("catatan") else ""))
            if m["saran"].get("info"):
                st.button(m["saran"]["info"], key=f"pr_{m['id']}_{versi()}", on_click=_perbaiki, args=([m["id"]], semua))
            elif m["saran"].get("hapus"):
                st.button("Kosongkan rujukan yang hilang", key=f"pr_{m['id']}_{versi()}", on_click=_perbaiki, args=([m["id"]], semua))
