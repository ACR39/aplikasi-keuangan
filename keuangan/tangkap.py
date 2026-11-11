"""Tangkap cepat: ketik satu kalimat ('es jeruk 8rb 2', 'gaji 5jt') lalu tebak jenis, barang, jumlah, kategori, dompet, dan toko."""
import re
from collections import Counter

import streamlit as st

from keuangan.bantu import (
    barang_dari, catat, dompet_aktif, f_dompet, f_kat, f_platform, kat_dari, kat_pertama, kategori_jenis, selesai_simpan, tambah_transaksi, versi,
)
from keuangan.inti import D, hari_ini, rp
from keuangan.mutasi import _norm, usulan_kategori

KATA_MASUK = ("gaji", "terima", "dapat", "bonus", "masuk", "THR", "honor", "transferan", "pemasukan", "dibayar", "cashback")
_ANGKA = re.compile(r"(?i)(?:rp\.?\s*)?(\d+(?:[.,]\d+)*)\s*(juta|jt|ribu|rb|k)?\b")


def _nilai(angka: str, satuan: str) -> float:
    s = (satuan or "").lower()
    if s in ("jt", "juta"):
        return float(angka.replace(".", "").replace(",", ".")) * 1_000_000 if angka.count(",") + angka.count(".") <= 1 and not re.fullmatch(r"\d{1,3}(\.\d{3})+", angka) \
            else float(angka.replace(".", "").replace(",", ".")) * 1_000_000
    if s in ("rb", "ribu", "k"):
        return float(angka.replace(",", ".")) * 1000 if re.fullmatch(r"\d+([.,]\d)?", angka) else float(angka.replace(".", "").replace(",", ".")) * 1000
    return float(angka.replace(".", "").replace(",", "."))


def ambil_angka(teks: str):
    """Pisahkan teks jadi (nominal, banyaknya, sisa_kata). Nominal = angka terbesar bersatuan atau terbesar; banyaknya = angka kecil
    tanpa satuan uang ('2', '2x', 'x2', '2 porsi'). Mengembalikan nominal None bila tidak ada angka."""
    t = teks.strip()
    qty = None
    m = re.search(r"(?i)(?<![\w.])(\d+)\s*[x×](?!\w)|(?<![\w.])[x×]\s*(\d+)(?![\w.])", t)
    if m:
        qty = int(m.group(1) or m.group(2))
        t = (t[:m.start()] + " " + t[m.end():]).strip()
    kandidat = []
    for m in _ANGKA.finditer(t):
        try:
            v = _nilai(m.group(1), m.group(2))
        except ValueError:
            continue
        kandidat.append((v, bool(m.group(2)) or m.group(0).lower().startswith("rp") or v >= 1000, m.span()))
    uang = [k for k in kandidat if k[1]]
    kecil = [k for k in kandidat if not k[1] and k[0] < 1000]
    nominal = max(uang, key=lambda k: k[0]) if uang else None
    if qty is None and kecil and nominal:
        qty = int(kecil[0][0]) if float(kecil[0][0]).is_integer() and kecil[0][0] >= 1 else None
        if qty:
            t = t[:kecil[0][2][0]] + " " + t[kecil[0][2][1]:]
    elif qty is None and kecil and not nominal:
        nominal = None
    if nominal:
        a, b = nominal[2]
        # posisi sudah bergeser bila ada penghapusan sebelumnya, jadi hapus lewat pencarian ulang
        t = re.sub(re.escape(teks[a:b]) if teks[a:b] in t else r"$^", " ", t, count=1)
    return (int(round(nominal[0])) if nominal else None), qty, re.sub(r"\s+", " ", t).strip()


def tebak(teks: str) -> dict | None:
    """Hasil tebakan untuk satu kalimat, atau None bila kosong. Kunci: jenis, jumlah, qty, harga_satuan, barang, kategori, dompet, toko, catatan."""
    asli = teks.strip()
    if not asli:
        return None
    nominal, qty, sisa = ambil_angka(asli)
    n = _norm(sisa)
    jenis = "masuk" if any(w.lower() in n.split() for w in KATA_MASUK) or asli.startswith("+") else "keluar"
    # barang: nama terpanjang yang termuat di kalimat
    cocok = None
    for b in sorted(D["barang"], key=lambda b: -len(b["nama"])):
        nb = _norm(b["nama"])
        if nb and (nb in n or (len(n) >= 4 and n in nb)) and (kat_dari(b["kategori"]) or {}).get("jenis") == jenis:
            cocok = b
            break
    toko = ""
    for x in sorted(D["toko"], key=lambda x: -len(x["nama"])):
        if _norm(x["nama"]) and _norm(x["nama"]) in n:
            toko = x["id"]
            break
    platform = ""
    if jenis == "keluar":
        for p in sorted(D["platform"], key=lambda p: -len(p["nama"])):
            dasar = _norm(re.sub(r"\(.*?\)", "", p["nama"]))
            if not dasar or dasar == "lainnya":
                continue
            pola = r"\s*".join(map(re.escape, dasar.split()))
            if re.search(rf"(?<![a-z]){pola}(?![a-z])", n):
                platform = p["id"]
                sisa = re.sub(rf"(?i)\b(?:pakai|pake|via|lewat)?\s*(?<![a-z]){pola}(?![a-z])", " ", sisa).strip()
                break
    dompet = ""
    for d in dompet_aktif():
        if _norm(d["nama"]) and _norm(d["nama"]) in n.split() or _norm(d["nama"]) in n and len(_norm(d["nama"])) >= 3:
            dompet = d["id"]
            break
    if not dompet:
        pakai = Counter(t["dompet"] for t in D["transaksi"][-30:] if t["jenis"] == jenis)
        dompet = pakai.most_common(1)[0][0] if pakai else (dompet_aktif()[0]["id"] if dompet_aktif() else "")
    qty_ = qty or 1
    ids_k = [k["id"] for k in kategori_jenis(jenis)]
    if cocok:
        hs = nominal if nominal else int(cocok.get("harga") or 0)
        kat = cocok["kategori"]
        if toko == "":
            tk = Counter(t.get("toko") for t in D["transaksi"] if t.get("barang") == cocok["id"] and t.get("toko"))
            toko = tk.most_common(1)[0][0] if tk else ""
        catatan = ""
    else:
        # tanpa barang: nominal tanpa 'banyaknya' = total; dengan banyaknya = harga satuan
        hs = nominal or 0
        kat = usulan_kategori(sisa, jenis) or kat_pertama(jenis, "k_lain") or ""
        catatan = sisa
    if kat not in ids_k:
        kat = ids_k[0] if ids_k else ""
    return {"jenis": jenis, "jumlah": int(round(hs * qty_)), "qty": qty_, "harga_satuan": int(hs), "barang": cocok["id"] if cocok else "",
            "kategori": kat, "dompet": dompet, "toko": toko, "platform": platform, "catatan": catatan}


