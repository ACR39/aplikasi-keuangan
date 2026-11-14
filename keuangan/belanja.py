"""Daftar belanja: rencanakan barang, lihat toko termurah, centang saat membeli, lalu catat jadi satu struk."""
import pandas as pd
import streamlit as st

from keuangan.bantu import (
    atur, barang_dari, tampil_peringatan_harga, catat, dompet_aktif, e, f_dompet, f_toko, proses_foto, selesai_simpan, toko_dari, versi,
)
from keuangan.inti import D, TGL_MAX, TGL_MIN, baru_id, fmt_iso, hanya_lihat, hari_ini, rp, sekarang
from keuangan.stok import panel_stok
from keuangan.struk import (
    baca_baris, bandingkan_toko, editor_baris, editor_kartu, peta_barang, peta_kategori, ringkas_struk, simpan_struk, termurah, total_baris,
)


# ---------------------------------------------------------------- bantu
def _daftar_aktif() -> list:
    return [x for x in D["belanja"] if not x.get("selesai")]


def _nama_item(it: dict) -> str:
    b = barang_dari(it.get("barang"))
    return b["nama"] if b else (it.get("nama") or "(tanpa nama)")


def _tabel_item(l: dict) -> pd.DataFrame:
    _, lab = peta_barang()
    baris = []
    for it in l["item"]:
        b = barang_dari(it.get("barang"))
        tm = termurah(it["barang"]) if b else None
        baris.append({
            "Beli": bool(it.get("beli")), "Barang": lab.get(it.get("barang")), "Keterangan": it.get("nama", "") if not b else "",
            "Banyaknya": float(it.get("qty") or 1), "Perkiraan harga": int(it.get("harga") or (b or {}).get("harga") or 0),
            "Termurah": f"{tm[0]} · {rp(tm[1])}" if tm else "",
        })
    return pd.DataFrame(baris, columns=["Beli", "Barang", "Keterangan", "Banyaknya", "Perkiraan harga", "Termurah"]).astype(
        {"Beli": bool, "Banyaknya": float, "Perkiraan harga": "Int64"}) if baris else pd.DataFrame({
        "Beli": pd.Series([], dtype=bool), "Barang": pd.Series([], dtype=object), "Keterangan": pd.Series([], dtype=object),
        "Banyaknya": pd.Series([], dtype=float), "Perkiraan harga": pd.Series([], dtype="Int64"), "Termurah": pd.Series([], dtype=object)})


def _item_dari_tabel(df: pd.DataFrame) -> list:
    id_b, _ = peta_barang()
    hasil = []
    for r in df.to_dict("records"):
        b = id_b.get(r.get("Barang")) if isinstance(r.get("Barang"), str) else ""
        ket = r.get("Keterangan") if isinstance(r.get("Keterangan"), str) else ""
        if not b and not ket.strip():
            continue
        qty = r.get("Banyaknya")
        harga = r.get("Perkiraan harga")
        hasil.append({"barang": b, "nama": "" if b else ket.strip(),
                      "qty": 1.0 if pd.isna(qty) or qty <= 0 else float(qty),
                      "harga": 0 if pd.isna(harga) else int(harga), "beli": bool(r.get("Beli"))})
    return hasil


def _taksir(items: list):
    """(perkiraan total, total bila semua di toko termurah, jumlah barang bertermurah)."""
    biasa = murah = n = 0
    for it in items:
        b = barang_dari(it.get("barang"))
        h = int(it.get("harga") or (b or {}).get("harga") or 0)
        biasa += round(it["qty"] * h)
        tm = termurah(it["barang"]) if b else None
        if tm:
            murah += round(it["qty"] * min(tm[1], h or tm[1]))
            n += 1
        else:
            murah += round(it["qty"] * h)
    return biasa, murah, n


