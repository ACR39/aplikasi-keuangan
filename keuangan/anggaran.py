"""Anggaran bulanan per kategori pengeluaran."""
import streamlit as st

from keuangan.bantu import (
    f_kat, kat_dari, toko_dari,
    atur, batang, catat, deretan_stat, e, ikon_kat, kartu_stat, kategori_jenis, nama_kat, per_kategori, pilih_bulan,
    selesai_simpan, turunan, versi,
)
from keuangan.inti import D, baru_id, hanya_lihat, nama_bulan, rp


def batas_harian() -> int:
    """Batas pengeluaran per hari (Rp); 0 bila tidak dipakai."""
    try:
        return max(0, int(D.get("pengaturan", {}).get("batas_harian", 0) or 0))
    except (TypeError, ValueError):
        return 0


def keluar_pada(tgl: str) -> int:
    """Pengeluaran pada tanggal ISO tertentu (termasuk biaya transfer)."""
    return sum(int(t["jumlah"]) if t["jenis"] == "keluar" else int(t.get("biaya", 0) or 0)
               for t in D["transaksi"] if t["tgl"] == tgl and t["jenis"] in ("keluar", "transfer"))


def jatah_hari_ini():
    """(terpakai, batas, persen) untuk hari ini, atau None bila batas harian tidak dipakai."""
    b = batas_harian()
    if not b:
        return None
    from keuangan.inti import hari_ini
    p = keluar_pada(hari_ini().isoformat())
    return p, b, p / b * 100


def teks_jatah() -> str:
    """Kalimat singkat sisa jatah hari ini untuk pesan setelah mencatat; '' bila tidak dipakai."""
    j = jatah_hari_ini()
    if not j:
        return ""
    p, b, _ = j
    return f"Sisa jatah hari ini {rp(b - p)}" if p <= b else f"Melewati jatah hari ini {rp(p - b)}"


def hari_melewati(ym: str) -> int:
    """Jumlah hari pada bulan ym yang pengeluarannya melewati batas harian."""
    b = batas_harian()
    if not b:
        return 0
    per = {}
    for t in D["transaksi"]:
        if t["tgl"][:7] == ym and t["jenis"] in ("keluar", "transfer"):
            per[t["tgl"]] = per.get(t["tgl"], 0) + (int(t["jumlah"]) if t["jenis"] == "keluar" else int(t.get("biaya", 0) or 0))
    return sum(1 for v in per.values() if v > b)


def _form_harian():
    b = batas_harian()
    with st.expander("📅 Batas pengeluaran harian" + (f" · {rp(b)}" if b else ""), expanded=False):
        st.caption("Jatah belanja per hari. Muncul di Beranda sebagai sisa jatah hari ini, dan diingatkan saat hampir atau sudah lewat. "
                   "Isi 0 untuk mematikan.")
        with st.form(f"f_harian_{versi()}"):
            nilai = st.number_input("Batas per hari (Rp)", min_value=0, step=10000, value=b, disabled=hanya_lihat())
            if st.form_submit_button("Simpan batas harian", type="primary", disabled=hanya_lihat()):
                D["pengaturan"]["batas_harian"] = int(nilai)
                catat("anggaran", f"Batas pengeluaran harian {rp(nilai)}" if nilai else "Matikan batas pengeluaran harian")
                selesai_simpan("Batas harian disimpan.")


TIAP_PILIH = ('kategori', 'toko', 'barang')
TIPE_AG = {"kategori": "Kategori", "toko": "Toko", "barang": "Barang"}


def tipe_ag(a: dict) -> str:
    return a.get("tipe", "kategori")


def target_ag(a: dict) -> str:
    return a["kategori"] if tipe_ag(a) == "kategori" else a.get("target", "")


def label_ag(a: dict) -> str:
    """Nama anggaran: kategori, toko, atau barang yang dibatasi."""
    from keuangan.bantu import barang_dari, toko_dari
    tp = tipe_ag(a)
    if tp == "toko":
        return f"Toko {(toko_dari(target_ag(a)) or {}).get('nama', '(dihapus)')}"
    if tp == "barang":
        return f"Barang {(barang_dari(target_ag(a)) or {}).get('nama', '(dihapus)')}"
    return nama_kat(a["kategori"])


def ikon_ag(a: dict) -> str:
    return {"toko": "🏪 ", "barang": "🛒 "}.get(tipe_ag(a)) or ikon_kat(a["kategori"])


def status_anggaran(ym: str) -> list:
    """[(anggaran, terpakai, persen)] diurutkan dari yang paling penuh."""
    pakai = per_kategori(ym, "keluar")
    bulan_ini = [t for t in D["transaksi"] if t["jenis"] == "keluar" and t["tgl"][:7] == ym]

    def dipakai(a):
        tp, tg = tipe_ag(a), target_ag(a)
        if tp == "toko":
            return sum(int(t["jumlah"]) for t in bulan_ini if t.get("toko") == tg)
        if tp == "barang":
            return sum(int(t["jumlah"]) for t in bulan_ini if t.get("barang") == tg)
        return sum(pakai.get(i, 0) for i in turunan(a["kategori"]))
    hasil = [(a, dipakai(a), (dipakai(a) / a["batas"] * 100) if a["batas"] else 0) for a in D["anggaran"]]
    return sorted(hasil, key=lambda x: -x[2])


