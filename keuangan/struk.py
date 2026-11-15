"""Satu struk, banyak barang. Dipakai oleh Catat transaksi (mode struk) dan Daftar belanja.

Satu struk disimpan sebagai beberapa transaksi pengeluaran biasa yang berbagi `grup`, tanggal, waktu, toko,
lokasi, dompet, dan foto struk. Jadi laporan per kategori, barang, dan toko tetap bekerja tanpa perubahan.
"""
import pandas as pd
import streamlit as st

from keuangan.bantu import atur_kategori, akar, anak_dari, pilih_kategori, kat_dari, nama_kat, perbarui_harga_barang, tambah_transaksi, transaksi_barang, toko_dari, barang_dari
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


def bandingkan_toko(items: list) -> list:
    """Untuk tiap toko yang punya riwayat harga barang di daftar, hitung perkiraan total belanja di toko itu.
    Barang yang harganya di toko itu belum diketahui dihitung dengan perkiraan harga di daftar (sama di semua toko, jadi adil).
    Kembalikan list {toko, nama, total, ada, n} terurut dari yang paling murah; hanya toko yang mencakup minimal separuh barang berharga."""
    harga_toko = {}
    for it in items:
        b = it.get("barang")
        if b and b not in harga_toko:
            per = {}
            for tr in transaksi_barang(b):  # terbaru dulu
                if tr.get("toko") and tr.get("harga_satuan") and tr["toko"] not in per:
                    per[tr["toko"]] = int(tr["harga_satuan"])
            harga_toko[b] = per
    n = len(items)
    hasil = []
    for tk in {k for per in harga_toko.values() for k in per}:
        total = ada = 0
        for it in items:
            b = it.get("barang")
            h = harga_toko.get(b, {}).get(tk) if b else None
            if h:
                ada += 1
                total += round(it["qty"] * h)
            else:
                est = int(it.get("harga") or (barang_dari(b) or {}).get("harga") or 0) if b else int(it.get("harga") or 0)
                total += round(it["qty"] * est)
        if ada * 2 >= n:
            hasil.append({"toko": tk, "nama": (toko_dari(tk) or {}).get("nama", "?"), "total": total, "ada": ada, "n": n})
    return sorted(hasil, key=lambda x: (x["total"], -x["ada"]))


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
                                                          help="Kosongkan untuk memakai harga terakhir barang. Isi 0 untuk barang gratis (hadiah atau bonus promo)."),
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
        total = 0 if _kosong(r.get("Total bayar")) else int(round(float(r["Total bayar"])))
        isi_harga = None if _kosong(r.get("Harga satuan")) else int(round(float(r["Harga satuan"])))
        if total > 0 and qty > 0:
            isi_harga = max(1, int(round(total / qty)))
        gratis = isi_harga == 0  # 0 yang diketik sengaja = barang gratis (hadiah, bonus promo); kosong = pakai harga terakhir
        harga = isi_harga or 0
        if isi_harga is None and b:
            harga = int(barang_dari(b).get("harga", 0) or 0)
        if qty <= 0:
            salah.append(f"Baris {n}: banyaknya harus lebih dari 0.")
        elif harga <= 0 and not gratis:
            salah.append(f"Baris {n}: isi harga satuan (isi 0 bila barang ini gratis).")
        else:
            normal = 0 if _kosong(r.get("Harga normal")) else int(round(float(r["Harga normal"])))
            baris.append({"barang": b, "kategori": kat, "ket": "" if _kosong(r.get("Keterangan")) else str(r["Keterangan"]).strip(),
                          "qty": qty, "harga": harga, "normal": normal if normal > harga else 0, "gratis": gratis, "total": total if total > 0 else 0,
                          "asal": "" if _kosong(r.get("Asal")) else str(r["Asal"]).strip()})
    return baris, salah


def nilai_baris(x: dict) -> int:
    """Jumlah yang dibayar untuk satu baris. Harga paket (total) dipakai apa adanya, karena harga satuannya bisa tidak bulat."""
    return int(x["total"]) if x.get("total") else int(round(x["qty"] * x["harga"]))


