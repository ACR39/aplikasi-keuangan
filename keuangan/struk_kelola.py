"""Kelola struk yang sudah tersimpan: pisah atau pindah barang, gabung dua struk, tambah biaya online dan potongan."""
import streamlit as st

from keuangan.bantu import catat, e, nama_dompet, perbarui_harga_barang, ringkas_teks, selesai_simpan, teks_barang, teks_toko, versi, atur_kategori
from keuangan.daring import KAT_BIAYA, baris_biaya, pastikan_kategori_biaya
from keuangan.inti import D, baru_id, fmt_iso, rp
from keuangan.struk import simpan_struk, terapkan_potongan
from keuangan.tutup_buku import tolak

# isian yang dibagi seluruh barang dalam satu struk
BERSAMA = ("tgl", "waktu", "dompet", "toko", "lokasi", "platform", "struk", "foto_hash", "acara")


def anggota(g: str) -> list:
    return sorted([x for x in D["transaksi"] if x.get("grup") == g], key=lambda x: x.get("dibuat", ""))


def _label_barang(x: dict) -> str:
    return f"{teks_barang(x) or x.get('catatan') or 'Tanpa nama'} · {rp(x['jumlah'])}"


def _label_struk(isi: list) -> str:
    t = isi[0]
    return f"{fmt_iso(t['tgl'])}{' ' + t['waktu'] if t.get('waktu') else ''} · {teks_toko(t) or 'Tanpa toko'} · {len(isi)} barang · {rp(sum(x['jumlah'] for x in isi))}"


def struk_lain(g: str, batas: int = 60) -> dict:
    """{grup: [transaksi]} untuk struk lain yang bisa jadi tujuan, terbaru dulu."""
    per = {}
    for t in D["transaksi"]:
        if t.get("grup") and t["grup"] != g and t["jenis"] == "keluar":
            per.setdefault(t["grup"], []).append(t)
    urut = sorted(per.items(), key=lambda kv: (kv[1][0]["tgl"], kv[1][0].get("waktu", "")), reverse=True)
    return dict(urut[:batas])


def pindahkan(ids: set, tujuan: str, contoh: dict) -> int:
    """Pindahkan transaksi berid ids ke struk `tujuan` (grup). Isian bersama diambil dari `contoh`. Kembalikan jumlah yang dipindah."""
    n = 0
    for t in D["transaksi"]:
        if t["id"] in ids:
            t["grup"] = tujuan
            for kk in BERSAMA:
                if contoh.get(kk):
                    t[kk] = contoh[kk]
                else:
                    t.pop(kk, None)
            n += 1
    return n


def terapkan_potongan_struk(g: str, potongan: int) -> int:
    """Bagi potongan ke barang (bukan biaya online) dalam struk g. Kembalikan jumlah yang benar-benar dipotong."""
    kat_biaya = {KAT_BIAYA} | {k["id"] for k in D["kategori"] if k.get("induk") == KAT_BIAYA}
    ts = [x for x in anggota(g) if x.get("kategori") not in kat_biaya and x["jumlah"] > 0]  # barang gratis tidak ikut dipotong
    baris = [{"qty": float(x.get("qty") or 1), "harga": float(x["jumlah"]) / float(x.get("qty") or 1), "total": int(x["jumlah"]),
              "normal": int(x.get("harga_normal") or 0)} for x in ts]
    baru = terapkan_potongan(baris, int(potongan))
    sebelum = sum(x["jumlah"] for x in ts)
    for x, b in zip(ts, baru):
        x["jumlah"] = int(b["total"])
        if x.get("barang"):
            x["harga_satuan"] = int(round(b["harga"]))
            if b["normal"]:
                x["harga_normal"] = int(b["normal"])
            else:
                x.pop("harga_normal", None)
    for bid in {x["barang"] for x in ts if x.get("barang")}:
        perbarui_harga_barang(bid)
    return sebelum - sum(x["jumlah"] for x in ts)


