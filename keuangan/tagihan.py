"""Tagihan dan langganan berulang: jatuh tempo, bayar (otomatis jadi transaksi), lewati."""
from datetime import timedelta

import streamlit as st

from keuangan.bantu import (
    f_dompet, f_kat,
    TIAP, atur, catat, dompet_aktif, e, kat_pertama, kategori_jenis, maju_tgl, nama_dompet, nama_kat, selesai_simpan,
    tambah_transaksi, versi,
)
from keuangan.penyimpanan import commit
from keuangan.inti import D, TGL_MAX, TGL_MIN, baru_id, fmt_iso, hanya_lihat, hari_ini, iso_ke_date, rp, sisa_hari


def status_tagihan(t: dict):
    s = sisa_hari(t.get("berikut"))
    if s is None:
        return "", ""
    if s < 0:
        return f"Terlambat {-s} hari", "st-bad"
    if s == 0:
        return "Jatuh tempo hari ini", "st-bad"
    if s <= 7:
        return f"{s} hari lagi", "st-warn"
    return f"{s} hari lagi", "st-ok"


def tagihan_mendekat(hari: int = 7) -> list:
    """Tagihan aktif yang jatuh tempo dalam `hari` hari (termasuk yang sudah lewat), paling mendesak dulu."""
    hasil = [t for t in D["tagihan"] if t.get("aktif", True) and t.get("jenis", "keluar") == "keluar" and not t.get("otomatis")
             and (sisa_hari(t.get("berikut")) or 9999) <= hari]
    return sorted(hasil, key=lambda t: t["berikut"])


def _bayar(t: dict, tgl_bayar):
    tr = tambah_transaksi(t.get("jenis", "keluar"), tgl_bayar, t["jumlah"], t["dompet"], t["kategori"], t["nama"], tagihan=t["id"])
    if t["tiap"] == "sekali":
        t["aktif"] = False
    else:
        t["berikut"] = maju_tgl(iso_ke_date(t["berikut"]), t["tiap"]).isoformat()
    catat("tagihan", f"{'Terima' if t.get('jenis') == 'masuk' else 'Bayar'} {t['nama']} {rp(t['jumlah'])} {'ke' if t.get('jenis') == 'masuk' else 'dari'} {nama_dompet(t['dompet'])}")
    selesai_simpan(f"{t['nama']} dicatat sebagai {'pemasukan' if t.get('jenis') == 'masuk' else 'pengeluaran'}.")


def catat_otomatis():
    """Catat transaksi berulang bertanda otomatis yang sudah jatuh tempo (satu kali per hari per sesi)."""
    if hanya_lihat():
        return
    hari = hari_ini()
    if st.session_state.get("oto_tgl") == hari.isoformat():
        return
    st.session_state["oto_tgl"] = hari.isoformat()
    nama = []
    for t in D["tagihan"]:
        if not t.get("otomatis"):
            continue
        n = 0
        while t.get("aktif", True) and n < 12 and iso_ke_date(t.get("berikut")) and iso_ke_date(t["berikut"]) <= hari:
            tambah_transaksi(t.get("jenis", "keluar"), t["berikut"], t["jumlah"], t["dompet"], t["kategori"], t["nama"], tagihan=t["id"])
            if t["tiap"] == "sekali":
                t["aktif"] = False
            else:
                t["berikut"] = maju_tgl(iso_ke_date(t["berikut"]), t["tiap"]).isoformat()
            nama.append(t["nama"])
            n += 1
    if nama:
        ringkas = ", ".join(sorted(set(nama)))
        catat("tagihan", f"Dicatat otomatis {len(nama)} transaksi berulang: {ringkas}")
        commit(f"Dicatat otomatis {len(nama)} transaksi berulang")


def _lewati(t: dict):
    if t["tiap"] == "sekali":
        t["aktif"] = False
    else:
        t["berikut"] = maju_tgl(iso_ke_date(t["berikut"]), t["tiap"]).isoformat()
    catat("tagihan", f"Lewati tagihan {t['nama']} periode ini")
    selesai_simpan("Tagihan dilewati ke periode berikutnya.")


