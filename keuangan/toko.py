"""Toko dan tempat beli: daftar toko (nama, jenis, lokasi) yang dipilih saat mencatat transaksi."""
import streamlit as st

from keuangan.bantu import daftar_jenis_toko, ikon_jenis_toko, jumlah_kunjungan
from keuangan.bantu import atur, catat, e, ikon_foto, kolom_foto, link_aman, proses_foto, selesai_simpan, transaksi_toko, versi
from keuangan.peta import peta_semua, pilih_titik, proses_gps, terdekat, teks_jarak, titik_dari, tombol_gps, url_peta
from keuangan.inti import D, IKON_PILIHAN, baru_id, fmt_iso, hanya_lihat, ikon_html, rp
from keuangan.ikon_pilih import pilih_ikon
from keuangan.pwa import gulir_ke_atas_bila_baru


def _form(awal: dict | None, titik=None):
    awal = awal or {}
    with st.form(f"f_toko_{versi()}_{awal.get('id', 'baru')}", clear_on_submit=False):
        c1, c2 = st.columns(2)
        nama = c1.text_input("Nama toko", value=awal.get("nama", ""), placeholder="Contoh: Indomaret Merdeka")
        jenis_list = daftar_jenis_toko()
        jenis = c2.selectbox("Jenis", jenis_list, index=jenis_list.index(awal["jenis"]) if awal.get("jenis") in jenis_list else 0)
        lokasi = st.text_input("Lokasi, opsional", value=awal.get("lokasi", ""), max_chars=80, placeholder="Jl. Merdeka, Bandung")
        with st.expander("Rincian lain: peta, jam buka, telepon, foto", expanded=bool(awal.get("peta") or awal.get("telepon") or awal.get("foto"))):
            peta = st.text_input("Tautan peta (Google Maps)", value=awal.get("peta", ""), placeholder="https://maps.app.goo.gl/...",
                                 help="Buka Google Maps, pilih Bagikan, lalu tempel tautannya di sini.")
            r1, r2 = st.columns(2)
            jam_buka = r1.text_input("Jam buka", value=awal.get("jam_buka", ""), max_chars=40, placeholder="08.00 - 21.00")
            telepon = r2.text_input("Telepon", value=awal.get("telepon", ""), max_chars=25)
            catatan_t = st.text_input("Catatan", value=awal.get("catatan", ""), max_chars=120)
            favorit = st.checkbox("Toko favorit (tampil paling atas)", value=bool(awal.get("favorit")))
            berkas, hapus_f = kolom_foto("Foto toko", f"ft_{awal.get('id', 'baru')}", awal.get("foto", ""), "toko")
        if st.form_submit_button("Simpan perubahan" if awal else "Tambah toko", type="primary"):
            if not nama.strip():
                st.error("Isi nama toko.")
            elif peta.strip() and not link_aman(peta):
                st.error("Tautan peta harus diawali http:// atau https://")
            elif any(x["nama"].strip().lower() == nama.strip().lower() and x.get("lokasi", "").strip().lower() == lokasi.strip().lower()
                     and x["id"] != awal.get("id") for x in D["toko"]):
                st.error("Toko itu sudah ada.")
            else:
                isi = {"nama": nama.strip(), "jenis": jenis, "lokasi": lokasi.strip()}
                foto = proses_foto(berkas, hapus_f, awal.get("foto", ""), "toko")
                if titik:
                    isi["lat"], isi["lon"] = titik
                else:
                    awal.pop("lat", None)
                    awal.pop("lon", None)
                for k_, v_ in (("peta", peta.strip()), ("jam_buka", jam_buka.strip()), ("telepon", telepon.strip()),
                               ("catatan", catatan_t.strip()), ("favorit", bool(favorit)), ("foto", foto)):
                    if v_:
                        isi[k_] = v_
                    else:
                        awal.pop(k_, None)
                if awal:
                    awal.update(isi)
                else:
                    D["toko"].append({"id": baru_id(), **isi})
                catat("toko", f"{'Ubah' if awal else 'Tambah'} toko {isi['nama']}")
                selesai_simpan("Toko disimpan.", edit_toko=None, edit_baru_toko=False, **{f"titik_{awal.get('id') or 'baru'}": "_reset"})