# ---------------------------------------------------------------- bagian halaman
def _buat_daftar():
    with st.form(f"f_bl_baru_{versi()}", clear_on_submit=False):
        c1, c2 = st.columns(2)
        nama = c1.text_input("Nama daftar", placeholder="Contoh: Belanja mingguan")
        tops = [""] + [x["id"] for x in sorted(D["toko"], key=lambda x: (not x.get("favorit"), x["nama"].lower()))]
        toko = c2.selectbox("Rencana toko, opsional", tops, format_func=f_toko())
        if st.form_submit_button("Buat daftar", type="primary"):
            if not nama.strip():
                st.error("Isi nama daftar.")
            else:
                d = {"id": baru_id(), "nama": nama.strip(), "toko": toko, "dibuat": hari_ini().isoformat(), "item": [], "riwayat": []}
                D["belanja"].append(d)
                catat("belanja", f"Buat daftar belanja {d['nama']}")
                selesai_simpan("Daftar dibuat.", bl_pilih=d["id"])


def _panel_selesai(l: dict):
    """Catat barang yang dicentang sebagai satu struk."""
    dibeli = [it for it in l["item"] if it.get("beli")]
    st.markdown("**Catat belanja yang sudah dibeli**")
    if not dibeli:
        st.info("Centang dulu barang yang sudah dibeli, lalu simpan.")
        st.button("Tutup", key=f"bl_tutup_{l['id']}", on_click=atur, args=(f"bl_selesai_{l['id']}", False))
        return
    _, lab_b = peta_barang()
    _, lab_k = peta_kategori()
    awal = pd.DataFrame([{
        "Barang": lab_b.get(it["barang"]), "Kategori": lab_k.get((barang_dari(it["barang"]) or {}).get("kategori")) if it.get("barang") else None,
        "Keterangan": it.get("nama", "") if not it.get("barang") else "", "Banyaknya": float(it["qty"]),
        "Harga satuan": pd.NA if not it.get("harga") and not (barang_dari(it.get("barang")) or {}).get("harga") else
        int(it.get("harga") or barang_dari(it["barang"])["harga"])} for it in dibeli])
    awal["Harga satuan"] = awal["Harga satuan"].astype("Int64")
    base = f"bl_f_{l['id']}_{versi()}"
    st.caption("Sesuaikan jumlah dan harga sesuai struk. Barang yang bukan dari daftar barang perlu Kategori.")
    df = editor_kartu(f"{base}_tbl", awal, tetap=True)
    baris_ok, _ = baca_baris(df)
    st.markdown(f"**Total: {rp(total_baris(baris_ok))}** · {len(baris_ok)} barang")
    c1, c2 = st.columns(2)
    tgl = c1.date_input("Tanggal", value=hari_ini(), min_value=TGL_MIN, max_value=TGL_MAX, format="DD/MM/YYYY", key=f"{base}_tgl")
    w = c2.time_input("Waktu beli", value=sekarang().time().replace(second=0, microsecond=0), step=60, key=f"{base}_w")
    c3, c4 = st.columns(2)
    dompet = [d["id"] for d in dompet_aktif()]
    if not dompet:
        st.warning("Tambah dompet dulu di Pengaturan > Data master > Dompet.")
        return
    dari = c3.selectbox("Dari dompet", dompet, format_func=f_dompet(), key=f"{base}_dompet")
    tops = [""] + [x["id"] for x in sorted(D["toko"], key=lambda x: (not x.get("favorit"), x["nama"].lower()))]
    awal_toko = l.get("toko") if l.get("toko") in tops else ""
    toko = c4.selectbox("Toko", tops, index=tops.index(awal_toko), format_func=f_toko(), key=f"{base}_toko")
    lokasi = st.text_input("Lokasi", value=(toko_dari(toko) or {}).get("lokasi", ""), max_chars=80, key=f"{base}_lok_{toko}")
    berkas = st.file_uploader("Foto struk, opsional", type=["jpg", "jpeg", "png", "webp"], key=f"{base}_up")
    a, b, _ = st.columns([1.3, 1, 3])
    if a.button("Catat sebagai transaksi", type="primary", key=f"{base}_catat"):
        baris, salah = baca_baris(df)
        if salah:
            st.error("\n\n".join(salah))
        elif not baris:
            st.error("Tidak ada barang untuk dicatat.")
        else:
            struk = proses_foto(berkas, False, "", "struk")
            simpan_struk(baris, tgl, w.strftime("%H:%M"), dari, toko, lokasi.strip(), struk)
            l["riwayat"].append({"tgl": tgl.isoformat(), "total": total_baris(baris), "toko": toko,
                                 "item": [{"barang": it.get("barang", ""), "nama": it.get("nama", ""), "qty": it["qty"], "harga": it.get("harga", 0)}
                                          for it in dibeli]})
            l["item"] = [it for it in l["item"] if not it.get("beli")]
            if not l["item"]:
                l["selesai"] = tgl.isoformat()
            catat("tambah", ringkas_struk(baris, toko) + f' (daftar {l["nama"]})')
            selesai_simpan(f"Belanja dicatat: {len(baris)} barang", **{f"bl_selesai_{l['id']}": False})
    b.button("Tutup", key=f"{base}_x", on_click=atur, args=(f"bl_selesai_{l['id']}", False))


