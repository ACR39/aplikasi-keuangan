"""Bagi tagihan (patungan): satu pembayaran, bagian tiap orang jadi piutang, bagian saya jadi pengeluaran."""
import streamlit as st

from keuangan.bantu import (
    atur, catat, dompet_aktif, f_dompet, f_toko, kat_pertama, nama_dompet, pilih_kategori, selesai_simpan, tambah_transaksi, versi,
)
from keuangan.inti import D, TGL_MAX, TGL_MIN, baru_id, hari_ini, rp


def hitung_bagian(total: int, orang: list, rata: bool, manual: dict | None = None):
    """Kembalikan (bagian_saya, {nama: bagian}). Dibagi rata: sisa pembulatan ditanggung saya.
    Manual: bagian saya = total dikurangi bagian semua orang (tidak boleh negatif)."""
    total, n = int(total), len(orang)
    if rata:
        tiap = total // (n + 1)
        return total - tiap * n, {o: tiap for o in orang}
    bagian = {o: int((manual or {}).get(o, 0) or 0) for o in orang}
    return total - sum(bagian.values()), bagian


def simpan_patungan(tgl, total, dompet, kategori, catatan, toko, orang_bagian: dict, bagian_saya: int, waktu: str = ""):
    """Catat: pengeluaran bagian saya (kategori pilihan) + pengeluaran per orang sebagai piutang. Uang keluar dompet = total."""
    grup = baru_id()
    if bagian_saya > 0:
        tambah_transaksi("keluar", tgl, bagian_saya, dompet, kategori, (catatan + " (bagian saya)").strip(), toko=toko, waktu=waktu, patungan=grup)
    for nama, v in orang_bagian.items():
        if v <= 0:
            continue
        u = {"id": baru_id(), "arah": "piutang", "orang": nama, "jumlah": int(v), "tgl": tgl.isoformat(),
             "tenggat": "", "catatan": f"Patungan: {catatan}".strip(": "), "bayar": [], "patungan": grup}
        D["utang"].append(u)
        tambah_transaksi("keluar", tgl, v, dompet, kat_pertama("keluar", "k_bayar_utang"), f"Talangi {nama}: {catatan}".strip(": "),
                         utang=u["id"], patungan=grup)
    return grup


def form_patungan():
    dompet = [d["id"] for d in dompet_aktif()]
    if not dompet:
        st.info("Tambahkan dompet dulu di Pengaturan > Data master > Dompet.")
        return
    k = f"pt_{versi()}"
    st.caption("Kamu membayar semuanya, teman membayar bagiannya nanti. Bagianmu jadi pengeluaran; bagian teman jadi piutang "
               "yang bisa dilunasi di Utang-piutang.")
    kat = pilih_kategori(k, "keluar")
    with st.form(f"f_{k}", clear_on_submit=False):
        c1, c2 = st.columns(2)
        total = c1.number_input("Total tagihan (Rp)", min_value=0, step=10000, value=0)
        tgl = c2.date_input("Tanggal", value=hari_ini(), min_value=TGL_MIN, max_value=TGL_MAX, format="DD/MM/YYYY")
        c3, c4 = st.columns(2)
        dom = c3.selectbox("Dibayar dari dompet", dompet, format_func=f_dompet())
        toko = c4.selectbox("Toko, opsional", [""] + [x["id"] for x in D["toko"]], format_func=f_toko({"": "-"}))
        catatan = st.text_input("Catatan", placeholder="Contoh: Makan malam bareng")
        nama = st.text_area("Nama teman (satu per baris)", placeholder="Budi\nSiti")
        cara = st.radio("Pembagian", ["Dibagi rata (termasuk saya)", "Atur sendiri"], horizontal=True)
        manual_txt = st.text_area("Kalau diatur sendiri: tulis 'Nama: jumlah' per baris", placeholder="Budi: 50000\nSiti: 30000")
        if st.form_submit_button("Simpan patungan", type="primary"):
            orang = []
            for x in nama.splitlines():
                if x.strip() and x.strip() not in orang:
                    orang.append(x.strip())
            manual = {}
            for baris in manual_txt.splitlines():
                if ":" in baris:
                    n_, _, v = baris.partition(":")
                    try:
                        manual[n_.strip()] = int("".join(c for c in v if c.isdigit()) or 0)
                    except ValueError:
                        pass
            rata = cara.startswith("Dibagi")
            if not orang or total <= 0:
                st.error("Isi total tagihan dan minimal satu nama teman.")
                return
            saya, bagian = hitung_bagian(total, orang, rata, manual if not rata else None)
            if saya < 0:
                st.error(f"Jumlah bagian teman melebihi total ({rp(sum(bagian.values()))} dari {rp(total)}).")
                return
            simpan_patungan(tgl, total, dom, kat, catatan, toko, bagian, saya)
            catat("tambah", f"Patungan {rp(total)}: {', '.join(orang)} (bagian saya {rp(saya)})")
            selesai_simpan(f"Patungan dicatat. Bagianmu {rp(saya)}; " + ", ".join(f"{o} {rp(v)}" for o, v in bagian.items()) + " masuk piutang.")