def _form(awal: dict | None):
    awal = awal or {}
    dompet = [d["id"] for d in dompet_aktif()]
    if awal.get("dompet") and awal["dompet"] not in dompet:
        dompet.append(awal["dompet"])
    if not dompet:
        st.warning("Tambah dompet dulu di Pengaturan > Dompet.")
        return
    jenis = st.radio("Jenis", ["keluar", "masuk"], horizontal=True, index=0 if awal.get("jenis", "keluar") == "keluar" else 1,
                     format_func=lambda j: "Pengeluaran (tagihan, langganan)" if j == "keluar" else "Pemasukan (gaji, dll.)",
                     key=f"tg_jenis_{versi()}_{awal.get('id', 'baru')}")
    ids = [k["id"] for k in kategori_jenis(jenis)]
    if not ids:
        st.warning("Belum ada kategori untuk jenis ini.")
        return
    with st.form(f"f_tg_{versi()}_{awal.get('id', 'baru')}_{jenis}", clear_on_submit=not awal):
        nama = st.text_input("Nama", value=awal.get("nama", ""), placeholder="Contoh: Listrik, Internet, Netflix, Gaji")
        c1, c2 = st.columns(2)
        jumlah = c1.number_input("Jumlah (Rp)", min_value=0, step=5000, value=int(awal.get("jumlah", 0) or 0))
        tiap = c2.selectbox("Berulang", list(TIAP), index=list(TIAP).index(awal.get("tiap", "bulanan")), format_func=TIAP.get)
        c3, c4, c5 = st.columns(3)
        berikut = c3.date_input("Jatuh tempo berikutnya", value=iso_ke_date(awal.get("berikut")) or hari_ini(),
                                min_value=TGL_MIN, max_value=TGL_MAX, format="DD/MM/YYYY")
        pil_k = kat_pertama(jenis, awal.get("kategori", "k_tagihan") if awal.get("jenis", "keluar") == jenis else "")
        kat = c4.selectbox("Kategori", ids, index=ids.index(pil_k) if pil_k in ids else 0, format_func=f_kat())
        dom = c5.selectbox("Dibayar dari" if jenis == "keluar" else "Masuk ke", dompet,
                           index=dompet.index(awal["dompet"]) if awal.get("dompet") in dompet else 0, format_func=f_dompet())
        otomatis = st.checkbox("Catat otomatis saat jatuh tempo", value=bool(awal.get("otomatis")),
                               help="Transaksinya dicatat sendiri saat Anda membuka aplikasi pada atau setelah tanggal jatuh tempo, tanpa menekan Bayar. "
                                    "Cocok untuk jumlah yang tetap, seperti langganan dan gaji.")
        catatan = st.text_input("Catatan, opsional", value=awal.get("catatan", ""))
        if st.form_submit_button("Simpan perubahan" if awal else "Tambah tagihan", type="primary"):
            if not nama.strip() or jumlah <= 0:
                st.error("Isi nama dan jumlah tagihan.")
                return
            isi = {"nama": nama.strip(), "jumlah": int(jumlah), "tiap": tiap, "berikut": berikut.isoformat(),
                   "kategori": kat, "dompet": dom, "catatan": catatan.strip(), "aktif": True, "jenis": jenis, "otomatis": bool(otomatis)}
            if awal:
                awal.update(isi)
            else:
                D["tagihan"].append({"id": baru_id(), **isi})
            catat("tagihan", f"{'Ubah' if awal else 'Tambah'} tagihan {isi['nama']} {rp(isi['jumlah'])} ({TIAP[tiap].lower()})")
            selesai_simpan("Tagihan disimpan.", edit_tg=None)