def _lepas_toko(x: dict):
    """Hapus toko. Transaksi tetap ada; nama toko dipindah ke catatan bila kosong, lokasi transaksi dipertahankan."""
    for t in D["transaksi"]:
        if t.get("toko") == x["id"]:
            if not t.get("catatan"):
                t["catatan"] = x["nama"]
            t.pop("toko", None)
    D["toko"] = [y for y in D["toko"] if y["id"] != x["id"]]
    from keuangan.penyimpanan import hapus_foto
    hapus_foto(x.get("foto", ""))


def _toko_terdekat():
    """Tombol dan daftar toko tersimpan terdekat dari posisi pengguna."""
    if not any(titik_dari(x) for x in D["toko"]):
        return
    pos = proses_gps("tk_dekat")
    if pos:
        st.session_state["tk_posisi"] = pos
    tombol_gps("tk_dekat")
    pos = st.session_state.get("tk_posisi")
    if not pos:
        return
    with st.container(border=True, key="kartu_g_tk_dekat"):
        st.markdown("**Toko terdekat dari Anda**")
        for x, km in terdekat(pos, D["toko"]):
            tautan = f"https://www.google.com/maps/dir/?api=1&destination={titik_dari(x)[0]:.6f},{titik_dari(x)[1]:.6f}&origin={pos[0]:.6f},{pos[1]:.6f}"
            st.markdown(f'{ikon_html(ikon_jenis_toko(x.get("jenis")))} **{e(x["nama"])}** · {teks_jarak(km)} · '
                        f'<a href="{e(tautan)}" target="_blank" rel="noopener noreferrer">Rute</a>', unsafe_allow_html=True)
        st.button("Sembunyikan", key="tk_dekat_tutup", on_click=lambda: st.session_state.update(tk_posisi=None))