def _simpan(h: dict, kat: str, dompet: str, platform: str = ""):
    kait = {}
    if h["barang"] or h["qty"] != 1:
        kait = {"qty": float(h["qty"]), "harga_satuan": h["harga_satuan"]}
        if h["barang"]:
            kait["barang"] = h["barang"]
    t = tambah_transaksi(h["jenis"], hari_ini(), h["jumlah"], dompet, kat, h["catatan"], toko=h["toko"], platform=platform, **kait)
    catat("tambah", f"Tangkap cepat: {t['jenis']} {rp(t['jumlah'])}")
    selesai_simpan(f"Tercatat: {'pengeluaran' if h['jenis'] == 'keluar' else 'pemasukan'} {rp(h['jumlah'])}"
                   + (f" ({barang_dari(h['barang'])['nama']} × {h['qty']})" if h["barang"] else ""))


def panel_tangkap():
    """Kotak ketik cepat di atas form catat. Tanggal selalu hari ini; ubah lewat form lengkap bila perlu."""
    with st.expander("⚡ Tangkap cepat", expanded=False):
        st.caption("Ketik satu kalimat, contoh: **es jeruk 8rb 2**, **bensin 30rb**, **gaji 5jt**, **nasi goreng 25rb gofood**. Barang, kategori, dompet, toko, dan platform ditebak dari kebiasaanmu; "
                   "periksa dulu sebelum menyimpan. Dengan banyaknya, nominal dihitung per satuan.")
        teks = st.text_input("Catat apa?", key=f"tc_teks_{versi()}", placeholder="es jeruk 8rb 2")
        h = tebak(teks)
        if not h:
            return
        from keuangan.ai_fitur import tombol_tangkap
        h_ai = tombol_tangkap(teks.strip(), h, f"{versi()}_{teks.strip()}")
        if h_ai:
            h = h_ai
            st.caption("🤖 Hasil tebakan AI. Periksa dulu sebelum menyimpan.")
        sfx = "_ai" if h_ai else ""
        if not h["jumlah"]:
            st.warning("Belum ada nominal. Tambahkan angka, misalnya 8rb atau 25000.")
            return
        ids = [k["id"] for k in kategori_jenis(h["jenis"])]
        c1, c2 = st.columns(2)
        kat = c1.selectbox("Kategori", ids, index=ids.index(h["kategori"]) if h["kategori"] in ids else 0, format_func=f_kat(), key=f"tc_kat_{versi()}_{teks}{sfx}")
        dom_ids = [d["id"] for d in dompet_aktif()]
        dom = c2.selectbox("Dompet", dom_ids, index=dom_ids.index(h["dompet"]) if h["dompet"] in dom_ids else 0, format_func=f_dompet(), key=f"tc_dom_{versi()}_{teks}{sfx}")
        plat = ""
        if h["jenis"] == "keluar" and D["platform"]:
            pops = [""] + [p["id"] for p in D["platform"]]
            plat = st.selectbox("Beli online lewat (opsional)", pops, index=pops.index(h.get("platform") or "") if (h.get("platform") or "") in pops else 0,
                                format_func=f_platform(), key=f"tc_pl_{versi()}_{teks}{sfx}")
        nama = barang_dari(h["barang"])["nama"] if h["barang"] else (h["catatan"] or "tanpa catatan")
        st.markdown(f"**{'Pengeluaran' if h['jenis'] == 'keluar' else 'Pemasukan'} {rp(h['jumlah'])}** · {nama}"
                    + (f" · {h['qty']} × {rp(h['harga_satuan'])}" if h["qty"] != 1 else ""))
        if st.button("Simpan", type="primary", key=f"tc_simpan_{versi()}"):
            _simpan(h, kat, dom, plat)
