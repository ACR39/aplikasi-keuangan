"""Acara dan proyek: label lintas kategori (Liburan Bali, Renovasi, Lebaran) untuk melihat total biaya satu keperluan."""
import streamlit as st

from keuangan.bantu import atur, catat, deretan_stat, e, f_kat, kartu_stat, nama_kat, selesai_simpan, versi, akar, baris_transaksi, kunci_urut
from keuangan.inti import D, baru_id, fmt_iso, hanya_lihat, rp


def acara_dari(id_):
    return next((a for a in D.get("acara", []) if a["id"] == id_), None)


def nama_acara(id_) -> str:
    a = acara_dari(id_)
    return a["nama"] if a else ("" if not id_ else "(acara dihapus)")


def f_acara(tambahan: dict | None = None):
    tambahan = tambahan or {}
    return lambda i: tambahan[i] if i in tambahan else nama_acara(i)


def transaksi_acara(id_) -> list:
    return [t for t in D["transaksi"] if t.get("acara") == id_]


def opsi_acara(awal: str = "") -> list:
    """Id acara yang aktif, ditambah acara terpilih sebelumnya walau sudah selesai."""
    ids = [a["id"] for a in sorted(D.get("acara", []), key=lambda a: a["nama"].lower()) if a.get("aktif", True) or a["id"] == awal]
    return [""] + ids


def pilih_acara(kunci: str, awal: str = "", label: str = "Acara atau proyek (opsional)"):
    """Kotak pilihan acara. Kembalikan id (kosong = tanpa acara). Tidak tampil bila belum ada acara."""
    if not D.get("acara"):
        return awal or ""
    opsi = opsi_acara(awal)
    if awal and awal not in opsi:
        opsi.append(awal)
    return st.selectbox(label, opsi, index=opsi.index(awal) if awal in opsi else 0, format_func=f_acara({"": "(tanpa acara)"}), key=kunci,
                        help="Label lintas kategori, misalnya Liburan atau Renovasi. Atur daftarnya di Pantau > Acara.")


def ringkas(id_: str) -> dict:
    ts = transaksi_acara(id_)
    keluar = sum(t["jumlah"] for t in ts if t["jenis"] == "keluar")
    masuk = sum(t["jumlah"] for t in ts if t["jenis"] == "masuk")
    kat = {}
    for t in ts:
        if t["jenis"] == "keluar":
            k = akar(t.get("kategori")) or t.get("kategori") or ""
            kat[k] = kat.get(k, 0) + t["jumlah"]
    return {"n": len(ts), "keluar": keluar, "masuk": masuk, "kat": sorted(kat.items(), key=lambda x: -x[1]), "ts": ts}


def _lepas_label(id_: str) -> int:
    n = 0
    for t in D["transaksi"]:
        if t.get("acara") == id_:
            t.pop("acara")
            n += 1
    return n


def _form_acara(edit: dict | None):
    with st.form(f"form_acara_{edit['id'] if edit else 'baru'}_{versi()}", clear_on_submit=not edit):
        nama = st.text_input("Nama acara atau proyek", value=(edit or {}).get("nama", ""), max_chars=40, placeholder="Contoh: Liburan Bali, Renovasi dapur")
        c1, c2 = st.columns(2)
        mulai = c1.text_input("Mulai (opsional, YYYY-MM-DD)", value=(edit or {}).get("mulai", ""), max_chars=10)
        selesai = c2.text_input("Selesai (opsional, YYYY-MM-DD)", value=(edit or {}).get("selesai", ""), max_chars=10)
        anggaran = st.number_input("Perkiraan biaya (Rp), opsional", min_value=0, step=100000, value=int((edit or {}).get("anggaran", 0) or 0),
                                   help="Dibandingkan dengan pengeluaran sebenarnya.")
        catatan = st.text_input("Catatan, opsional", value=(edit or {}).get("catatan", ""), max_chars=120)
        aktif = st.checkbox("Masih berjalan (muncul di pilihan saat mencatat)", value=(edit or {}).get("aktif", True))
        kirim = st.form_submit_button("Simpan perubahan" if edit else "Tambah acara", type="primary")
    if not kirim:
        return
    nama = nama.strip()
    if not nama:
        st.error("Nama acara wajib diisi.")
        return
    if any(a["nama"].lower() == nama.lower() and a["id"] != (edit or {}).get("id") for a in D["acara"]):
        st.error("Sudah ada acara dengan nama itu.")
        return
    for lab, v in (("Mulai", mulai.strip()), ("Selesai", selesai.strip())):
        if v:
            from keuangan.inti import iso_ke_date
            if not iso_ke_date(v):
                st.error(f"{lab}: tulis tanggal seperti 2026-12-31 atau kosongkan.")
                return
    isi = {"nama": nama, "mulai": mulai.strip(), "selesai": selesai.strip(), "anggaran": int(anggaran), "catatan": catatan.strip(), "aktif": bool(aktif)}
    if edit:
        edit.update(isi)
        catat("ubah", f"Ubah acara {nama}")
        selesai_simpan("Acara diubah.", edit_acara=None)
    else:
        D["acara"].append({"id": baru_id(), **isi})
        catat("tambah", f"Acara baru {nama}")
        selesai_simpan("Acara ditambahkan.")


