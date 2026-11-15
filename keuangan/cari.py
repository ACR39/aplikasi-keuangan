"""Pencarian cepat satu kotak: transaksi, barang, toko, daftar belanja, utang-piutang, dan tagihan."""
import streamlit as st

from keuangan.bantu import (
    atur, barang_dari, e, kat_dari, kunci_urut, nama_dompet, nama_kat, nama_platform, pindah_halaman, ringkas_teks, teks_barang, teks_toko, toko_dari,
)
from keuangan.inti import D, fmt_iso, rp

MAKS = 8


def _cocok(q: str, *bagian) -> bool:
    return q in " ".join(str(b) for b in bagian if b).lower()


def cari(q: str) -> dict:
    """Hasil per kelompok untuk kata kunci q (huruf besar/kecil diabaikan; angka dicocokkan ke jumlah)."""
    q = q.strip().lower()
    if not q:
        return {}
    angka = "".join(c for c in q if c.isdigit())
    tx = [t for t in D["transaksi"]
          if _cocok(q, t.get("catatan"), nama_kat(t.get("kategori")) if t["jenis"] != "transfer" else "transfer", nama_dompet(t["dompet"]),
                    teks_barang(t), teks_toko(t), t.get("lokasi"), t["tgl"], nama_platform(t.get("platform")))
          or (len(angka) >= 3 and angka == str(t["jumlah"]))]
    return {
        "transaksi": sorted(tx, key=kunci_urut, reverse=True),
        "barang": [b for b in D["barang"] if _cocok(q, b["nama"], b.get("merek"), b.get("barcode"), nama_kat(b.get("kategori")), b.get("catatan"))],
        "toko": [x for x in D["toko"] if _cocok(q, x["nama"], x.get("jenis"), x.get("lokasi"), x.get("catatan"))],
        "belanja": [l for l in D["belanja"] if _cocok(q, l["nama"], *[i.get("nama") for i in l.get("item", [])])],
        "utang": [u for u in D["utang"] if _cocok(q, u["orang"], u.get("catatan"))],
        "tagihan": [t for t in D["tagihan"] if _cocok(q, t["nama"], t.get("catatan"))],
    }


def saring(q: str, f: dict) -> list:
    """Transaksi yang lolos filter lanjutan f (kunci opsional: dari, sampai, min, maks, jenis, kategori, dompet, toko) dan kata kunci q."""
    from keuangan.bantu import turunan
    q = q.strip().lower()
    kat = set()
    for k in f.get("kategori", []):
        kat |= turunan(k)
    hasil = []
    for t in D["transaksi"]:
        if f.get("dari") and t["tgl"] < f["dari"] or f.get("sampai") and t["tgl"] > f["sampai"]:
            continue
        j = int(t["jumlah"])
        if f.get("min") and j < f["min"] or f.get("maks") and j > f["maks"]:
            continue
        if f.get("jenis") and t["jenis"] not in f["jenis"]:
            continue
        if kat and t.get("kategori") not in kat:
            continue
        if f.get("dompet") and t["dompet"] not in f["dompet"] and t.get("ke") not in f["dompet"]:
            continue
        if f.get("toko") and t.get("toko") not in f["toko"]:
            continue
        if q and not _cocok(q, t.get("catatan"), nama_kat(t.get("kategori")) if t["jenis"] != "transfer" else "transfer", nama_dompet(t["dompet"]),
                            teks_barang(t), teks_toko(t), t.get("lokasi"), nama_platform(t.get("platform"))):
            continue
        hasil.append(t)
    return sorted(hasil, key=kunci_urut, reverse=True)


def _filter_lanjutan() -> dict:
    """Panel filter di bawah kotak cari; kembalikan dict filter yang aktif (kosong bila tidak ada)."""
    from keuangan.bantu import f_dompet, f_kat, f_toko
    f = {}
    with st.expander("Filter lanjutan", expanded=bool(st.session_state.get("cari_f_buka"))):
        c1, c2 = st.columns(2)
        rentang = c1.date_input("Rentang tanggal", value=(), format="DD/MM/YYYY", key="cari_f_tgl")
        if len(rentang) == 2:
            f["dari"], f["sampai"] = rentang[0].isoformat(), rentang[1].isoformat()
        elif len(rentang) == 1:
            f["dari"] = f["sampai"] = rentang[0].isoformat()
        jenis = c2.multiselect("Jenis", ["keluar", "masuk", "transfer"], format_func={"keluar": "Pengeluaran", "masuk": "Pemasukan", "transfer": "Transfer"}.get, key="cari_f_jenis")
        c3, c4 = st.columns(2)
        mn = c3.number_input("Jumlah minimal (Rp)", min_value=0, step=10000, value=0, key="cari_f_min")
        mx = c4.number_input("Jumlah maksimal (Rp, 0 = tanpa batas)", min_value=0, step=10000, value=0, key="cari_f_maks")
        kat = st.multiselect("Kategori (termasuk sub)", [k["id"] for k in D["kategori"] if not k.get("induk")], format_func=f_kat(), key="cari_f_kat")
        c5, c6 = st.columns(2)
        dom = c5.multiselect("Dompet", [d["id"] for d in D["dompet"]], format_func=f_dompet(), key="cari_f_dom")
        tk = c6.multiselect("Toko", [x["id"] for x in D["toko"]], format_func=f_toko(), key="cari_f_toko")
    for k, v in (("jenis", jenis), ("min", mn), ("maks", mx), ("kategori", kat), ("dompet", dom), ("toko", tk)):
        if v:
            f[k] = v
    return f