def _kartu_item(l: dict, kunci: str) -> list:
    """Satu kartu per barang di daftar belanja (ramah HP). Kembalikan daftar item seperti l['item']."""
    _, lab_b = peta_barang()
    sk = f"{kunci}_ids"
    if sk not in st.session_state:
        ids = []
        for n, it in enumerate(l["item"]):
            ids.append(n)
            st.session_state[f"{kunci}_{n}_brg"] = it.get("barang") if it.get("barang") in lab_b else ""
            st.session_state[f"{kunci}_{n}_ket"] = it.get("nama", "")
            st.session_state[f"{kunci}_{n}_qty"] = float(it.get("qty") or 1)
            st.session_state[f"{kunci}_{n}_hrg"] = int(it.get("harga") or 0)
            st.session_state[f"{kunci}_{n}_beli"] = bool(it.get("beli"))
        st.session_state[sk] = ids
        st.session_state[f"{kunci}_next"] = len(ids)
    ids = st.session_state[sk]
    opsi = [""] + list(lab_b)
    hasil, hapus = [], None
    if not ids:
        st.caption("Belum ada barang. Tekan Tambah barang di bawah.")
    for rid in ids:
        k = f"{kunci}_{rid}"
        if st.session_state.get(f"{k}_brg") not in opsi:
            st.session_state[f"{k}_brg"] = ""
        with st.container(border=True, key=f"kartu_g_bi_{k}"):
            h1, h2 = st.columns([6, 1])
            beli = h1.checkbox("Sudah dibeli", key=f"{k}_beli")
            if h2.button("", key=f"{k}_del", help="Hapus barang ini"):
                hapus = rid
            brg = st.selectbox("Barang", opsi, key=f"{k}_brg", format_func=lambda i: lab_b.get(i, "(pilih dari daftar barang)") if i else "(pilih dari daftar barang)")
            ket = ""
            if not brg:
                ket = st.text_input("Nama barang (di luar daftar)", key=f"{k}_ket", max_chars=60)
            c1, c2 = st.columns(2)
            qty = c1.number_input("Banyaknya", min_value=0.0, step=1.0, format="%g", key=f"{k}_qty")
            hrg = c2.number_input("Perkiraan harga (Rp)", min_value=0, step=500, key=f"{k}_hrg",
                                  help="Kosong = harga terakhir barang.")
            b = barang_dari(brg) if brg else None
            efektif = int(hrg) or int((b or {}).get("harga") or 0)
            if b:
                tm = termurah(b["id"])
                if tm:
                    st.caption(f"Termurah: {tm[0]} · {rp(tm[1])}")
                if efektif:
                    tampil_peringatan_harga(b["id"], efektif)
            if efektif and qty:
                st.caption(f"Subtotal: {rp(round(qty * efektif))}")
        if brg or ket.strip():
            hasil.append({"barang": brg or "", "nama": "" if brg else ket.strip(),
                          "qty": float(qty) if qty > 0 else 1.0, "harga": int(hrg), "beli": bool(beli)})
    if hapus is not None:
        st.session_state[sk] = [i for i in ids if i != hapus]
        st.rerun()
    if st.button("Tambah barang", key=f"{kunci}_tambah"):
        n = st.session_state[f"{kunci}_next"]
        st.session_state[f"{kunci}_{n}_qty"] = 1.0
        st.session_state[sk] = ids + [n]
        st.session_state[f"{kunci}_next"] = n + 1
        st.rerun()
    return hasil