def panel_kelola(g: str, isi: list):
    """Panel 'Kelola struk' di kartu struk."""
    t0 = isi[0]
    with st.expander("🧰 Kelola struk: pisah, gabung, biaya, potongan"):
        tab1, tab2, tab3 = st.tabs(["Pisah atau pindah", "Gabung struk", "Biaya dan potongan"])
        with tab1:
            st.caption("Pilih barang yang salah masuk struk ini, lalu pindahkan ke struk baru atau struk lain. Barang yang pindah ikut tanggal, jam, toko, dompet, dan foto struk tujuan.")
            pilih = {x["id"]: _label_barang(x) for x in isi}
            ids = st.multiselect("Barang yang dipindah", list(pilih), format_func=pilih.get, key=f"kl_pilih_{g}_{versi()}")
            lain = struk_lain(g)
            tujuan = st.selectbox("Pindah ke", ["__baru__"] + list(lain), key=f"kl_tuj_{g}_{versi()}",
                                  format_func=lambda i: "➕ Struk baru (pisah)" if i == "__baru__" else _label_struk(lain[i]))
            baru = tujuan == "__baru__"
            if baru and len(ids) >= len(isi):
                st.caption("Untuk struk baru, sisakan minimal satu barang di struk ini.")
            if not baru and ids:
                st.caption(f"Dompet barang yang pindah menjadi {nama_dompet(lain[tujuan][0]['dompet'])} mengikuti struk tujuan.")
            if st.button("Pindahkan", key=f"kl_pindah_{g}_{versi()}", type="primary", disabled=not ids or (baru and len(ids) >= len(isi))):
                contoh = t0 if baru else lain[tujuan][0]
                if tolak(t0["tgl"], contoh["tgl"]):
                    return
                tg = baru_id() if baru else tujuan
                n = pindahkan(set(ids), tg, contoh)
                catat("ubah", f"Pindah {n} barang {'ke struk baru' if baru else 'ke struk ' + (teks_toko(contoh) or '')} dari struk {teks_toko(t0) or ''}".strip())
                selesai_simpan(f"{n} barang dipindah" + (" ke struk baru." if baru else "."))
        with tab2:
            lain = struk_lain(g)
            if not lain:
                st.caption("Belum ada struk lain untuk digabung.")
            else:
                st.caption("Seluruh barang struk yang dipilih masuk ke struk ini dan mengikuti tanggal, jam, toko, dompet, dan fotonya.")
                dari = st.selectbox("Gabungkan struk ini dengan", list(lain), key=f"kl_gab_{g}_{versi()}", format_func=lambda i: _label_struk(lain[i]))
                if st.button("Gabungkan ke struk ini", key=f"kl_gabok_{g}_{versi()}", type="primary"):
                    if tolak(t0["tgl"], lain[dari][0]["tgl"]):
                        return
                    n = pindahkan({x["id"] for x in anggota(dari)}, g, t0)
                    catat("ubah", f"Gabung struk {n} barang ke struk {teks_toko(t0) or ''}".strip())
                    selesai_simpan(f"Struk digabung: {n} barang masuk ke struk ini.")
        with tab3:
            st.markdown("**Biaya pesanan online**")
            st.caption("Ditambah sebagai baris sendiri (kategori Biaya pesan online). Kosongkan yang tidak ada.")
            b1, b2 = st.columns(2)
            ong = b1.number_input("Ongkir (Rp)", min_value=0, step=500, key=f"kl_ong_{g}_{versi()}")
            lay = b2.number_input("Biaya layanan / admin (Rp)", min_value=0, step=500, key=f"kl_lay_{g}_{versi()}")
            b3, b4 = st.columns(2)
            kms = b3.number_input("Biaya pengemasan (Rp)", min_value=0, step=500, key=f"kl_kms_{g}_{versi()}")
            rst = b4.number_input("Biaya tambahan resto (Rp)", min_value=0, step=500, key=f"kl_rst_{g}_{versi()}")
            b5, b6 = st.columns(2)
            asu = b5.number_input("Asuransi (Rp)", min_value=0, step=500, key=f"kl_asu_{g}_{versi()}")
            lain_b = b6.number_input("Biaya lain (Rp)", min_value=0, step=500, key=f"kl_lainb_{g}_{versi()}")
            dso = st.number_input("Diskon ongkir (Rp)", min_value=0, step=500, key=f"kl_dso_{g}_{versi()}",
                                  help="Mengurangi ongkir yang diisi di atas, tidak mengurangi harga barang.")
            baris = baris_biaya(ong, lay, asu, lain_b, dso, kms, rst)
            if baris and st.button(f"Tambahkan biaya {rp(sum(x['harga'] for x in baris))}", key=f"kl_biaya_{g}_{versi()}", type="primary"):
                if tolak(t0["tgl"]):
                    return
                pastikan_kategori_biaya()
                simpan_struk(baris, t0["tgl"], t0.get("waktu", ""), t0["dompet"], t0.get("toko", ""), t0.get("lokasi", ""), t0.get("struk", ""),
                             foto_hash=t0.get("foto_hash", ""), platform=t0.get("platform", ""), grup=g, acara=t0.get("acara", ""))
                catat("tambah", f"Tambah {len(baris)} biaya {rp(sum(x['harga'] for x in baris))} ke struk {teks_toko(t0) or ''}".strip())
                selesai_simpan("Biaya ditambahkan ke struk.")
            st.divider()
            st.markdown("**Potongan seluruh struk (voucher atau diskon total)**")
            st.caption("Dibagi ke harga tiap barang sebanding nilainya (biaya online tidak dipotong), lalu harga sebelumnya tersimpan sebagai harga normal. "
                       "Mengubah harga barang yang sudah tercatat, jadi cek dulu angkanya.")
            pot = st.number_input("Potongan (Rp)", min_value=0, step=500, key=f"kl_pot_{g}_{versi()}")
            yakin = st.checkbox("Saya paham harga barang di struk ini akan berubah", key=f"kl_potyakin_{g}_{versi()}")
            if st.button("Terapkan potongan", key=f"kl_potok_{g}_{versi()}", disabled=not pot or not yakin):
                if tolak(t0["tgl"]):
                    return
                n = terapkan_potongan_struk(g, int(pot))
                catat("ubah", f"Potongan {rp(n)} dibagi ke struk {teks_toko(t0) or ''}".strip())
                selesai_simpan(f"Potongan {rp(n)} diterapkan ke barang di struk ini.")
