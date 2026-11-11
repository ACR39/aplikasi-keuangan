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


def _buka_transaksi(q: str):
    pindah_halaman("Daftar transaksi")
    st.session_state["tr_q"] = q


def halaman_cari():
    q = st.text_input("Cari apa saja", key="cari_q", placeholder="Barang, toko, catatan, nama orang, atau jumlah").strip()
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
