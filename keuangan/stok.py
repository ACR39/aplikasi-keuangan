"""Pengingat stok habis: dari kebiasaan beli sebuah barang, perkirakan kapan waktunya beli lagi."""
from datetime import date

import streamlit as st

from keuangan.bantu import atur, catat, e, selesai_simpan, transaksi_barang
from keuangan.inti import D, hanya_lihat, hari_ini, rp


def _median(x: list):
    x = sorted(x)
    n = len(x)
    return x[n // 2] if n % 2 else (x[n // 2 - 1] + x[n // 2]) / 2


def kebiasaan(b: dict):
    """Pola beli satu barang, atau None bila datanya belum cukup (minimal 3 hari beli berbeda).
    {'tiap': hari antar pembelian (median), 'terakhir': tanggal, 'sisa': hari sampai perkiraan beli lagi (negatif = lewat), 'qty'}"""
    per_hari = {}
    for t in transaksi_barang(b["id"]):
        if t["jenis"] == "keluar":
            per_hari[t["tgl"]] = per_hari.get(t["tgl"], 0) + float(t.get("qty") or 1)
    tgl = sorted(per_hari)
    if len(tgl) < 3:
        return None
    ds = [date.fromisoformat(x) for x in tgl]
    jeda = [(b2 - a).days for a, b2 in zip(ds, ds[1:]) if (b2 - a).days > 0]
    if len(jeda) < 2:
        return None
    tiap = _median(jeda)
    if not 2 <= tiap <= 120:
        return None
    sisa = (ds[-1] - hari_ini()).days + round(tiap)
    qty = _median(list(per_hari.values()))
    return {"tiap": round(tiap), "terakhir": ds[-1], "sisa": sisa, "qty": qty if qty > 0 else 1.0}


def _sudah_di_daftar() -> set:
    return {it.get("barang") for l in D["belanja"] if not l.get("selesai") for it in l["item"] if it.get("barang") and not it.get("beli")}


def abaikan() -> list:
    return D.get("pengaturan", {}).get("stok_abaikan", [])


def waktunya_beli() -> list:
    """[(barang, kebiasaan)] yang kira-kira waktunya dibeli lagi (dalam 2 hari ke depan sampai terlewat 1,5 kali jedanya), paling mendesak dulu."""
    di_daftar, ab = _sudah_di_daftar(), set(abaikan())
    hasil = []
    for b in D["barang"]:
        if b["id"] in di_daftar or b["id"] in ab:
            continue
        k = kebiasaan(b)
        if k and -k["tiap"] * 1.5 <= k["sisa"] <= 2:
            hasil.append((b, k))
    return sorted(hasil, key=lambda z: z[1]["sisa"])


def teks_stok(b: dict, k: dict) -> str:
    lalu = (hari_ini() - k["terakhir"]).days
    status = "waktunya beli lagi" if k["sisa"] <= 0 else f"sekitar {k['sisa']} hari lagi"
    return f"biasanya dibeli tiap ±{k['tiap']} hari, terakhir {lalu} hari lalu: {status}"


def _tambah(l: dict, daftar: list):
    ada = {it.get("barang") for it in l["item"]}
    n = 0
    for b, k in daftar:
        if b["id"] in ada:
            continue
        qty = float(k["qty"])
        l["item"].append({"barang": b["id"], "nama": "", "qty": qty if qty != int(qty) else float(int(qty)), "harga": int(b.get("harga") or 0), "beli": False})
        n += 1
    if n:
        catat("belanja", f"Tambah {n} barang pengingat stok ke {l['nama']}")
        selesai_simpan(f"{n} barang ditambahkan ke daftar.", **{f"bl_ver_{l['id']}": st.session_state.get("bl_ver_" + l["id"], 0) + 1})


def _abaikan(id_: str):
    D["pengaturan"].setdefault("stok_abaikan", []).append(id_)
    catat("belanja", f"Matikan pengingat stok {next((b['nama'] for b in D['barang'] if b['id'] == id_), '')}")
    selesai_simpan("Pengingat untuk barang itu dimatikan.")


def panel_stok(l: dict):
    """Di halaman Daftar belanja: barang yang waktunya dibeli lagi, bisa langsung ditambahkan ke daftar terpilih."""
    daftar = waktunya_beli()
    ab = [b for b in D["barang"] if b["id"] in set(abaikan())]
    if not daftar and not ab:
        return
    with st.expander(f"🔔 Waktunya beli lagi ({len(daftar)})", expanded=bool(daftar)):
        if not daftar:
            st.caption("Belum ada yang perlu dibeli lagi menurut kebiasaan Anda.")
        else:
            st.caption("Perkiraan dari jarak antar pembelian sebelumnya (butuh minimal 3 kali beli di hari berbeda).")
        for b, k in daftar:
            with st.container(border=True, key=f"kartu_g_stok_{b['id']}"):
                st.markdown(f"**{e(b['nama'])}**")
                st.caption(f"{teks_stok(b, k)} · biasanya {k['qty']:g}" + (f" {b['satuan']}" if b.get("satuan") else ""))
                a, c = st.columns(2)
                a.button("Tambah ke daftar", key=f"stok_tambah_{b['id']}", type="primary", on_click=_tambah, args=(l, [(b, k)]))
                c.button("Jangan ingatkan", key=f"stok_abai_{b['id']}", on_click=_abaikan, args=(b["id"],))
        if len(daftar) > 1:
            st.button(f"Tambah semua ({len(daftar)})", key="stok_semua", on_click=_tambah, args=(l, daftar))
        if ab:
            st.caption("Pengingat dimatikan untuk: " + ", ".join(b["nama"] for b in ab))
            st.button("Aktifkan lagi semua", key="stok_aktif", on_click=lambda: (D["pengaturan"].update(stok_abaikan=[]), selesai_simpan("Pengingat diaktifkan lagi.")))


def baris_perhatian() -> list:
    """Teks HTML untuk kotak Perlu perhatian di Beranda."""
    d = waktunya_beli()
    baris = [f'🛒 <b>{e(b["nama"])}</b>: {e(teks_stok(b, k))}' for b, k in d[:3]]
    if len(d) > 3:
        baris.append(f'🛒 dan {len(d) - 3} barang lain mungkin perlu dibeli lagi (lihat Daftar belanja)')
    return baris