def total_baris(baris: list) -> int:
    return sum(nilai_baris(x) for x in baris)


def terapkan_potongan(baris: list, potongan: int) -> list:
    """Bagi potongan seluruh struk (voucher, diskon total) ke tiap barang sebanding nilainya.
    Harga satuan jadi harga yang benar-benar dibayar; harga sebelum potongan disimpan sebagai harga normal."""
    total = total_baris(baris)
    potongan = int(potongan or 0)
    if potongan <= 0 or total <= 0:
        return baris
    berbayar = [i for i, x in enumerate(baris) if nilai_baris(x) > 0]  # barang gratis tidak ikut dipotong
    potongan = min(potongan, total - len(berbayar))  # tiap barang tetap berharga
    sisa = potongan
    hasil = []
    for i, x in enumerate(baris):
        nilai = nilai_baris(x)
        if nilai <= 0:
            hasil.append(x)
            continue
        bagian = sisa if i == berbayar[-1] else min(sisa, round(potongan * nilai / total))
        sisa -= bagian
        baru = max(1, round((nilai - bagian) / x["qty"]))
        awal = max(x["normal"], x["harga"])
        hasil.append({**x, "harga": baru, "normal": awal if awal > baru else 0, **({"total": max(1, nilai - bagian)} if x.get("total") else {})})
    return hasil


def terapkan_tambahan(baris: list, tambahan: int) -> list:
    """Bagi PPN/pajak/biaya tambahan ke tiap barang sebanding nilainya, jadi total barang = total struk.
    Harga satuan (dan harga normal, bila ada) naik dengan faktor yang sama."""
    total = total_baris(baris)
    tambahan = int(tambahan or 0)
    if tambahan <= 0 or total <= 0:
        return baris
    berbayar = [i for i, x in enumerate(baris) if nilai_baris(x) > 0]  # barang gratis tidak ikut ditambah
    sisa, hasil = tambahan, []
    for i, x in enumerate(baris):
        nilai = nilai_baris(x)
        if nilai <= 0:
            hasil.append(x)
            continue
        bagian = sisa if i == berbayar[-1] else round(tambahan * nilai / total)
        sisa -= bagian
        faktor = (nilai + bagian) / nilai if nilai else 1
        baru = round((nilai + bagian) / x["qty"])
        hasil.append({**x, "harga": baru, "normal": round(x["normal"] * faktor) if x["normal"] else 0,
                      **({"total": nilai + bagian} if x.get("total") else {})})
    return hasil


def baris_pajak(baris: list, pajak: int) -> dict:
    """Satu baris tersendiri 'PPN' berkategori sama dengan barang termahal di struk."""
    besar = max(baris, key=nilai_baris)
    return {"barang": "", "kategori": besar["kategori"], "ket": "PPN", "qty": 1, "harga": int(pajak), "normal": 0, "asal": ""}


def total_cepat(df: pd.DataFrame) -> int:
    """Total yang tampil langsung saat mengetik; baris bermasalah diabaikan."""
    baris, _ = baca_baris(df)
    return total_baris(baris)


# ---------------------------------------------------------------- simpan
def struk_serupa(tgl_iso: str, toko: str, total: int, foto_hash: str = ""):
    """Transaksi satu struk yang sudah tercatat dan mirip: foto sama, atau toko, tanggal, dan total sama. None bila tidak ada."""
    per = {}
    for t in D["transaksi"]:
        if t.get("grup"):
            per.setdefault(t["grup"], []).append(t)
    for ts in per.values():
        t0 = ts[0]
        jumlah = sum(int(x["jumlah"]) for x in ts)
        if (foto_hash and t0.get("foto_hash") == foto_hash) or (
                total > 0 and t0["tgl"] == tgl_iso and (t0.get("toko") or "") == (toko or "") and abs(jumlah - total) <= 5):
            return ts
    return None


