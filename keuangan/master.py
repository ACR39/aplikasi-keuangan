"""Master data: dompet dan kategori."""
import streamlit as st

from keuangan.bantu import (
    anak_dari, atur, catat, e, f_dompet, f_kat, kat_dari, kategori_jenis, kategori_utama, nama_kat, saldo_dompet,
    selesai_simpan, versi,
)
from keuangan.inti import D, IKON_PILIHAN, JENIS_DOMPET, PALET, baru_id, rp


def _dipakai_dompet(id_) -> int:
    return sum(1 for t in D["transaksi"] if id_ in (t["dompet"], t.get("ke"))) + sum(1 for t in D["tagihan"] if t["dompet"] == id_)


def halaman_dompet():
    with st.container(key="kartu_g_daftar_dompet"):
        st.markdown('<div class="dh"><span class="dt">Dompet</span><span class="dn">%d</span></div>'
                    '<div class="dd">Tempat uang disimpan: tunai, rekening bank, dompet digital, kartu kredit. Saldo dihitung otomatis '
                    'dari saldo awal ditambah semua transaksi.</div>' % len(D["dompet"]), unsafe_allow_html=True)
        for d in D["dompet"]:
            c = st.columns([1, 0.001, 0.001, 0.001])
            c[0].markdown(f'<div class="itm"><div class="isi"><div class="jd">{e(d["nama"])}{" (diarsipkan)" if d.get("arsip") else ""}</div>'
                          f'<div class="mt">{e(d.get("jenis", ""))} · saldo {rp(saldo_dompet(d["id"]))} · saldo awal {rp(d.get("saldo_awal", 0))}</div></div></div>',
                          unsafe_allow_html=True)
            c[1].button("Ubah", key=f"ub_dm_{d['id']}", on_click=atur, args=("edit_dompet", d["id"]))
            c[2].button("Arsipkan" if not d.get("arsip") else "Aktifkan", key=f"ub_ars_{d['id']}",
                        on_click=atur, args=("ars_dompet", d["id"]))
            c[3].button("Hapus", key=f"hp_dm_{d['id']}", on_click=atur, args=("hapus_dompet", d["id"]))
            if st.session_state.get("ars_dompet") == d["id"]:
                d["arsip"] = not d.get("arsip")
                catat("dompet", f"{'Arsipkan' if d['arsip'] else 'Aktifkan'} dompet {d['nama']}")
                st.session_state.pop("ars_dompet")
                selesai_simpan("Dompet diperbarui.")
            if st.session_state.get("hapus_dompet") == d["id"]:
                n = _dipakai_dompet(d["id"])
                if n:
                    st.warning(f"Dompet {d['nama']} dipakai di {n} transaksi atau tagihan, jadi tidak bisa dihapus. "
                               "Arsipkan saja supaya tidak muncul di pilihan.")
                    st.button("Mengerti", key=f"ok_dm_{d['id']}", on_click=atur, args=("hapus_dompet", None))
                else:
                    st.warning(f"Hapus dompet {d['nama']}?")
                    a, b, _ = st.columns([1, 1, 4])
                    if a.button("Ya, hapus", key=f"ya_dm_{d['id']}", type="primary"):
                        D["dompet"] = [x for x in D["dompet"] if x["id"] != d["id"]]
                        catat("dompet", f"Hapus dompet {d['nama']}")
                        selesai_simpan("Dompet dihapus.", hapus_dompet=None)
                    b.button("Batal", key=f"batal_dm_{d['id']}", on_click=atur, args=("hapus_dompet", None))
        edit = next((x for x in D["dompet"] if x["id"] == st.session_state.get("edit_dompet")), None)
        with st.form(f"f_dompet_{versi()}_{edit['id'] if edit else 'baru'}", clear_on_submit=not edit):
            st.markdown(f"**{'Ubah dompet' if edit else 'Tambah dompet'}**")
            c1, c2, c3 = st.columns(3)
            nama = c1.text_input("Nama", value=edit["nama"] if edit else "", placeholder="Contoh: BCA, GoPay")
            jenis = c2.selectbox("Jenis", JENIS_DOMPET, index=JENIS_DOMPET.index(edit["jenis"]) if edit and edit.get("jenis") in JENIS_DOMPET else 1)
            awal = c3.number_input("Saldo awal (Rp)", step=10000, value=int(edit.get("saldo_awal", 0)) if edit else 0,
                                   help="Saldo sebelum transaksi pertama yang dicatat. Boleh negatif untuk kartu kredit.")
            if st.form_submit_button("Simpan perubahan" if edit else "Tambah", type="primary"):
                if not nama.strip():
                    st.error("Isi nama dompet.")
                elif any(x["nama"].strip().lower() == nama.strip().lower() and x is not edit for x in D["dompet"]):
                    st.error("Sudah ada dompet dengan nama itu.")
                else:
                    if edit:
                        edit.update({"nama": nama.strip(), "jenis": jenis, "saldo_awal": int(awal)})
                    else:
                        D["dompet"].append({"id": baru_id(), "nama": nama.strip(), "jenis": jenis, "saldo_awal": int(awal), "arsip": False})
                    catat("dompet", f"{'Ubah' if edit else 'Tambah'} dompet {nama.strip()}")
                    selesai_simpan("Dompet disimpan.", edit_dompet=None)
        if edit and st.button("Batal ubah", key="batal_ubah_dm"):
            st.session_state.pop("edit_dompet", None)
            st.rerun()


