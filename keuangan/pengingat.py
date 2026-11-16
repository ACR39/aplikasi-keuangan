"""Dua peringatan di Perlu perhatian: belum mencatat transaksi, dan kategori yang bulan ini lebih boros dari biasanya."""
from datetime import date

from keuangan.bantu import akar, e, nama_kat
from keuangan.inti import D, hari_ini, rp, sekarang


def _bulan_lalu(h: date, n: int) -> str:
    i = h.year * 12 + h.month - 1 - n
    return f"{i // 12}-{i % 12 + 1:02d}"


def baris_belum_mencatat() -> list:
    """Satu kalimat bila sudah 2 hari atau lebih tanpa transaksi, atau malam ini belum ada catatan hari ini."""
    h = hari_ini()
    tgl = [t["tgl"] for t in D["transaksi"] if t["tgl"] <= h.isoformat()]
    if not tgl:
        return []
    terakhir = date.fromisoformat(max(tgl))
    jeda = (h - terakhir).days
    if jeda >= 2:
        return [f"Sudah {jeda} hari belum ada transaksi yang dicatat (terakhir {terakhir.strftime('%d/%m/%Y')}). Catat yang terlewat supaya saldo tetap cocok."]
    if jeda == 1 and sekarang().hour >= 18:
        return ["Hari ini belum ada transaksi yang dicatat."]
    return []


def kategori_boros(h: date | None = None, batas_persen: int = 30, minimal: int = 50000) -> list:
    """[(id kategori utama, bulan ini, rata-rata 3 bulan lalu pada tanggal yang sama, persen naik)], terbesar dulu.
    Hanya kategori yang naik minimal `batas_persen` persen dan `minimal` rupiah, dan punya data di minimal 2 dari 3 bulan lalu."""
    h = h or hari_ini()
    ym = h.strftime("%Y-%m")
    lalu = [_bulan_lalu(h, n) for n in (1, 2, 3)]
    sekarang_k: dict = {}
    sebelum: dict = {b: {} for b in lalu}
    for t in D["transaksi"]:
        if t["jenis"] != "keluar" or not t.get("kategori"):
            continue
        bln = t["tgl"][:7]
        if bln != ym and bln not in sebelum:
            continue
        if int(t["tgl"][8:10]) > h.day:
            continue
        k = akar(t["kategori"])
        tujuan = sekarang_k if bln == ym else sebelum[bln]
        tujuan[k] = tujuan.get(k, 0) + int(t["jumlah"])
    hasil = []
    for k, v in sekarang_k.items():
        nilai = [sebelum[b].get(k, 0) for b in lalu]
        ada = [x for x in nilai if x]
        if len(ada) < 2:
            continue
        rata = sum(nilai) / 3
        if rata and v - rata >= minimal and v >= rata * (1 + batas_persen / 100):
            hasil.append((k, v, round(rata), round((v - rata) / rata * 100)))
    return sorted(hasil, key=lambda x: -(x[1] - x[2]))


def baris_boros(maks: int = 3) -> list:
    return [f'<b>{e(nama_kat(k))}</b> bulan ini {rp(v)} sampai hari ini, {p}% di atas rata-rata 3 bulan terakhir ({rp(r)} pada tanggal yang sama)'
            for k, v, r, p in kategori_boros()[:maks]]


def baris_perhatian() -> list:
    return baris_belum_mencatat() + baris_boros()