def simpan_struk(baris: list, tgl, waktu: str, dompet: str, toko: str, lokasi: str, struk: str, catatan: str = "", foto_hash: str = "",
                 platform: str = "", grup: str = "", acara: str = "") -> list:
    """Buat satu transaksi pengeluaran per baris. Pemanggil yang menulis riwayat dan commit.
    `grup` diisi bila baris ditambahkan ke struk yang sudah ada; `acara` = id acara atau proyek."""
    grup = grup or baru_id()
    hasil = []
    for x in baris:
        qty = int(x["qty"]) if float(x["qty"]).is_integer() else x["qty"]
        hasil.append(tambah_transaksi(
            "keluar", tgl, nilai_baris(x), dompet, x["kategori"], x["ket"] or catatan,
            barang=x["barang"], qty=qty if x["barang"] else 0, harga_satuan=x["harga"] if x["barang"] else 0,
            harga_normal=x.get("normal", 0) if x["barang"] else 0,
            toko=toko, platform=platform, lokasi=lokasi, waktu=waktu, struk=struk, grup=grup, foto_hash=foto_hash, acara=acara, gratis=bool(x.get("gratis"))))
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
            kid = (barang_dari(id_b[r["Barang"]]) or {}).get("kategori", "") if r.get("Barang") in id_b else id_k.get(r.get("Kategori"), "")
            if kat_dari(kid):
                atur_kategori(f"{kunci}_{n}_c", kid)
            st.session_state[f"{kunci}_{n}_ket"] = r.get("Keterangan") if isinstance(r.get("Keterangan"), str) else ""
            st.session_state[f"{kunci}_{n}_qty"] = float(r["Banyaknya"]) if not _kosong(r.get("Banyaknya")) else 1.0
            st.session_state[f"{kunci}_{n}_gr"] = not _kosong(r.get("Harga satuan")) and int(r["Harga satuan"]) == 0 and _kosong(r.get("Total bayar"))
            st.session_state[f"{kunci}_{n}_hrg"] = int(r["Harga satuan"]) if not _kosong(r.get("Harga satuan")) else 0
            st.session_state[f"{kunci}_{n}_tot"] = int(r["Total bayar"]) if not _kosong(r.get("Total bayar")) else 0
            st.session_state[f"{kunci}_{n}_nrm"] = int(r["Harga normal"]) if not _kosong(r.get("Harga normal")) else 0
            st.session_state[f"{kunci}_{n}_raw"] = str(r["Asal"]) if not _kosong(r.get("Asal")) else ""
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
            if tetap:
                brg = st.selectbox("Barang", opsi_b, key=f"{k}_brg", disabled=bool(st.session_state.get(f"{k}_brg")),
                                   format_func=lambda i: i or "(pilih dari daftar barang)")
                kat = ket = ""
                if not brg:
                    kat = st.selectbox("Kategori (untuk barang di luar daftar)", opsi_k, key=f"{k}_kat",
                                       disabled=bool(st.session_state.get(f"{k}_kat")),
                                       format_func=lambda i: i or "(pilih kategori)")
                    ket = st.text_input("Nama / keterangan", key=f"{k}_ket", max_chars=60)
            else:
                efektif_k = pilih_kategori(f"{k}_c", "keluar", "", kosong=True)
                utama_k = efektif_k
                langsung = bool(efektif_k) and any(x["kategori"] == efektif_k for x in D["barang"])
                sub_ok = bool(efektif_k) and (not anak_dari(efektif_k) or langsung)
                if sub_ok:
                    opsi_f = [""] + [lab for lab, bid in id_b.items() if (barang_dari(bid) or {}).get("kategori") == efektif_k]
                    if st.session_state.get(f"{k}_brg") not in opsi_f:
                        st.session_state[f"{k}_brg"] = ""
                    brg = st.selectbox("Barang (opsional)", opsi_f, key=f"{k}_brg", format_func=lambda i: i or "(pilih dari daftar barang)",
                                       help="Hanya barang di kategori dan sub kategori yang dipilih.")
                else:
                    st.session_state[f"{k}_brg"] = ""
                    brg = ""
                    st.selectbox("Barang (opsional)", [""], key=f"{k}_brg_kosong", disabled=True,
                                 format_func=lambda i: "Isi kategori dan sub kategori dulu" if not utama_k else "Pilih sub kategori dulu")
                kat = ket = ""
                if not brg:
                    kat = lab_k.get(efektif_k, "") if efektif_k else ""
                    ket = st.text_input("Nama / keterangan", key=f"{k}_ket", max_chars=60)
            c1, c2 = st.columns(2)
            qty = c1.number_input("Banyaknya", min_value=0.0, step=1.0, format="%g", key=f"{k}_qty")
            gratis = st.checkbox("Gratis (hadiah atau bonus promo)", key=f"{k}_gr")
            hrg = c2.number_input("Harga satuan (Rp)", min_value=0, step=500, key=f"{k}_hrg", disabled=gratis)
            tot = st.number_input("Total bayar untuk barang ini (opsional)", min_value=0, step=500, key=f"{k}_tot", disabled=gratis,
                                  help="Untuk harga paket, misalnya beli 3 cuma Rp 5.000: isi banyaknya 3 dan total 5000. Menggantikan harga satuan.")
            if gratis:
                hrg = tot = 0
            nrm = st.number_input("Harga normal sebelum diskon (opsional)", min_value=0, step=500, key=f"{k}_nrm", disabled=gratis,
                                  help="Harga satuan normal tanpa promo. Harga satuan atau total di atas adalah yang dibayar.")
            b = barang_dari(id_b.get(brg)) if brg else None
            if tot and qty:
                hrg = max(1, round(tot / qty))
                st.caption(f"Harga paket: {rp(tot)} untuk {qty:g}, rata-rata {rp(hrg)} per satuan.")
            efektif = int(hrg) or (0 if gratis else int((b or {}).get("harga", 0) or 0))
            if b and not hrg and not gratis:
                st.caption(f"Harga kosong, memakai harga terakhir {rp(efektif)}.")
            if gratis:
                st.caption("Dicatat Rp 0, tetap masuk stok.")
            if b:
                from keuangan.bantu import harga_normal_barang
                hn_r = harga_normal_barang(b["id"])
                if hn_r:
                    st.caption(f"Harga normal biasanya {rp(hn_r)}.")
            if b and efektif:
                from keuangan.bantu import tampil_peringatan_harga
                tampil_peringatan_harga(b["id"], efektif)
            if nrm and efektif and nrm > efektif:
                st.caption(f"Diskon {round((nrm - efektif) / nrm * 100)}% (hemat {rp(nrm - efektif)} per satuan).")
            if efektif and qty:
                st.caption(f"Subtotal: {rp(int(tot) if tot else round(qty * efektif))}")
        baris.append({"Barang": brg or None, "Kategori": kat or None, "Keterangan": ket,
                      "Banyaknya": qty, "Harga satuan": 0 if gratis else (int(hrg) if hrg else None), "Harga normal": int(nrm) if nrm else None,
                      "Total bayar": int(tot) if tot else None,
                      "Asal": st.session_state.get(f"{k}_raw", "")})
    if hapus is not None:
        st.session_state[sk] = [i for i in ids if i != hapus]
        st.rerun()
    if not tetap and st.button("➕ Tambah barang", key=f"{kunci}_tambah"):
        st.session_state[f"{kunci}_{st.session_state[f'{kunci}_next']}_qty"] = 1.0
        st.session_state[sk] = ids + [st.session_state[f"{kunci}_next"]]
        st.session_state[f"{kunci}_next"] += 1
        st.rerun()
    df = pd.DataFrame(baris, columns=KOLOM + ["Harga normal", "Total bayar", "Asal"])
    for kol in ("Harga satuan", "Harga normal", "Total bayar"):
        df[kol] = df[kol].astype("Int64")
    return df