def _banding_toko(items: list, biasa: int, kunci: str):
    """Toko mana yang paling hemat untuk seluruh daftar ini."""
    if len(items) < 2:
        return
    hasil = bandingkan_toko(items)
    with st.expander("Toko mana yang paling hemat?"):
        if not hasil:
            st.caption("Belum cukup riwayat harga. Perbandingan muncul setelah barang di daftar pernah dicatat dengan toko, "
                       "minimal separuh barang di toko yang sama.")
            return
        st.caption("Perkiraan total bila semua dibeli di satu toko, memakai harga terakhir di toko itu. Barang yang belum pernah "
                   f"dibeli di sana dihitung dengan perkiraan harga di daftar. Perkiraan daftar sekarang: {rp(biasa)}.")
        for i, h in enumerate(hasil[:4], start=1):
            with st.container(border=True, key=f"kartu_g_bt_{kunci}_{h['toko']}"):
                selisih = biasa - h["total"]
                ket = f"hemat {rp(selisih)}" if selisih > 0 else f"lebih mahal {rp(-selisih)}" if selisih < 0 else "sama dengan perkiraan"
                st.markdown(f"**{i}. {e(h['nama'])}** · {rp(h['total'])} · {ket}")
                st.caption(f"Harga diketahui untuk {h['ada']} dari {h['n']} barang.")
                st.button("Pakai toko ini", key=f"{kunci}_pt_{h['toko']}", on_click=atur, args=(f"{kunci}_toko", h["toko"]))


def _satu_daftar(l: dict):
    kunci = f"bl_{l['id']}_{st.session_state.get('bl_ver_' + l['id'], 0)}"
    c1, c2 = st.columns(2)
    tops = [""] + [x["id"] for x in sorted(D["toko"], key=lambda x: (not x.get("favorit"), x["nama"].lower()))]
    toko = c1.selectbox("Rencana toko", tops, index=tops.index(l["toko"]) if l.get("toko") in tops else 0,
                        format_func=f_toko(), key=f"{kunci}_toko")
    with c2:
        st.write("")
        if st.button("Tambah semua barang langganan", key=f"{kunci}_lg", width="stretch"):
            ada = {it.get("barang") for it in l["item"]}
            baru = [b for b in D["barang"] if b.get("langganan") and b["id"] not in ada]
            for b in baru:
                l["item"].append({"barang": b["id"], "nama": "", "qty": 1.0, "harga": int(b.get("harga") or 0), "beli": False})
            if baru:
                catat("belanja", f"Tambah {len(baru)} barang langganan ke {l['nama']}")
                selesai_simpan(f"{len(baru)} barang langganan ditambah.", **{f"bl_ver_{l['id']}": st.session_state.get("bl_ver_" + l["id"], 0) + 1})
            else:
                st.info("Tidak ada barang langganan baru. Tandai barang sebagai langganan di Pengaturan > Data master > Barang dan produk.")
    item_baru = _kartu_item(l, kunci)
    biasa, murah, n = _taksir(item_baru)
    dibeli = sum(1 for it in item_baru if it["beli"])
    st.markdown(f"**Perkiraan total: {rp(biasa)}** · {len(item_baru)} barang · {dibeli} sudah dicentang")
    if n and murah < biasa:
        st.caption(f"Kalau tiap barang dibeli di toko termurahnya, perkiraan {rp(murah)} (hemat {rp(biasa - murah)}).")
    _banding_toko(item_baru, biasa, kunci)
    a, b, c, _ = st.columns([1, 1.4, 1, 2])
    if a.button("Simpan", type="primary", key=f"{kunci}_simpan"):
        l["item"], l["toko"] = item_baru, toko
        catat("belanja", f"Ubah daftar belanja {l['nama']}")
        selesai_simpan("Daftar disimpan.", **{f"bl_ver_{l['id']}": st.session_state.get("bl_ver_" + l["id"], 0) + 1})
    if b.button("Selesai belanja, catat…", key=f"{kunci}_sel"):
        l["item"], l["toko"] = item_baru, toko
        selesai_simpan("Daftar disimpan.", **{f"bl_selesai_{l['id']}": True, f"bl_ver_{l['id']}": st.session_state.get("bl_ver_" + l["id"], 0) + 1})
    c.button("Hapus daftar", key=f"{kunci}_hapus", on_click=atur, args=("hapus_bl", l["id"]))
    if st.session_state.get("hapus_bl") == l["id"]:
        st.warning(f"Hapus daftar {l['nama']}? Transaksi yang sudah dicatat dari daftar ini tidak ikut terhapus.")
        y, n_, _ = st.columns([1, 1, 4])
        if y.button("Ya, hapus", type="primary", key=f"{kunci}_ya"):
            D["belanja"] = [x for x in D["belanja"] if x["id"] != l["id"]]
            catat("belanja", f"Hapus daftar belanja {l['nama']}")
            selesai_simpan("Daftar dihapus.", hapus_bl=None, bl_pilih=None)
        n_.button("Batal", key=f"{kunci}_batal", on_click=atur, args=("hapus_bl", None))
    if st.session_state.get(f"bl_selesai_{l['id']}"):
        with st.container(key=f"kartu_g_bl_sel_{l['id']}"):
            _panel_selesai(l)