def halaman_acara():
    ro = hanya_lihat()
    edit = next((a for a in D["acara"] if a["id"] == st.session_state.get("edit_acara")), None)
    if not ro:
        with st.expander("✏️ Ubah acara" if edit else "➕ Tambah acara", expanded=bool(edit) or not D["acara"]):
            _form_acara(edit)
            if edit:
                st.button("Batal", key="batal_acara", on_click=atur, args=("edit_acara", None))
    if not D["acara"]:
        st.info("Belum ada acara. Tambahkan satu, lalu pilih saat mencatat transaksi atau struk.")
        return
    semua = {a["id"]: ringkas(a["id"]) for a in D["acara"]}
    deretan_stat(kartu_stat("Acara", str(len(D["acara"]))),
                 kartu_stat("Total pengeluaran", rp(sum(r["keluar"] for r in semua.values())), kelas="m"),
                 kartu_stat("Berjalan", str(sum(1 for a in D["acara"] if a.get("aktif", True)))))
    for a in sorted(D["acara"], key=lambda a: (not a.get("aktif", True), a["nama"].lower())):
        r = semua[a["id"]]
        rentang = " – ".join(x for x in (fmt_iso(a["mulai"]) if a.get("mulai") else "", fmt_iso(a["selesai"]) if a.get("selesai") else "") if x)
        with st.container(key=f"acara_{a['id']}", border=True):
            st.markdown(f"**🏷️ {e(a['nama'])}**" + ("" if a.get("aktif", True) else " · selesai") + (f" · {rentang}" if rentang else ""), unsafe_allow_html=True)
            ket = f"{r['n']} transaksi · pengeluaran {rp(r['keluar'])}" + (f" · pemasukan {rp(r['masuk'])}" if r["masuk"] else "")
            st.caption(ket + (f" · {a['catatan']}" if a.get("catatan") else ""))
            if a.get("anggaran"):
                st.markdown(f'<div class="perhatian">Perkiraan {rp(a["anggaran"])}: terpakai {rp(r["keluar"])} '
                            f'({r["keluar"] * 100 / a["anggaran"]:.0f}%), {"sisa " + rp(a["anggaran"] - r["keluar"]) if r["keluar"] <= a["anggaran"] else "lewat " + rp(r["keluar"] - a["anggaran"])}</div>',
                            unsafe_allow_html=True)
            with st.expander("Rincian"):
                if r["kat"]:
                    st.markdown("**Per kategori**")
                    for k, v in r["kat"]:
                        st.markdown(f'<div class="perhatian">{e(nama_kat(k) or "Tanpa kategori")}: <b>{rp(v)}</b></div>', unsafe_allow_html=True)
                for t in sorted(r["ts"], key=kunci_urut, reverse=True)[:40]:
                    st.markdown(baris_transaksi(t), unsafe_allow_html=True)
                if len(r["ts"]) > 40:
                    st.caption(f"Menampilkan 40 dari {len(r['ts'])} transaksi terbaru. Gunakan filter Acara di Daftar transaksi untuk semuanya.")
            if not ro:
                c1, c2 = st.columns(2)
                c1.button("Ubah", key=f"ubah_acara_{a['id']}", on_click=atur, args=("edit_acara", a["id"]))
                if st.session_state.get("hapus_acara") == a["id"]:
                    st.warning(f"Hapus acara ini? Label dilepas dari {r['n']} transaksi; transaksinya tetap ada.")
                    ya, tdk = st.columns(2)
                    if ya.button("Ya, hapus", key=f"ya_acara_{a['id']}", type="primary"):
                        n = _lepas_label(a["id"])
                        D["acara"] = [x for x in D["acara"] if x["id"] != a["id"]]
                        catat("hapus", f"Hapus acara {a['nama']} ({n} transaksi dilepas)")
                        selesai_simpan("Acara dihapus.", hapus_acara=None)
                    tdk.button("Batal", key=f"tdk_acara_{a['id']}", on_click=atur, args=("hapus_acara", None))
                else:
                    c2.button("Hapus", key=f"hapus_acara_{a['id']}", on_click=atur, args=("hapus_acara", a["id"]))
