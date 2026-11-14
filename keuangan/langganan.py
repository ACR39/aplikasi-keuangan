"""Deteksi pengeluaran rutin yang belum dijadwalkan (langganan terlupa) dan tawarkan jadikan transaksi berulang."""
import statistics
from datetime import date, timedelta

import streamlit as st

from keuangan.bantu import barang_dari, catat, e, kat_dari, nama_kat, selesai_simpan, toko_dari, versi
from keuangan.inti import D, baru_id, fmt_iso, hari_ini, rp
from keuangan.mutasi import _norm


def _kunci(t: dict) -> str:
    if t.get("barang"):
        return "b:" + t["barang"]
    n = _norm(t.get("catatan", ""))
    if n:
        return "c:" + n
    return "k:" + (t.get("kategori") or "") + "|" + (t.get("toko") or "")


def _nama(k: str, ts: list) -> str:
    if k.startswith("b:"):
        return (barang_dari(k[2:]) or {}).get("nama", "?")
    if k.startswith("c:"):
        return ts[-1].get("catatan", "").strip() or k[2:]
    t = ts[-1]
    return (toko_dari(t.get("toko")) or {}).get("nama") or nama_kat(t.get("kategori"))


def deteksi(h: date | None = None) -> list:
    """Kelompok pengeluaran berulang ~bulanan: minimal 3 bulan berbeda, selang 20-40 hari, jumlah mirip (±10%), terakhir <= 50 hari lalu.
    Kelompok yang sudah jadi transaksi berulang, diabaikan, atau berasal dari tagihan tidak ikut."""
    h = h or hari_ini()
    abaikan = set(D["pengaturan"].get("langganan_abaikan", []))
    terdaftar = {_norm(t["nama"]) for t in D["tagihan"]}
    grup = {}
    for t in D["transaksi"]:
        if t["jenis"] == "keluar" and not t.get("tagihan") and not t.get("grup") and not t.get("patungan") and not t.get("utang"):
            grup.setdefault(_kunci(t), []).append(t)
    hasil = []
    for k, ts in grup.items():
        ts.sort(key=lambda t: t["tgl"])
        if k in abaikan or len(ts) < 3:
            continue
        jml = [int(t["jumlah"]) for t in ts]
        med = statistics.median(jml)
        ts = [t for t in ts if med and abs(int(t["jumlah"]) - med) <= 0.1 * med]
        tgl = [date.fromisoformat(t["tgl"]) for t in ts]
        bulan = {(d.year, d.month) for d in tgl}
        if len(bulan) < 3:
            continue
        selang = [(b - a).days for a, b in zip(tgl, tgl[1:]) if (b - a).days > 3]
        if len(selang) < 2 or not all(20 <= s <= 40 for s in selang[-3:]) or (h - tgl[-1]).days > 50:
            continue
        nama = _nama(k, ts)
        if _norm(nama) in terdaftar:
            continue
        rata = int(round(statistics.median([int(t["jumlah"]) for t in ts])))
        hasil.append({"kunci": k, "nama": nama, "jumlah": rata, "kali": len(ts), "terakhir": tgl[-1],
                      "berikut": tgl[-1] + timedelta(days=round(statistics.median(selang))), "kategori": ts[-1].get("kategori", ""),
                      "dompet": ts[-1]["dompet"], "setahun": rata * 12, "henti": k in D["pengaturan"].get("langganan_henti", [])})
    return sorted(hasil, key=lambda x: -x["jumlah"])


def jumlah_belum_dijadwalkan() -> int:
    return len([x for x in deteksi() if not x["henti"]])


def _jadwalkan(x: dict):
    berikut = x["berikut"] if x["berikut"] >= hari_ini() else hari_ini()
    D["tagihan"].append({"id": baru_id(), "nama": x["nama"], "jumlah": x["jumlah"], "tiap": "bulanan", "berikut": berikut.isoformat(),
                         "kategori": x["kategori"], "dompet": x["dompet"], "catatan": "Dari deteksi pengeluaran rutin", "aktif": True,
                         "jenis": "keluar", "otomatis": False})
    catat("tagihan", f"Jadwalkan pengeluaran rutin {x['nama']} {rp(x['jumlah'])}")
    selesai_simpan(f"{x['nama']} dijadwalkan tiap bulan mulai {fmt_iso(berikut.isoformat())}.")


def _tandai(kunci: str, daftar: str, pesan: str):
    D["pengaturan"].setdefault(daftar, [])
    if kunci not in D["pengaturan"][daftar]:
        D["pengaturan"][daftar].append(kunci)
    selesai_simpan(pesan)


def panel_langganan():
    hasil = deteksi()
    with st.expander(f"Pengeluaran rutin yang belum dijadwalkan ({len(hasil)})", expanded=bool(hasil)):
        if not hasil:
            st.caption("Belum ada pola. Aplikasi mencari pengeluaran dengan jumlah mirip yang muncul tiap bulan, minimal 3 bulan berturut-turut.")
            return
        st.caption("Pengeluaran ini muncul tiap bulan dengan jumlah mirip. Jadikan transaksi berulang supaya jatuh temponya terpantau, "
                   "atau tandai kalau mau dihentikan.")
        for x in hasil:
            with st.container(key=f"kartu_g_lg_{x['kunci']}"):
                st.markdown(f"**{e(x['nama'])}** · {rp(x['jumlah'])} per bulan · {x['kali']} kali · terakhir {fmt_iso(x['terakhir'].isoformat())}"
                            f"{' · mau dihentikan' if x['henti'] else ''}")
                st.caption(f"Setahun sekitar {rp(x['setahun'])}. Perkiraan berikutnya {fmt_iso(x['berikut'].isoformat())}.")
                c1, c2, c3 = st.columns(3)
                c1.button("Jadwalkan", key=f"lg_j_{x['kunci']}_{versi()}", on_click=_jadwalkan, args=(x,), width="stretch")
                c2.button("Mau dihentikan" if not x["henti"] else "Batal tanda", key=f"lg_h_{x['kunci']}_{versi()}", width="stretch",
                          on_click=(_tandai if not x["henti"] else _batal_henti), args=(x["kunci"], "langganan_henti", "Ditandai mau dihentikan.") if not x["henti"] else (x["kunci"],))
                c3.button("Abaikan", key=f"lg_a_{x['kunci']}_{versi()}", on_click=_tandai, args=(x["kunci"], "langganan_abaikan", "Diabaikan."), width="stretch")


def _batal_henti(kunci: str):
    D["pengaturan"].get("langganan_henti", []) and kunci in D["pengaturan"]["langganan_henti"] and D["pengaturan"]["langganan_henti"].remove(kunci)
    selesai_simpan("Tanda dihapus.")