def _jumlah_pakai(id_) -> int:
    return (sum(1 for t in D["transaksi"] if t.get("kategori") == id_) + sum(1 for a in D["anggaran"] if a["kategori"] == id_)
            + sum(1 for t in D["tagihan"] if t["kategori"] == id_) + sum(1 for b in D["barang"] if b["kategori"] == id_))


def _form_kat(kunci: str, jenis: str, awal: dict | None = None, induk: str = "", tombol: str = "Tambah"):
    """Form kategori. Kembalikan dict isian bila sah dan tombol ditekan."""
    awal = awal or {}
    p = kat_dari(induk or awal.get("induk"))
    with st.form(kunci, clear_on_submit=not awal):
        c1, c2, c3 = st.columns([2, 1, 1])
        nama = c1.text_input("Nama", value=awal.get("nama", ""), placeholder="Contoh: Listrik" if induk else "Contoh: Rumah")
        ikon = c2.selectbox("Ikon", IKON_PILIHAN, index=IKON_PILIHAN.index(awal["ikon"]) if awal.get("ikon") in IKON_PILIHAN else
                            (IKON_PILIHAN.index(p["ikon"]) if p and p.get("ikon") in IKON_PILIHAN else 0))
        warna = c3.color_picker("Warna", value=awal.get("warna") or (p["warna"] if p else PALET[len(D["kategori"]) % len(PALET)]))
        letak = awal.get("induk", induk)
        if awal and not anak_dari(awal["id"]):
            opsi = [""] + [x["id"] for x in kategori_utama(jenis) if x["id"] != awal["id"]]
            letak = st.selectbox("Letak", opsi, index=opsi.index(letak) if letak in opsi else 0,
                                 format_func=f_kat({"": "Kategori utama"}))
        kirim = st.form_submit_button(tombol, type="primary")
    if not kirim:
        return None
    if not nama.strip():
        st.error("Isi nama kategori.")
        return None
    if any(x["nama"].strip().lower() == nama.strip().lower() and x.get("induk", "") == letak and x["jenis"] == jenis
           and x["id"] != awal.get("id") for x in D["kategori"]):
        st.error("Sudah ada kategori dengan nama itu di tempat yang sama.")
        return None
    return {"nama": nama.strip(), "ikon": ikon, "warna": warna, "induk": letak}


def _hapus_kat(k: dict, jenis: str):
    n_anak = len(anak_dari(k["id"]))
    if n_anak:
        st.warning(f"{k['nama']} masih punya {n_anak} sub kategori. Hapus atau pindahkan dulu sub kategorinya.")
        st.button("Mengerti", key=f"ok_kt_{k['id']}", on_click=atur, args=("hapus_kat", None))
        return
    pakai = _jumlah_pakai(k["id"])
    if not pakai:
        st.warning(f"Hapus kategori {k['nama']}?")
        a, b, _ = st.columns([1, 1, 4])
        if a.button("Ya, hapus", key=f"ya_kt_{k['id']}", type="primary"):
            D["kategori"] = [x for x in D["kategori"] if x["id"] != k["id"]]
            catat("kategori", f"Hapus kategori {nama_kat(k['id'])}")
            selesai_simpan("Kategori dihapus.", hapus_kat=None, tb_kat_buka=None if st.session_state.get("tb_kat_buka") == k["id"] else st.session_state.get("tb_kat_buka"))
        b.button("Batal", key=f"batal_kt_{k['id']}", on_click=atur, args=("hapus_kat", None))
        return
    lain = [x["id"] for x in kategori_jenis(jenis) if x["id"] != k["id"]]
    if not lain:
        st.warning("Kategori ini dipakai dan tidak ada kategori lain untuk menampung. Tambah kategori lain dulu.")
        return
    st.warning(f"{k['nama']} dipakai di {pakai} data. Gabungkan ke kategori lain sebelum dihapus.")
    ganti = st.selectbox("Gabungkan ke", lain, format_func=f_kat(), key=f"tb_gab_{k['id']}")
    a, b, _ = st.columns([1.3, 1, 4])
    if a.button("Gabung dan hapus", key=f"ya_kt_{k['id']}", type="primary"):
        for t in D["transaksi"]:
            if t.get("kategori") == k["id"]:
                t["kategori"] = ganti
        for t in D["tagihan"]:
            if t["kategori"] == k["id"]:
                t["kategori"] = ganti
        for bb in D["barang"]:
            if bb["kategori"] == k["id"]:
                bb["kategori"] = ganti
        sudah = {x["kategori"] for x in D["anggaran"] if x["kategori"] != k["id"]}
        D["anggaran"] = [x for x in D["anggaran"] if x["kategori"] != k["id"] or ganti not in sudah]
        for x in D["anggaran"]:
            if x["kategori"] == k["id"]:
                x["kategori"] = ganti
        catat("kategori", f"Gabung kategori {nama_kat(k['id'])} ke {nama_kat(ganti)}")
        D["kategori"] = [x for x in D["kategori"] if x["id"] != k["id"]]
        selesai_simpan("Kategori digabung.", hapus_kat=None)
    b.button("Batal", key=f"batal_kt_{k['id']}", on_click=atur, args=("hapus_kat", None))


