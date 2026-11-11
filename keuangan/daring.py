"""Platform beli online (GoFood, GrabFood, ShopeeFood, dst): daftar yang bisa diatur sendiri dan ringkasan online vs offline."""
import streamlit as st

from keuangan.bantu import (
    atur, catat, deretan_stat, e, f_platform, kartu_stat, nama_platform, selesai_simpan, transaksi_platform, versi,
)
from keuangan.inti import D, baru_id, hanya_lihat, rp


def ringkas_online(ts: list) -> dict:
    """Pengeluaran online vs offline dari kumpulan transaksi (satu struk dihitung satu pesanan).

    Kembalian: {"online": (pesanan, total), "offline": (pesanan, total), "per_platform": [(id, pesanan, total)]}
    """
    on, off, per = [0, 0], [0, 0], {}
    dilihat = set()
    for t in ts:
        if t["jenis"] != "keluar":
            continue
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
    return {"online": tuple(on), "offline": tuple(off),
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
        for i, n, total in r["per_platform"]:
            st.caption(f"{nama_platform(i)} · {rp(total)} · {n} pesanan")


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