def _hasil_filter(q: str, f: dict):
    hasil = saring(q, f)
    masuk = sum(int(t["jumlah"]) for t in hasil if t["jenis"] == "masuk")
    keluar = sum(int(t["jumlah"]) for t in hasil if t["jenis"] == "keluar")
    st.markdown(f"**{len(hasil)} transaksi** · masuk {rp(masuk)} · keluar {rp(keluar)}")
    if not hasil:
        return
    with st.container(key="kartu_g_cari_filter"):
        for t in hasil[:50]:
            st.markdown(f'<div class="perhatian">{fmt_iso(t["tgl"])} · {e(ringkas_teks(t))}</div>', unsafe_allow_html=True)
        if len(hasil) > 50:
            st.caption(f"Menampilkan 50 pertama dari {len(hasil)}. Ubah massal di bawah mencakup semua hasil.")
    from keuangan.inti import hanya_lihat
    if not hanya_lihat():
        from keuangan.massal import panel_massal
        panel_massal(hasil)


def _buka_transaksi(q: str):
    pindah_halaman("Daftar transaksi")
    st.session_state["tr_q"] = q


def halaman_cari():
    q = st.text_input("Cari apa saja", key="cari_q", placeholder="Barang, toko, catatan, nama orang, atau jumlah").strip()
    f = _filter_lanjutan()
    if f:
        _hasil_filter(q, f)
        return
    if not q:
        st.caption("Ketik kata kunci. Pencarian mencakup transaksi, barang, toko, daftar belanja, utang-piutang, dan tagihan.")
        return
    h = cari(q)
    total = sum(len(v) for v in h.values())
    if not total:
        st.info("Tidak ada yang cocok.")
        return
    st.caption(f"{total} hasil untuk “{q}”")
    if h["transaksi"]:
        with st.container(key="kartu_g_cari_tx"):
            st.markdown(f"**Transaksi** · {len(h['transaksi'])}")
            for t in h["transaksi"][:MAKS]:
                st.markdown(f'<div class="perhatian">{fmt_iso(t["tgl"])} · {e(ringkas_teks(t))}</div>', unsafe_allow_html=True)
            if len(h["transaksi"]) > MAKS:
                st.button(f"Lihat semua {len(h['transaksi'])} di Daftar transaksi", key="cari_semua", on_click=_buka_transaksi, args=(q,))
    if h["barang"]:
        with st.container(key="kartu_g_cari_brg"):
            st.markdown(f"**Barang** · {len(h['barang'])}")
            for b in h["barang"][:MAKS]:
                st.markdown(f'<div class="perhatian"><b>{e(b["nama"])}</b> · {e(nama_kat(b.get("kategori")))}'
                            + (f' · harga terakhir {rp(b["harga"])}' if b.get("harga") else "") + '</div>', unsafe_allow_html=True)
    if h["toko"]:
        with st.container(key="kartu_g_cari_tk"):
            st.markdown(f"**Toko** · {len(h['toko'])}")
            for x in h["toko"][:MAKS]:
                st.markdown(f'<div class="perhatian"><b>{e(x["nama"])}</b>' + (f' · {e(x["lokasi"])}' if x.get("lokasi") else "") + '</div>', unsafe_allow_html=True)
    if h["belanja"]:
        with st.container(key="kartu_g_cari_bl"):
            st.markdown(f"**Daftar belanja** · {len(h['belanja'])}")
            for l in h["belanja"][:MAKS]:
                st.markdown(f'<div class="perhatian"><b>{e(l["nama"])}</b> · {len(l.get("item", []))} item</div>', unsafe_allow_html=True)
    if h["utang"]:
        with st.container(key="kartu_g_cari_ut"):
            st.markdown(f"**Utang-piutang** · {len(h['utang'])}")
            for u in h["utang"][:MAKS]:
                st.markdown(f'<div class="perhatian"><b>{e(u["orang"])}</b> · {"piutang" if u["arah"] == "piutang" else "utang"} {rp(u["jumlah"])}</div>', unsafe_allow_html=True)
    if h["tagihan"]:
        with st.container(key="kartu_g_cari_tg"):
            st.markdown(f"**Transaksi berulang** · {len(h['tagihan'])}")
            for t in h["tagihan"][:MAKS]:
                st.markdown(f'<div class="perhatian"><b>{e(t["nama"])}</b> · {rp(t["jumlah"])} · berikut {fmt_iso(t["berikut"])}</div>', unsafe_allow_html=True)
