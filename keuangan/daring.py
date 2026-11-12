"""Platform beli online (GoFood, GrabFood, ShopeeFood, dst): daftar yang bisa diatur sendiri dan ringkasan online vs offline."""
import streamlit as st

from keuangan.bantu import (
    atur, catat, deretan_stat, e, f_platform, kartu_stat, nama_platform, selesai_simpan, transaksi_platform, versi,
)
from keuangan.inti import D, _slug, baru_id, hanya_lihat, rp

KAT_BIAYA = "k_biaya_online"
# (kunci isian, nama sub kategori)
BIAYA_ONLINE = (("ong", "Ongkir"), ("lay", "Biaya layanan dan admin"), ("kms", "Biaya pengemasan"), ("rst", "Biaya tambahan resto"),
                ("asu", "Asuransi"), ("lain", "Biaya lain"))


def id_sub_biaya(kunci: str) -> str:
    return f"{KAT_BIAYA}__{_slug(dict(BIAYA_ONLINE)[kunci])}"


def pastikan_kategori_biaya():
    """Buat kategori 'Biaya pesan online' beserta subnya bila belum ada (atau sudah terhapus). Pemanggil yang commit."""
    ada = {k["id"] for k in D["kategori"]}
    if KAT_BIAYA not in ada:
        D["kategori"].append({"id": KAT_BIAYA, "nama": "Biaya pesan online", "jenis": "keluar", "induk": "", "ikon": "🛵", "warna": "#0e9f8e"})
    for kunci, nama in BIAYA_ONLINE:
        if id_sub_biaya(kunci) not in ada:
            D["kategori"].append({"id": id_sub_biaya(kunci), "nama": nama, "jenis": "keluar", "induk": KAT_BIAYA, "ikon": "🛵", "warna": "#0e9f8e"})


def baris_biaya(ong: int = 0, lay: int = 0, asu: int = 0, lain: int = 0, diskon_ongkir: int = 0, kms: int = 0, rst: int = 0) -> list:
    """Baris struk untuk biaya pesanan online. Diskon ongkir mengurangi ongkir saja (tidak lebih), bukan harga barang."""
    nilai = {"ong": max(0, int(ong or 0) - int(diskon_ongkir or 0)), "lay": int(lay or 0), "kms": int(kms or 0), "rst": int(rst or 0),
             "asu": int(asu or 0), "lain": int(lain or 0)}
    return [{"barang": "", "kategori": id_sub_biaya(k), "ket": nama, "qty": 1, "harga": nilai[k], "normal": 0, "asal": ""}
            for k, nama in BIAYA_ONLINE if nilai[k] > 0]


def ringkas_online(ts: list) -> dict:
    """Pengeluaran online vs offline dari kumpulan transaksi (satu struk dihitung satu pesanan).

    Kembalian: {"online": (pesanan, total), "offline": (pesanan, total), "per_platform": [(id, pesanan, total)]}
    """
    on, off, per = [0, 0], [0, 0], {}
    dilihat = set()
    biaya, biaya_per = 0, {}
    kat_biaya = {KAT_BIAYA} | {k["id"] for k in D["kategori"] if k.get("induk") == KAT_BIAYA}
    for t in ts:
        if t["jenis"] != "keluar":
            continue
        if t.get("platform") and t.get("kategori") in kat_biaya:
            biaya += int(t["jumlah"])
            biaya_per[t["platform"]] = biaya_per.get(t["platform"], 0) + int(t["jumlah"])
        kunci = t.get("grup") or t["id"]
        jml = int(t["jumlah"])
        sasaran = on if t.get("platform") else off
        sasaran[1] += jml
        if t.get("platform"):
            p = per.setdefault(t["platform"], [0, 0])
            p[1] += jml
        if kunci not in dilihat:
            dilihat.add(kunci)
            sasaran[0] += 1
            if t.get("platform"):
                per[t["platform"]][0] += 1
    return {"online": tuple(on), "offline": tuple(off), "biaya": biaya, "biaya_platform": biaya_per,
            "per_platform": sorted(((i, v[0], v[1]) for i, v in per.items()), key=lambda x: -x[2])}


def teks_online(ts: list) -> str:
    """Satu kalimat ringkas, '' bila belum ada belanja online."""
    r = ringkas_online(ts)
    n, total = r["online"]
    if not n:
        return ""
    semua = total + r["offline"][1]
    persen = round(total / semua * 100) if semua else 0
    return f"Belanja online {rp(total)} dalam {n} pesanan ({persen}% dari pengeluaran), offline {rp(r['offline'][1])}."


def kartu_online(ts: list, kunci: str = "kartu_g_br_online"):
    """Kartu ringkasan online vs offline untuk Beranda dan Laporan. Tidak tampil bila belum ada belanja online."""
    r = ringkas_online(ts)
    if not r["online"][0]:
        return
    with st.container(key=kunci):
        st.markdown("**Belanja online vs offline**")
        (n_on, t_on), (n_off, t_off) = r["online"], r["offline"]
        semua = t_on + t_off
        deretan_stat(kartu_stat("Online", rp(t_on), f"{n_on} pesanan", "m"), kartu_stat("Offline", rp(t_off), f"{n_off} transaksi"))
        if semua:
            st.caption(f"{round(t_on / semua * 100)}% pengeluaran lewat aplikasi.")
        if r["biaya"] and t_on:
            st.caption(f"Biaya pesan (ongkir, layanan, kemasan, dan lain-lain) {rp(r['biaya'])}, {round(r['biaya'] / t_on * 100)}% dari belanja online.")
        for i, n, total in r["per_platform"]:
            st.caption(f"{nama_platform(i)} · {rp(total)} · {n} pesanan" + (f" · biaya pesan {rp(r['biaya_platform'][i])}" if r["biaya_platform"].get(i) else ""))


