"""Barang dan produk: daftar barang per kategori / sub kategori, dipakai saat mencatat transaksi."""
import streamlit as st

from keuangan.bantu import (
    pilih_kategori, akar, atur, catat, e, f_kat, ikon_kat, kategori_jenis, nama_kat, selesai_simpan, transaksi_barang, turunan, versi,
)
from keuangan.inti import D, baru_id, fmt_iso, hanya_lihat, rp


def semua_kategori() -> list:
    return [k["id"] for j in ("keluar", "masuk") for k in kategori_jenis(j)]


def _form(awal: dict | None, kat_awal: str = ""):
    awal = awal or {}
    if not semua_kategori():
        st.warning("Belum ada kategori. Tambah dulu di Pengaturan > Kategori.")
        return
    pil = awal.get("kategori") or kat_awal
    kk = f"f_brg_{versi()}_{awal.get('id', 'baru')}"
    jenis = next((k["jenis"] for k in D["kategori"] if k["id"] == pil), "keluar")
    jenis = st.radio("Jenis kategori", ["keluar", "masuk"], index=0 if jenis == "keluar" else 1, horizontal=True,
                     format_func=lambda j: "Pengeluaran" if j == "keluar" else "Pemasukan", key=f"{kk}_jenis")
    kat = pilih_kategori(f"{kk}_{jenis}", jenis, pil if any(k["id"] == pil and k["jenis"] == jenis for k in D["kategori"]) else "")
    with st.form(f"{kk}_{kat}", clear_on_submit=not awal):
        nama = st.text_input("Nama barang", value=awal.get("nama", ""), placeholder="Contoh: Indomie goreng")
        c3, c4 = st.columns(2)
        satuan = c3.text_input("Satuan, opsional", value=awal.get("satuan", ""), placeholder="bungkus, kg, liter")
        harga = c4.number_input("Harga satuan (Rp), opsional", min_value=0, step=500, value=int(awal.get("harga", 0) or 0),
                                help="Terisi otomatis saat mencatat. Harga ikut diperbarui dari transaksi terbaru barang ini.")
        if st.form_submit_button("Simpan perubahan" if awal else "Tambah barang", type="primary"):
            if not nama.strip():
                st.error("Isi nama barang.")
            elif any(x["nama"].strip().lower() == nama.strip().lower() and x["kategori"] == kat and x["id"] != awal.get("id")
                     for x in D["barang"]):
                st.error("Barang itu sudah ada di kategori ini.")
            else:
                isi = {"nama": nama.strip(), "kategori": kat, "satuan": satuan.strip(), "harga": int(harga)}
                if awal:
                    awal.update(isi)
                else:
                    D["barang"].append({"id": baru_id(), **isi})
                catat("barang", f"{'Ubah' if awal else 'Tambah'} barang {isi['nama']} di {nama_kat(kat)}")
                selesai_simpan("Barang disimpan.", edit_brg=None)


def _lepas_barang(b: dict):
    """Hapus barang. Transaksi lama tetap ada; tautan barang dilepas dan namanya dipindah ke catatan bila kosong."""
    for t in D["transaksi"]:
        if t.get("barang") == b["id"]:
            if not t.get("catatan"):
                t["catatan"] = b["nama"]
            for k in ("barang", "qty", "harga_satuan"):
                t.pop(k, None)
    D["barang"] = [x for x in D["barang"] if x["id"] != b["id"]]


def halaman_barang():
    with st.container(key="kartu_filter"):
        c1, c2 = st.columns([1, 1])
        kat = c1.selectbox("Kategori", ["semua"] + semua_kategori(), key="br_kat", format_func=f_kat({"semua": "Semua kategori"}))
        q = c2.text_input("Cari nama barang", key="br_q", placeholder="Ketik kata kunci").strip().lower()
    daftar = [b for b in D["barang"] if (kat == "semua" or b["kategori"] in turunan(kat)) and q in b["nama"].lower()]
    st.caption(f"{len(daftar)} barang" + ("" if daftar else ". Belum ada, tambahkan di bawah (atau langsung dari menu Catat transaksi)."))
    kelompok = {}
    for b in sorted(daftar, key=lambda b: (nama_kat(b["kategori"]).lower(), b["nama"].lower())):
        kelompok.setdefault(b["kategori"], []).append(b)
    for k, isi in kelompok.items():
        st.markdown(f'<div class="dgrup">{e(nama_kat(k))}<span>{len(isi)}</span></div>', unsafe_allow_html=True)
        for b in isi:
            pakai = transaksi_barang(b["id"])
            total = sum(t["jumlah"] for t in pakai)
            ket = (f'{rp(b["harga"])}' + (f' / {e(b["satuan"])}' if b.get("satuan") else "") if b.get("harga") else "harga belum diisi")
            ket += f' · dibeli {len(pakai)}×' + (f' · terakhir {fmt_iso(pakai[0]["tgl"])}' if pakai else "") + (f' · total {rp(total)}' if pakai else "")
            with st.container(key=f"tx_br_{b['id']}"):
                kolom = st.columns([1] + ([0.001, 0.001] if not hanya_lihat() else []))
                kolom[0].markdown(f'<div class="rt"><div class="ic kat" style="background:{e(kat_warna(b["kategori"]))}">{e(kat_ikon(b["kategori"]))}</div>'
                                  f'<div class="isi"><div class="jd">{e(b["nama"])}</div><div class="mt">{ket}</div></div></div>',
                                  unsafe_allow_html=True)
                if not hanya_lihat():
                    kolom[1].button("Ubah", key=f"kedit_br_{b['id']}", on_click=atur, args=("edit_brg", b["id"]))
                    kolom[2].button("Hapus", key=f"khapus_br_{b['id']}", on_click=atur, args=("hapus_brg", b["id"]))
            if st.session_state.get("hapus_brg") == b["id"]:
                st.warning(f"Hapus barang {b['nama']}? " + (f"Dipakai di {len(pakai)} transaksi; transaksinya tetap ada dan namanya dipindah ke catatan." if pakai else ""))
                a, c, _ = st.columns([1, 1, 4])
                if a.button("Ya, hapus", key=f"ya_br_{b['id']}", type="primary"):
                    _lepas_barang(b)
                    catat("barang", f"Hapus barang {b['nama']}")
                    selesai_simpan("Barang dihapus.", hapus_brg=None)
                c.button("Batal", key=f"batal_br_{b['id']}", on_click=atur, args=("hapus_brg", None))
    if hanya_lihat():
        return
    edit = next((x for x in D["barang"] if x["id"] == st.session_state.get("edit_brg")), None)
    with st.container(key="kartu_g_form_brg"):
        st.markdown(f"**{'Ubah barang' if edit else 'Tambah barang'}**")
        _form(edit, kat if kat != "semua" else "")
        if edit and st.button("Batal ubah", key="batal_ubah_brg"):
            st.session_state.pop("edit_brg", None)
            st.rerun()
        st.caption("Memindahkan barang ke kategori lain tidak mengubah kategori pada transaksi yang sudah tercatat.")


def kat_warna(id_) -> str:
    from keuangan.bantu import kat_dari
    k = kat_dari(id_)
    return k.get("warna", "#9aa0a6") if k else "#9aa0a6"


def kat_ikon(id_) -> str:
    from keuangan.bantu import kat_dari
    k = kat_dari(id_)
    return k.get("ikon", "📦") if k else "📦"