def halaman_toko():
    atas = st.container()  # form tambah/ubah ditaruh di sini (paling atas) supaya tidak perlu menggulir ke bawah
    with st.container(key="kartu_filter"):
        c1, c2 = st.columns(2)
        jn = c1.selectbox("Jenis", ["semua"] + daftar_jenis_toko(), key="tk_jenis", format_func=lambda j: "Semua jenis" if j == "semua" else j)
        q = c2.text_input("Cari nama atau lokasi", key="tk_q", placeholder="Ketik kata kunci").strip().lower()
    _toko_terdekat()
    daftar = [x for x in D["toko"] if (jn == "semua" or x.get("jenis") == jn) and q in f'{x["nama"]} {x.get("lokasi", "")}'.lower()]
    st.caption(f"{len(daftar)} toko" + ("" if daftar else ". Belum ada, tambahkan di atas (atau langsung dari menu Catat transaksi)."))
    if any(titik_dari(x) for x in D["toko"]) and st.toggle("Lihat semua toko di peta", key="tk_peta"):
        peta_semua(daftar)
    for x in sorted(daftar, key=lambda x: (not x.get("favorit"), x["nama"].lower())):
        pakai = transaksi_toko(x["id"])
        total = sum(t["jumlah"] for t in pakai if t["jenis"] == "keluar")
        ket = ("★ " if x.get("favorit") else "") + x.get("jenis", "Lainnya") + (f' · {e(x["lokasi"])}' if x.get("lokasi") else "")
        if x.get("jam_buka"):
            ket += f' · 🕒 {e(x["jam_buka"])}'
        if x.get("telepon"):
            ket += f' · 📞 {e(x["telepon"])}'
        if url_peta(x):
            ket += f' · <a href="{e(url_peta(x))}" target="_blank" rel="noopener noreferrer">📍 {"Titik di peta" if titik_dari(x) else "Buka di peta"}</a>'
        ket += f" · dikunjungi {jumlah_kunjungan(pakai)}×" + (f" · total {rp(total)} · terakhir {fmt_iso(pakai[0]['tgl'])}" if pakai else "")
        with st.container(key=f"tx_tk_{x['id']}"):
            kolom = st.columns([1] + ([0.001, 0.001] if not hanya_lihat() else []))
            kolom[0].markdown(f'<div class="rt">{ikon_foto(x.get("foto"), ikon_jenis_toko(x.get("jenis")))}'
                              f'<div class="isi"><div class="jd">{e(x["nama"])}</div><div class="mt">{ket}</div></div></div>',
                              unsafe_allow_html=True)
            if not hanya_lihat():
                kolom[1].button("Ubah", key=f"kedit_tk_{x['id']}", on_click=atur, args=("edit_toko", x["id"]))
                kolom[2].button("Hapus", key=f"khapus_tk_{x['id']}", on_click=atur, args=("hapus_toko", x["id"]))
        if st.session_state.get("hapus_toko") == x["id"]:
            st.warning(f"Hapus toko {x['nama']}? " + (f"Dipakai di {len(pakai)} transaksi; transaksinya tetap ada dan namanya dipindah ke catatan." if pakai else ""))
            a, c, _ = st.columns([1, 1, 4])
            if a.button("Ya, hapus", key=f"ya_tk_{x['id']}", type="primary"):
                _lepas_toko(x)
                catat("toko", f"Hapus toko {x['nama']}")
                selesai_simpan("Toko dihapus.", hapus_toko=None)
            c.button("Batal", key=f"batal_tk_{x['id']}", on_click=atur, args=("hapus_toko", None))
    if hanya_lihat():
        return
    edit = next((x for x in D["toko"] if x["id"] == st.session_state.get("edit_toko")), None)
    with atas:
        if not edit and not st.session_state.get("edit_baru_toko"):
            gulir_ke_atas_bila_baru(None)
            st.button("➕ Tambah toko baru", key="tambah_toko_btn", type="primary", on_click=atur, args=("edit_baru_toko", True))
            return
        gulir_ke_atas_bila_baru(("toko", edit["id"] if edit else "baru"))
        with st.container(key="kartu_g_form_tk"):
            st.markdown(f"**{'Ubah toko' if edit else 'Tambah toko'}**")
            kt = (edit or {}).get("id") or "baru"
            if st.session_state.get(f"titik_{kt}") == "_reset":
                for suf in ("", "_klik", "_minta"):
                    st.session_state.pop(f"titik_{kt}{suf}", None)
            st.markdown("**Titik lokasi**")
            titik = pilih_titik(kt, titik_dari(edit))
            _form(edit, titik)
            if st.button("Batal", key="batal_ubah_tk"):
                st.session_state.pop("edit_toko", None)
                st.session_state["edit_baru_toko"] = False
                st.rerun()


# ---------------------------------------------------------------- jenis toko
IKON_TOKO_PILIHAN = IKON_PILIHAN


def _hapus_jenis(j: dict):
    pakai = [x for x in D["toko"] if x.get("jenis") == j["nama"]]
    if not pakai:
        st.warning(f"Hapus jenis {j['nama']}?")
        a, b, _ = st.columns([1, 1, 4])
        if a.button("Ya, hapus", key=f"ya_jt_{j['id']}", type="primary"):
            D["jenis_toko"] = [x for x in D["jenis_toko"] if x["id"] != j["id"]]
            catat("jenis toko", f"Hapus jenis toko {j['nama']}")
            selesai_simpan("Jenis toko dihapus.", hapus_jenis_toko=None)
        b.button("Batal", key=f"batal_jt_{j['id']}", on_click=atur, args=("hapus_jenis_toko", None))
        return
    lain = [x["nama"] for x in D["jenis_toko"] if x["id"] != j["id"]]
    if not lain:
        st.warning("Ini satu-satunya jenis toko, jadi tidak bisa dihapus.")
        st.button("Mengerti", key=f"ok_jt_{j['id']}", on_click=atur, args=("hapus_jenis_toko", None))
        return
    st.warning(f"{j['nama']} dipakai {len(pakai)} toko. Pindahkan toko-tokonya ke jenis lain sebelum menghapus.")
    ganti = st.selectbox("Pindahkan ke", lain, key=f"jt_gab_{j['id']}")
    a, b, _ = st.columns([1.3, 1, 4])
    if a.button("Pindah dan hapus", key=f"ya_jt_{j['id']}", type="primary"):
        for x in pakai:
            x["jenis"] = ganti
        D["jenis_toko"] = [x for x in D["jenis_toko"] if x["id"] != j["id"]]
        catat("jenis toko", f"Hapus jenis toko {j['nama']}, {len(pakai)} toko dipindah ke {ganti}")
        selesai_simpan("Jenis toko dihapus.", hapus_jenis_toko=None)
    b.button("Batal", key=f"batal_jt_{j['id']}", on_click=atur, args=("hapus_jenis_toko", None))