def halaman_anggaran():
    _form_harian()
    ym = pilih_bulan("ag_bulan")
    daftar = status_anggaran(ym)
    total_b = sum(a["batas"] for a, _, _ in daftar)
    total_p = sum(p for _, p, _ in daftar)
    deretan_stat(kartu_stat("Total anggaran", rp(total_b)), kartu_stat("Terpakai", rp(total_p), kelas="m" if total_p > total_b else ""),
                 kartu_stat("Sisa", rp(total_b - total_p), kelas="g" if total_b >= total_p else "m"),
                 kartu_stat("Kategori", str(len(daftar))))
    if not daftar:
        st.info("Belum ada anggaran. Tambahkan batas pengeluaran per kategori di bawah.")
    with st.container(key="kartu_g_anggaran"):
        for a, pakai, persen in daftar:
            st.markdown(
                f'<div class="perhatian"><div class="ag"><b>{ikon_ag(a)}{e(label_ag(a))}</b>'
                f'<span>{rp(pakai)} dari {rp(a["batas"])} · <b>{persen:.0f}%</b></span></div>{batang(pakai, a["batas"])}'
                f'<div class="ag"><span>{"Lewat " + rp(pakai - a["batas"]) if pakai > a["batas"] else "Sisa " + rp(a["batas"] - pakai)}</span></div></div>',
                unsafe_allow_html=True)
            if not hanya_lihat():
                c1, c2, _ = st.columns([1, 1, 4])
                c1.button("Ubah", key=f"kedit_ag_{a['id']}", on_click=atur, args=("edit_ag", a["id"]))
                c2.button("Hapus", key=f"khapus_ag_{a['id']}", on_click=atur, args=("hapus_ag", a["id"]))
                if st.session_state.get("hapus_ag") == a["id"]:
                    st.warning(f"Hapus anggaran {label_ag(a)}? Transaksi tidak ikut terhapus.")
                    y, b, _ = st.columns([1, 1, 4])
                    if y.button("Ya, hapus", key=f"ya_ag_{a['id']}", type="primary"):
                        D["anggaran"] = [x for x in D["anggaran"] if x["id"] != a["id"]]
                        catat("anggaran", f"Hapus anggaran {label_ag(a)}")
                        selesai_simpan("Anggaran dihapus.", hapus_ag=None)
                    b.button("Batal", key=f"batal_ag_{a['id']}", on_click=atur, args=("hapus_ag", None))
    if hanya_lihat():
        return
    edit = next((x for x in D["anggaran"] if x["id"] == st.session_state.get("edit_ag")), None)
    from keuangan.bantu import barang_dari
    with st.container(key="kartu_g_form_ag"):
        st.markdown(f"**{'Ubah anggaran' if edit else 'Tambah anggaran'}**")
        tipe = st.radio("Batasi per", list(TIAP_PILIH), horizontal=True, format_func=TIPE_AG.get,
                        index=list(TIAP_PILIH).index(tipe_ag(edit)) if edit else 0, key=f"ag_tipe_{versi()}_{edit['id'] if edit else 'baru'}",
                        disabled=bool(edit), help="Selain kategori, bisa juga membatasi belanja di satu toko atau untuk satu barang, misalnya kopi.")
        pakai_id = {target_ag(x) for x in D["anggaran"] if tipe_ag(x) == tipe and (not edit or x["id"] != edit["id"])}
        if tipe == "kategori":
            ids = [k["id"] for k in kategori_jenis("keluar") if k["id"] not in pakai_id]
            nama = f_kat()
        elif tipe == "toko":
            ids = [x["id"] for x in sorted(D["toko"], key=lambda x: x["nama"].lower()) if x["id"] not in pakai_id]
            nama = lambda i: (toko_dari(i) or {}).get("nama", i)
        else:
            ids = [b_["id"] for b_ in sorted(D["barang"], key=lambda x: x["nama"].lower())
                   if b_["id"] not in pakai_id and (kat_dari(b_["kategori"]) or {}).get("jenis", "keluar") == "keluar"]
            nama = lambda i: (barang_dari(i) or {}).get("nama", i)
        if not ids:
            st.caption({"kategori": "Semua kategori pengeluaran sudah punya anggaran.", "toko": "Belum ada toko, atau semua toko sudah punya anggaran.",
                        "barang": "Belum ada barang, atau semua barang sudah punya anggaran."}[tipe])
            return
        with st.form(f"f_ag_{versi()}_{edit['id'] if edit else 'baru'}_{tipe}", clear_on_submit=True):
            c1, c2 = st.columns(2)
            awal_t = target_ag(edit) if edit and tipe_ag(edit) == tipe else ids[0]
            tg = c1.selectbox(TIPE_AG[tipe], ids, index=ids.index(awal_t) if awal_t in ids else 0, format_func=nama)
            batas = c2.number_input("Batas per bulan (Rp)", min_value=0, step=50000, value=int(edit["batas"]) if edit else 0)
            if st.form_submit_button("Simpan perubahan" if edit else "Tambah", type="primary"):
                if batas <= 0:
                    st.error("Batas harus lebih dari nol.")
                else:
                    isi = {"tipe": tipe, "target": "" if tipe == "kategori" else tg, "kategori": tg if tipe == "kategori" else "", "batas": int(batas)}
                    if edit:
                        edit.update(isi)
                    else:
                        D["anggaran"].append({"id": baru_id(), **isi})
                    catat("anggaran", f"Anggaran {label_ag(isi)} {rp(batas)} per bulan")
                    selesai_simpan("Anggaran disimpan.", edit_ag=None)
        if edit and st.button("Batal ubah", key="batal_ubah_ag"):
            st.session_state.pop("edit_ag", None)
            st.rerun()
        st.caption(f"Batas berlaku tiap bulan. Angka terpakai dihitung dari pengeluaran pada {nama_bulan(ym)}. Anggaran kategori utama sudah mencakup semua sub kategorinya. Anggaran toko dan barang menghitung semua pengeluaran yang tercatat dengan toko atau barang itu.")