def halaman_tagihan():
    aktif = sorted([t for t in D["tagihan"] if t.get("aktif", True)], key=lambda t: t["berikut"])
    selesai = [t for t in D["tagihan"] if not t.get("aktif", True)]
    per_bulan = sum(t["jumlah"] * {"mingguan": 52 / 12, "bulanan": 1, "tiga_bulan": 1 / 3, "tahunan": 1 / 12}.get(t["tiap"], 0)
                    for t in aktif if t.get("jenis", "keluar") == "keluar")
    st.caption(f"Perkiraan beban tagihan berulang: **{rp(per_bulan)}** per bulan ({len(aktif)} aktif, termasuk pemasukan berulang).")
    if not aktif:
        st.info("Belum ada tagihan. Tambahkan di bawah.")
    for t in aktif:
        teks, kelas = status_tagihan(t)
        with st.container(key=f"tx_tg_{t['id']}"):
            st.markdown(
                f'<div class="rt"><div class="ic {t.get("jenis", "keluar")}">{"💰" if t.get("jenis") == "masuk" else "⏰"}</div><div class="isi"><div class="jd">{e(t["nama"])}</div>'
                f'<div class="mt">{fmt_iso(t["berikut"])} · {e(TIAP[t["tiap"]])} · {e(nama_dompet(t["dompet"]))} · {e(nama_kat(t["kategori"]))}'
                f'{" · 🔄 otomatis" if t.get("otomatis") else ""}{" · " + e(t["catatan"]) if t.get("catatan") else ""}</div></div>'
                f'<div class="nom {t.get("jenis", "keluar")}">{rp(t["jumlah"])}<div class="{kelas}" style="font-size:.76rem;font-weight:600">{teks}</div></div></div>',
                unsafe_allow_html=True)
            if hanya_lihat():
                continue
            with st.container(key=f"aksi_tg_{t['id']}"):
                c = st.columns([1, 1, 1, 1, 3])
                c[0].button("Terima" if t.get("jenis") == "masuk" else "Bayar", key=f"bayar_{t['id']}", on_click=atur, args=("bayar_ftg", t["id"]))
                c[1].button("Lewati", key=f"lewat_{t['id']}", on_click=atur, args=("lewat_tg", t["id"]))
                c[2].button("Ubah", key=f"kedit_tg_{t['id']}", on_click=atur, args=("edit_tg", t["id"]))
                c[3].button("Hapus", key=f"khapus_tg_{t['id']}", on_click=atur, args=("hapus_tg", t["id"]))
            if st.session_state.get("bayar_ftg") == t["id"]:
                tb = st.date_input("Tanggal bayar", value=hari_ini(), format="DD/MM/YYYY", key=f"tb_bayar_{t['id']}")
                a, b, _ = st.columns([1.3, 1, 4])
                if a.button(f"Catat bayar {rp(t['jumlah'])}", key=f"ya_by_{t['id']}", type="primary"):
                    st.session_state.pop("bayar_ftg", None)
                    _bayar(t, tb)
                b.button("Batal", key=f"batal_by_{t['id']}", on_click=atur, args=("bayar_ftg", None))
            if st.session_state.get("lewat_tg") == t["id"]:
                st.info("Lewati periode ini tanpa mencatat pengeluaran?")
                a, b, _ = st.columns([1, 1, 4])
                if a.button("Ya, lewati", key=f"ya_lw_{t['id']}", type="primary"):
                    st.session_state.pop("lewat_tg", None)
                    _lewati(t)
                b.button("Batal", key=f"batal_lw_{t['id']}", on_click=atur, args=("lewat_tg", None))
            if st.session_state.get("hapus_tg") == t["id"]:
                st.warning("Hapus tagihan ini? Transaksi yang sudah tercatat tidak ikut terhapus.")
                a, b, _ = st.columns([1, 1, 4])
                if a.button("Ya, hapus", key=f"ya_ht_{t['id']}", type="primary"):
                    D["tagihan"] = [x for x in D["tagihan"] if x["id"] != t["id"]]
                    catat("tagihan", f"Hapus tagihan {t['nama']}")
                    selesai_simpan("Tagihan dihapus.", hapus_tg=None)
                b.button("Batal", key=f"batal_ht_{t['id']}", on_click=atur, args=("hapus_tg", None))
    if hanya_lihat():
        return
    edit = next((x for x in D["tagihan"] if x["id"] == st.session_state.get("edit_tg")), None)
    with st.container(key="kartu_g_form_tg"):
        st.markdown(f"**{'Ubah tagihan' if edit else 'Tambah tagihan'}**")
        _form(edit)
        if edit and st.button("Batal ubah", key="batal_ubah_tg"):
            st.session_state.pop("edit_tg", None)
            st.rerun()
    if selesai:
        with st.expander(f"Tagihan sekali saja yang sudah selesai ({len(selesai)})"):
            for t in selesai:
                st.markdown(f'<div class="perhatian"><b>{e(t["nama"])}</b> · {rp(t["jumlah"])} · jatuh tempo {fmt_iso(t["berikut"])}</div>',
                            unsafe_allow_html=True)