def halaman_belanja():
    if hanya_lihat():
        st.info("Akun ini hanya bisa melihat.")
    aktif = _daftar_aktif()
    ids = [x["id"] for x in aktif]
    if ids:
        if st.session_state.get("bl_pilih") not in ids:
            st.session_state["bl_pilih"] = ids[0]
        nama = {x["id"]: f'{x["nama"]} ({len(x["item"])} barang)' for x in aktif}
        pil = st.selectbox("Daftar belanja", ids, format_func=lambda i: nama.get(i, ""), key="bl_pilih")
        l = next(x for x in aktif if x["id"] == pil)
        if hanya_lihat():
            st.dataframe(pd.DataFrame([{"Barang": _nama_item(it), "Banyaknya": it["qty"], "Perkiraan harga": it.get("harga", 0)} for it in l["item"]]),
                         hide_index=True, width="stretch")
        else:
            with st.container(key=f"kartu_g_bl_{l['id']}"):
                panel_stok(l)
                _satu_daftar(l)
    else:
        st.info("Belum ada daftar belanja. Buat satu di bawah.")
    if hanya_lihat():
        return
    with st.expander("Buat daftar baru", expanded=not ids):
        _buat_daftar()
    selesai = [x for x in D["belanja"] if x.get("selesai")]
    if selesai:
        with st.expander(f"Daftar selesai ({len(selesai)})"):
            for x in sorted(selesai, key=lambda x: x["selesai"], reverse=True):
                total = sum(r["total"] for r in x.get("riwayat", []))
                c1, c2 = st.columns([3, 1])
                c1.markdown(f'**{e(x["nama"])}** · selesai {fmt_iso(x["selesai"])} · {rp(total)}', unsafe_allow_html=True)
                if c2.button("Pakai lagi", key=f"bl_ulang_{x['id']}"):
                    baru = {"id": baru_id(), "nama": x["nama"], "toko": (x["riwayat"][-1].get("toko") if x.get("riwayat") else x.get("toko", "")),
                            "dibuat": hari_ini().isoformat(), "riwayat": [], "item": []}
                    lihat = set()
                    for r in x.get("riwayat", []):
                        for it in r["item"]:
                            k = (it.get("barang"), it.get("nama"))
                            if k not in lihat:
                                lihat.add(k)
                                baru["item"].append({"barang": it.get("barang", ""), "nama": it.get("nama", ""), "qty": it["qty"],
                                                     "harga": it.get("harga", 0), "beli": False})
                    D["belanja"].append(baru)
                    catat("belanja", f"Pakai lagi daftar belanja {x['nama']}")
                    selesai_simpan("Daftar baru dibuat dari daftar lama.", bl_pilih=baru["id"])