def halaman_jenis_toko():
    with st.container(key="kartu_g_daftar_jenis_toko"):
        st.markdown('<div class="dh"><span class="dt">Jenis toko</span><span class="dn">%d</span></div>'
                    '<div class="dd">Pengelompokan toko, misalnya Minimarket, SPBU, atau Bengkel. Dipakai saat menambah toko dan untuk menyaring daftar toko.</div>'
                    % len(D["jenis_toko"]), unsafe_allow_html=True)
        for j in sorted(D["jenis_toko"], key=lambda x: x["nama"].lower()):
            n = sum(1 for x in D["toko"] if x.get("jenis") == j["nama"])
            c = st.columns([1, 0.001, 0.001])
            c[0].markdown(f'<div class="itm"><div class="isi"><div class="jd">{ikon_html(j.get("ikon", "📍"))} {e(j["nama"])}</div>'
                          f'<div class="mt">{n} toko</div></div></div>', unsafe_allow_html=True)
            if not hanya_lihat():
                c[1].button("Ubah", key=f"ub_jt_{j['id']}", on_click=atur, args=("edit_jenis_toko", j["id"]))
                c[2].button("Hapus", key=f"hp_jt_{j['id']}", on_click=atur, args=("hapus_jenis_toko", j["id"]))
            if st.session_state.get("hapus_jenis_toko") == j["id"] and not hanya_lihat():
                _hapus_jenis(j)
        if hanya_lihat():
            return
        edit = next((x for x in D["jenis_toko"] if x["id"] == st.session_state.get("edit_jenis_toko")), None)
        ikon = pilih_ikon(f"ikjt_{edit['id'] if edit else 'baru'}", (edit or {}).get("ikon") or "mdi:storefront")
        with st.form(f"f_jenis_toko_{versi()}_{edit['id'] if edit else 'baru'}", clear_on_submit=not edit):
            st.markdown(f"**{'Ubah jenis toko' if edit else 'Tambah jenis toko'}**")
            nama = st.text_input("Nama", value=edit["nama"] if edit else "", max_chars=30, placeholder="Contoh: Bengkel, Laundry, Toko bangunan")
            if st.form_submit_button("Simpan perubahan" if edit else "Tambah", type="primary"):
                if not nama.strip():
                    st.error("Isi nama jenis toko.")
                elif any(x["nama"].strip().lower() == nama.strip().lower() and x is not edit for x in D["jenis_toko"]):
                    st.error("Sudah ada jenis toko dengan nama itu.")
                else:
                    if edit:
                        lama = edit["nama"]
                        for x in D["toko"]:
                            if x.get("jenis") == lama:
                                x["jenis"] = nama.strip()
                        edit["nama"], edit["ikon"] = nama.strip(), ikon
                        catat("jenis toko", f"Ubah jenis toko {lama} → {nama.strip()}")
                    else:
                        D["jenis_toko"].append({"id": baru_id(), "nama": nama.strip(), "ikon": ikon})
                        catat("jenis toko", f"Tambah jenis toko {nama.strip()}")
                    selesai_simpan("Jenis toko disimpan.", edit_jenis_toko=None)
        if edit and st.button("Batal ubah", key="batal_ubah_jt"):
            st.session_state.pop("edit_jenis_toko", None)
            st.rerun()