def _dipakai(id_) -> int:
    return len(transaksi_platform(id_)) + sum(1 for x in D["templat"] if x.get("platform") == id_)


def _hapus(p: dict):
    n = _dipakai(p["id"])
    if not n:
        st.warning(f"Hapus platform {p['nama']}?")
        a, b, _ = st.columns([1, 1, 4])
        if a.button("Ya, hapus", key=f"ya_pl_{p['id']}", type="primary"):
            D["platform"] = [x for x in D["platform"] if x["id"] != p["id"]]
            catat("platform", f"Hapus platform {p['nama']}")
            selesai_simpan("Platform dihapus.", hapus_platform=None)
        b.button("Batal", key=f"batal_pl_{p['id']}", on_click=atur, args=("hapus_platform", None))
        return
    st.warning(f"{p['nama']} dipakai di {n} transaksi atau templat. Pindahkan ke platform lain, atau kosongkan "
               "(transaksinya dianggap beli langsung) sebelum dihapus.")
    lain = [""] + [x["id"] for x in D["platform"] if x["id"] != p["id"]]
    ganti = st.selectbox("Pindahkan ke", lain, key=f"pl_gab_{p['id']}", format_func=f_platform({"": "(kosongkan, jadi beli langsung)"}))
    a, b, _ = st.columns([1.3, 1, 4])
    if a.button("Pindah dan hapus", key=f"ya_pl_{p['id']}", type="primary"):
        for t in list(D["transaksi"]) + list(D["templat"]) + [s["transaksi"] for s in D["sampah"]]:
            if t.get("platform") == p["id"]:
                if ganti:
                    t["platform"] = ganti
                else:
                    t.pop("platform", None)
        D["platform"] = [x for x in D["platform"] if x["id"] != p["id"]]
        catat("platform", f"Hapus platform {p['nama']}, {n} data dipindah ke {nama_platform(ganti) or 'beli langsung'}")
        selesai_simpan("Platform dihapus.", hapus_platform=None)
    b.button("Batal", key=f"batal_pl_{p['id']}", on_click=atur, args=("hapus_platform", None))


def halaman_platform():
    with st.container(key="kartu_g_daftar_platform"):
        st.markdown('<div class="dh"><span class="dt">Platform beli online</span><span class="dn">%d</span></div>'
                    '<div class="dd">Aplikasi tempat Anda memesan makanan atau barang. Saat mencatat, platform bisa dipilih supaya '
                    'belanja online terpisah dari belanja langsung.</div>' % len(D["platform"]), unsafe_allow_html=True)
        if not D["platform"]:
            st.caption("Belum ada platform. Tambah di bawah.")
        for p in sorted(D["platform"], key=lambda x: x["nama"].lower()):
            ts = [t for t in transaksi_platform(p["id"]) if t["jenis"] == "keluar"]
            total = sum(int(t["jumlah"]) for t in ts)
            c = st.columns([1, 0.001, 0.001])
            c[0].markdown(f'<div class="itm"><div class="isi"><div class="jd">🛵 {e(p["nama"])}</div>'
                          f'<div class="mt">{len(ts)} transaksi · total {rp(total)}</div></div></div>', unsafe_allow_html=True)
            if not hanya_lihat():
                c[1].button("Ubah", key=f"ub_pl_{p['id']}", on_click=atur, args=("edit_platform", p["id"]))
                c[2].button("Hapus", key=f"hp_pl_{p['id']}", on_click=atur, args=("hapus_platform", p["id"]))
            if st.session_state.get("hapus_platform") == p["id"] and not hanya_lihat():
                _hapus(p)
        if hanya_lihat():
            return
        edit = next((x for x in D["platform"] if x["id"] == st.session_state.get("edit_platform")), None)
        with st.form(f"f_platform_{versi()}_{edit['id'] if edit else 'baru'}", clear_on_submit=not edit):
            st.markdown(f"**{'Ubah platform' if edit else 'Tambah platform'}**")
            nama = st.text_input("Nama", value=edit["nama"] if edit else "", max_chars=40, placeholder="Contoh: GoFood, Tokopedia, Maxim")
            if st.form_submit_button("Simpan perubahan" if edit else "Tambah", type="primary"):
                if not nama.strip():
                    st.error("Isi nama platform.")
                elif any(x["nama"].strip().lower() == nama.strip().lower() and x is not edit for x in D["platform"]):
                    st.error("Sudah ada platform dengan nama itu.")
                else:
                    if edit:
                        lama = edit["nama"]
                        edit["nama"] = nama.strip()
                        catat("platform", f"Ubah platform {lama} → {nama.strip()}")
                    else:
                        D["platform"].append({"id": baru_id(), "nama": nama.strip()})
                        catat("platform", f"Tambah platform {nama.strip()}")
                    selesai_simpan("Platform disimpan.", edit_platform=None)
        if edit and st.button("Batal ubah", key="batal_ubah_pl"):
            st.session_state.pop("edit_platform", None)
            st.rerun()
