"""Anggaran amplop: pemasukan dibagi ke amplop (jatah per bulan), tiap pengeluaran memotong amplop kategorinya."""
import streamlit as st

from keuangan.bantu import akar, atur, batang, catat, deretan_stat, e, f_kat, kartu_stat, kategori_utama, nama_kat, selesai_simpan, versi
from keuangan.inti import D, baru_id, hanya_lihat, hari_ini, rp


def _geser(ym: str, n: int) -> str:
    i = int(ym[:4]) * 12 + int(ym[5:]) - 1 + n
    return f"{i // 12}-{i % 12 + 1:02d}"


def terpakai(a: dict, ym: str) -> int:
    ids = set(a.get("kategori", []))
    return sum(int(t["jumlah"]) for t in D["transaksi"]
               if t["jenis"] == "keluar" and t["tgl"][:7] == ym and t.get("kategori") and akar(t["kategori"]) in ids)


def bawaan(a: dict, ym: str) -> int:
    """Sisa dari bulan-bulan sebelumnya (hanya yang bersisa, maksimal 12 bulan ke belakang) bila amplop diberi 'bawa sisa'."""
    if not a.get("bawa"):
        return 0
    mulai = a.get("mulai") or ym
    total, bln = 0, _geser(ym, -1)
    for _ in range(12):
        if bln < mulai:
            break
        total += max(0, int(a["jatah"]) - terpakai(a, bln))
        bln = _geser(bln, -1)
    return total


def hitung(a: dict, ym: str) -> dict:
    pakai, bawa = terpakai(a, ym), bawaan(a, ym)
    tersedia = int(a["jatah"]) + bawa
    return {"pakai": pakai, "bawa": bawa, "tersedia": tersedia, "sisa": tersedia - pakai}


def ringkas(ym: str) -> dict:
    masuk = sum(int(t["jumlah"]) for t in D["transaksi"] if t["jenis"] == "masuk" and t["tgl"][:7] == ym)
    jatah = sum(int(a["jatah"]) for a in D["amplop"])
    return {"masuk": masuk, "jatah": jatah, "belum": masuk - jatah}


def _baris_amplop(a: dict, ym: str):
    r = hitung(a, ym)
    kat = ", ".join(nama_kat(k) for k in a.get("kategori", [])) or "belum ada kategori"
    st.markdown(f'<div class="ag"><b>{e(a["nama"])}</b><span>{rp(r["pakai"])} / {rp(r["tersedia"])}</span></div>{batang(r["pakai"], r["tersedia"])}',
                unsafe_allow_html=True)
    st.markdown(f'<div class="sc-ket">{"Sisa " + e(rp(r["sisa"])) if r["sisa"] >= 0 else "Lewat " + e(rp(-r["sisa"]))}'
                + (f' · termasuk bawaan {e(rp(r["bawa"]))}' if r["bawa"] else "") + f' · {e(kat)}</div>', unsafe_allow_html=True)


def kartu_amplop():
    if not D["amplop"]:
        return
    ym = hari_ini().strftime("%Y-%m")
    with st.container(key="kartu_g_br_amplop"):
        st.markdown("**Amplop bulan ini**")
        for a in D["amplop"]:
            _baris_amplop(a, ym)
            st.markdown('<div style="height:.5rem"></div>', unsafe_allow_html=True)