def _baris_kat(k: dict, jenis: str, buka: bool = False, ubah: bool = True):
    """Satu baris kategori (bulatan ikon, nama, jumlah sub) dengan tombol Buka / Ubah / Hapus."""
    n = len(anak_dari(k["id"]))
    with st.container(key=f"tx_kt_{k['id']}"):
        kolom = st.columns([1] + [0.001] * (1 + 2 * ubah))
        kolom[0].markdown(f'<div class="rt"><div class="ic kat" style="background:{e(k.get("warna", "#9aa0a6"))}">{e(k.get("ikon", "🏷️"))}</div>'
                          f'<div class="isi"><div class="jd">{e(k["nama"])}</div></div>'
                          f'<div class="mt">{f"({n})" if n and buka else ""}</div></div>', unsafe_allow_html=True)
        i = 1
        if buka:
            kolom[i].button("Buka", key=f"buka_kt_{k['id']}", on_click=atur, args=("tb_kat_buka", k["id"]))
            i += 1
        if ubah:
            kolom[i].button("Ubah", key=f"kedit_kt_{k['id']}", on_click=atur, args=("edit_kat", k["id"]))
            kolom[i + 1].button("Hapus", key=f"khapus_kt_{k['id']}", on_click=atur, args=("hapus_kat", k["id"]))
    if st.session_state.get("edit_kat") == k["id"]:
        with st.container(key=f"kartu_g_edkat_{k['id']}"):
            isi = _form_kat(f"f_ekat_{k['id']}_{versi()}", jenis, awal=k, tombol="Simpan perubahan")
            if st.button("Batal", key=f"batal_ek_{k['id']}", on_click=atur, args=("edit_kat", None)):
                pass
            if isi:
                lama = nama_kat(k["id"])
                k.update(isi)
                for x in anak_dari(k["id"]):
                    pass
                catat("kategori", f"Ubah kategori {lama} → {nama_kat(k['id'])}")
                selesai_simpan("Kategori diubah.", edit_kat=None)
    if st.session_state.get("hapus_kat") == k["id"]:
        _hapus_kat(k, jenis)


def halaman_kategori():
    jenis = st.radio("Jenis", ["keluar", "masuk"], format_func={"keluar": "Pengeluaran", "masuk": "Pemasukan"}.get,
                     horizontal=True, key="tb_kat_jenis", label_visibility="collapsed")
    p = kat_dari(st.session_state.get("tb_kat_buka"))
    if p and (p["jenis"] != jenis or p.get("induk")):
        st.session_state.pop("tb_kat_buka", None)
        p = None
    if p is None:
        utama = kategori_utama(jenis)
        st.markdown(f'<div class="dgrup">Semua kategori<span>{len(utama)} kategori utama · {len(kategori_jenis(jenis)) - len(utama)} sub</span></div>',
                    unsafe_allow_html=True)
        for k in utama:
            _baris_kat(k, jenis, buka=True, ubah=False)
        with st.container(key="kartu_g_kat_baru"):
            st.markdown("**Tambah kategori utama**")
            isi = _form_kat(f"f_kat_baru_{jenis}_{versi()}", jenis)
            if isi:
                D["kategori"].append({"id": baru_id(), "jenis": jenis, **isi})
                catat("kategori", f"Tambah kategori {isi['nama']}")
                selesai_simpan("Kategori ditambah.")
        return
    st.button("← Kembali ke semua kategori", key="kembali_kat", on_click=atur, args=("tb_kat_buka", None))
    st.markdown('<div class="dgrup">Umum<span>kategori utama</span></div>', unsafe_allow_html=True)
    _baris_kat(p, jenis)
    anak = sorted(anak_dari(p["id"]), key=lambda k: k["nama"].lower())
    st.markdown(f'<div class="dgrup">Sub kategori<span>{len(anak)}</span></div>', unsafe_allow_html=True)
    if not anak:
        st.caption("Belum ada sub kategori. Transaksi bisa langsung memakai kategori utama.")
    for k in anak:
        _baris_kat(k, jenis)
    with st.container(key="kartu_g_sub_baru"):
        st.markdown(f"**Tambah sub kategori di {p['nama']}**")
        isi = _form_kat(f"f_sub_baru_{p['id']}_{versi()}", jenis, induk=p["id"])
        if isi:
            D["kategori"].append({"id": baru_id(), "jenis": jenis, **isi})
            catat("kategori", f"Tambah sub kategori {isi['nama']} di {p['nama']}")
            selesai_simpan("Sub kategori ditambah.")