def _form(edit: dict | None):
    dipakai = {k for a in D["amplop"] if a is not edit for k in a.get("kategori", [])}
    opsi = [k["id"] for k in kategori_utama("keluar") if k["id"] not in dipakai]
    with st.form(f"f_amp_{(edit or {}).get('id', 'baru')}_{versi()}"):
        nama = st.text_input("Nama amplop", value=(edit or {}).get("nama", ""), placeholder="Makan, transport, hiburan")
        jatah = st.number_input("Jatah per bulan (Rp)", min_value=0, step=50000, value=int((edit or {}).get("jatah", 0)))
        awal = [k for k in (edit or {}).get("kategori", []) if k in opsi]
        kat = st.multiselect("Kategori yang memotong amplop ini", opsi, default=awal, format_func=f_kat())
        bawa = st.checkbox("Bawa sisa ke bulan berikutnya", value=bool((edit or {}).get("bawa", False)),
                           help="Sisa tiap bulan ditambahkan ke jatah bulan berikutnya. Kelebihan pakai tidak ikut dibawa.")
        if not st.form_submit_button("Simpan perubahan" if edit else "Tambah amplop", type="primary"):
            return
    if not nama.strip() or jatah <= 0:
        st.error("Isi nama amplop dan jatah lebih dari 0.")
        return
    isi = {"nama": nama.strip(), "jatah": int(jatah), "kategori": kat, "bawa": bool(bawa)}
    if edit:
        edit.update(isi)
        catat("amplop", f"Ubah amplop {isi['nama']}")
        selesai_simpan("Amplop diubah.", edit_amp=None)
    else:
        D["amplop"].append({"id": baru_id(), "mulai": hari_ini().strftime("%Y-%m"), **isi})
        catat("amplop", f"Tambah amplop {isi['nama']} {rp(isi['jatah'])}")
        selesai_simpan("Amplop ditambahkan.")


def halaman_amplop():
    ro = hanya_lihat()
    ym = hari_ini().strftime("%Y-%m")
    edit = next((a for a in D["amplop"] if a["id"] == st.session_state.get("edit_amp")), None)
    if not ro:
        with st.container():
            _form(edit)
            if edit:
                st.button("Batal", key="batal_amp", on_click=atur, args=("edit_amp", None))
    if not D["amplop"]:
        st.info("Belum ada amplop. Buat amplop (misalnya Makan Rp 1.500.000), pilih kategori yang memotongnya, lalu lihat sisanya tiap hari.")
        return
    r = ringkas(ym)
    deretan_stat(kartu_stat("Pemasukan bulan ini", rp(r["masuk"]), kelas="g"),
                 kartu_stat("Total jatah amplop", rp(r["jatah"])),
                 kartu_stat("Belum dibagi" if r["belum"] >= 0 else "Jatah kelebihan", rp(abs(r["belum"])), "dari pemasukan" if r["belum"] >= 0 else "melebihi pemasukan", "g" if r["belum"] >= 0 else "m"))
    for a in D["amplop"]:
        with st.container(key=f"amp_{a['id']}", border=True):
            _baris_amplop(a, ym)
            if ro:
                continue
            c1, c2 = st.columns(2)
            c1.button("Ubah", key=f"amp_u_{a['id']}", on_click=atur, args=("edit_amp", a["id"]))
            if st.session_state.get("hapus_amp") == a["id"]:
                st.warning(f"Hapus amplop {a['nama']}? Transaksi tidak ikut terhapus.")
                ya, tdk = st.columns(2)
                if ya.button("Ya, hapus", key=f"amp_ya_{a['id']}", type="primary"):
                    D["amplop"] = [x for x in D["amplop"] if x["id"] != a["id"]]
                    catat("amplop", f"Hapus amplop {a['nama']}")
                    selesai_simpan("Amplop dihapus.", hapus_amp=None)
                tdk.button("Batal", key=f"amp_tdk_{a['id']}", on_click=atur, args=("hapus_amp", None))
            else:
                c2.button("Hapus", key=f"amp_h_{a['id']}", on_click=atur, args=("hapus_amp", a["id"]))
    bebas = {akar(t["kategori"]) for t in D["transaksi"] if t["jenis"] == "keluar" and t["tgl"][:7] == ym and t.get("kategori")} - {k for a in D["amplop"] for k in a.get("kategori", [])}
    if bebas:
        st.caption("Pengeluaran bulan ini di luar amplop: " + ", ".join(nama_kat(k) for k in sorted(bebas)) + ".")
