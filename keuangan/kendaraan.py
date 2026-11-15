"""Kendaraan: catat kilometer dan liter saat isi BBM, hitung km per liter dan biaya per km, serta ingatkan servis dan pajak."""
from datetime import date

import pandas as pd
import streamlit as st

from keuangan.bantu import atur, catat, deretan_stat, e, kartu_stat, kunci_urut, selesai_simpan, versi
from keuangan.inti import D, baru_id, fmt_iso, hanya_lihat, hari_ini, iso_ke_date, rp

JENIS_KENDARAAN = ["Motor", "Mobil", "Lainnya"]


def kendaraan_dari(id_):
    return next((k for k in D.get("kendaraan", []) if k["id"] == id_), None)


def nama_kendaraan(id_) -> str:
    k = kendaraan_dari(id_)
    return (k["nama"] + (f' ({k["plat"]})' if k.get("plat") else "")) if k else ("" if not id_ else "(kendaraan dihapus)")


def f_kendaraan(tambahan: dict | None = None):
    tambahan = tambahan or {}
    return lambda i: tambahan[i] if i in tambahan else nama_kendaraan(i)


def transaksi_kendaraan(id_) -> list:
    return sorted([t for t in D["transaksi"] if t.get("kendaraan") == id_], key=lambda t: (t["tgl"], t.get("waktu", ""), t.get("dibuat", "")))


def odo_sekarang(id_) -> int:
    """Kilometer terbaru: terbesar dari odometer awal dan semua catatan kendaraan."""
    k = kendaraan_dari(id_) or {}
    return max([int(k.get("odo_awal") or 0)] + [int(t.get("odo") or 0) for t in D["transaksi"] if t.get("kendaraan") == id_])


def isian_kendaraan(kunci: str, awal: dict) -> dict:
    """Bagian form Catat transaksi (di dalam st.form). Kembalikan {} bila tak dipakai, atau isian kendaraan, odo, liter, penuh."""
    if not D.get("kendaraan"):
        return {}
    with st.expander("🚗 Kendaraan: BBM atau servis (opsional)", expanded=bool(awal.get("kendaraan"))):
        ids = [""] + [k["id"] for k in D["kendaraan"]]
        awal_k = awal.get("kendaraan", "")
        if awal_k and awal_k not in ids:
            ids.append(awal_k)
        kid = st.selectbox("Kendaraan", ids, index=ids.index(awal_k) if awal_k in ids else 0, format_func=f_kendaraan({"": "(bukan untuk kendaraan)"}), key=f"{kunci}_kend")
        c1, c2 = st.columns(2)
        odo = c1.number_input("Kilometer di odometer", min_value=0, step=1, value=int(awal.get("odo") or 0), key=f"{kunci}_odo",
                              help="Angka di odometer saat ini. Kosongkan (0) bila tidak dicatat.")
        liter = c2.number_input("Liter BBM", min_value=0.0, step=0.5, format="%g", value=float(awal.get("liter") or 0), key=f"{kunci}_liter",
                                help="Isi hanya untuk pembelian BBM; kosongkan untuk servis atau pajak.")
        penuh = st.checkbox("Tangki diisi penuh", value=not awal.get("sebagian"), key=f"{kunci}_penuh",
                            help="Km per liter dihitung dari dua pengisian penuh berurutan.")
    return {"kendaraan": kid, "odo": int(odo), "liter": float(liter), "penuh": bool(penuh)} if kid else {}


def pasang(t: dict, isi: dict):
    """Pasang atau lepas isian kendaraan pada transaksi t (dipakai saat ubah)."""
    for kk in ("kendaraan", "odo", "liter", "sebagian"):
        t.pop(kk, None)
    if isi.get("kendaraan"):
        t["kendaraan"] = isi["kendaraan"]
        if isi.get("odo"):
            t["odo"] = int(isi["odo"])
        if isi.get("liter"):
            t["liter"] = float(isi["liter"])
            if not isi.get("penuh", True):
                t["sebagian"] = True


def kait(isi: dict) -> dict:
    """Isian untuk tambah_transaksi (nilai kosong dibuang di sana)."""
    k = {"kendaraan": isi.get("kendaraan", ""), "odo": isi.get("odo", 0), "liter": isi.get("liter", 0)}
    if isi.get("liter") and not isi.get("penuh", True):
        k["sebagian"] = True  # hanya yang tidak penuh yang ditandai (nilai kosong tidak disimpan)
    return k


def isi_bbm(id_: str) -> list:
    """Pengisian BBM (ada liter) berurutan waktu, dengan km per liter dari isi penuh sebelumnya (kosong bila belum bisa dihitung)."""
    hasil = []
    ts = [t for t in transaksi_kendaraan(id_) if float(t.get("liter") or 0) > 0]
    terakhir_penuh = None  # odometer pengisian penuh sebelumnya
    liter_sejak, biaya_sejak = 0.0, 0
    for t in ts:
        liter_sejak += float(t["liter"])
        biaya_sejak += int(t["jumlah"])
        baris = {"id": t["id"], "tgl": t["tgl"], "odo": int(t.get("odo") or 0), "liter": float(t["liter"]), "jumlah": int(t["jumlah"]),
                 "per_liter": round(int(t["jumlah"]) / float(t["liter"])), "kmpl": None, "per_km": None, "penuh": not t.get("sebagian")}
        if baris["penuh"] and baris["odo"]:
            if terakhir_penuh is not None and baris["odo"] > terakhir_penuh:
                km = baris["odo"] - terakhir_penuh
                baris["kmpl"] = km / liter_sejak
                baris["per_km"] = biaya_sejak / km
            terakhir_penuh, liter_sejak, biaya_sejak = baris["odo"], 0.0, 0
        hasil.append(baris)
    return hasil


def statistik(id_: str) -> dict:
    ib = isi_bbm(id_)
    pasang_ = [b for b in ib if b["kmpl"]]
    ts = transaksi_kendaraan(id_)
    odos = [int(t["odo"]) for t in ts if t.get("odo")]
    km_tempuh = (max(odos) - min(odos)) if len(odos) >= 2 else 0
    total = sum(t["jumlah"] for t in ts if t["jenis"] == "keluar")
    bbm = sum(b["jumlah"] for b in ib)
    kmpl = (sum(b["kmpl"] * b["liter"] for b in pasang_) / sum(b["liter"] for b in pasang_)) if pasang_ else None
    return {"isi": ib, "kmpl": kmpl, "kmpl_terakhir": pasang_[-1]["kmpl"] if pasang_ else None,
            "per_km_bbm": (sum(b["per_km"] * 1 for b in pasang_) / len(pasang_)) if pasang_ else None,
            "km_tempuh": km_tempuh, "total": total, "bbm": bbm, "per_km_total": (total / km_tempuh) if km_tempuh and total else None,
            "odo": odo_sekarang(id_)}


# ---------------------------------------------------------------- pengingat servis dan pajak
def status_servis(k: dict, s: dict) -> tuple[str, int]:
    """(teks, urgensi) urgensi: 0 aman, 1 segera, 2 lewat. Berdasar kilometer dan/atau bulan sejak terakhir."""
    odo = odo_sekarang(k["id"])
    teks, urg = [], 0
    if s.get("tiap_km"):
        sisa = int(s.get("km_terakhir") or 0) + int(s["tiap_km"]) - odo
        if sisa < 0:
            teks.append(f"lewat {-sisa:,} km".replace(",", "."))
            urg = 2
        else:
            teks.append(f"{sisa:,} km lagi".replace(",", "."))
            if sisa <= max(200, int(s["tiap_km"]) // 10):
                urg = max(urg, 1)
    if s.get("tiap_bulan") and s.get("tgl_terakhir"):
        d0 = iso_ke_date(s["tgl_terakhir"])
        if d0:
            tahun, bulan = divmod(d0.month - 1 + int(s["tiap_bulan"]), 12)
            import calendar
            y, m = d0.year + tahun, bulan + 1
            jatuh = date(y, m, min(d0.day, calendar.monthrange(y, m)[1]))
            sisa_h = (jatuh - hari_ini()).days
            teks.append(f"lewat {-sisa_h} hari" if sisa_h < 0 else f"{sisa_h} hari lagi")
            urg = max(urg, 2 if sisa_h < 0 else 1 if sisa_h <= 14 else 0)
    return (" · ".join(teks) or "belum diatur"), urg


def baris_perhatian() -> list:
    baris = []
    for k in D.get("kendaraan", []):
        for s in k.get("servis", []):
            teks, urg = status_servis(k, s)
            if urg:
                baris.append(f'{"🔴" if urg == 2 else "🟡"} {e(k["nama"])}: <b>{e(s["nama"])}</b> {e(teks)}')
        if k.get("pajak"):
            d = iso_ke_date(k["pajak"])
            if d:
                n = (d - hari_ini()).days
                if n <= 30:
                    baris.append(f'{"🔴" if n < 0 else "🟡"} Pajak <b>{e(k["nama"])}</b> '
                                 + (f"lewat {-n} hari ({fmt_iso(k['pajak'])})" if n < 0 else f"jatuh tempo {n} hari lagi ({fmt_iso(k['pajak'])})"))
    return baris


# ---------------------------------------------------------------- halaman
def _form_kendaraan(edit: dict | None):
    with st.form(f"form_kend_{edit['id'] if edit else 'baru'}_{versi()}", clear_on_submit=not edit):
        c1, c2 = st.columns(2)
        nama = c1.text_input("Nama kendaraan", value=(edit or {}).get("nama", ""), max_chars=30, placeholder="Contoh: Vario, Avanza")
        plat = c2.text_input("Plat nomor (opsional)", value=(edit or {}).get("plat", ""), max_chars=12)
        c3, c4 = st.columns(2)
        jenis = c3.selectbox("Jenis", JENIS_KENDARAAN, index=JENIS_KENDARAAN.index((edit or {}).get("jenis", "Motor")) if (edit or {}).get("jenis", "Motor") in JENIS_KENDARAAN else 0)
        odo = c4.number_input("Odometer saat mulai dicatat (km)", min_value=0, step=100, value=int((edit or {}).get("odo_awal", 0) or 0))
        pajak = st.text_input("Jatuh tempo pajak (YYYY-MM-DD, opsional)", value=(edit or {}).get("pajak", ""), max_chars=10)
        kirim = st.form_submit_button("Simpan perubahan" if edit else "Tambah kendaraan", type="primary")
    if not kirim:
        return
    if not nama.strip():
        st.error("Nama kendaraan wajib diisi.")
        return
    if pajak.strip() and not iso_ke_date(pajak.strip()):
        st.error("Tanggal pajak: tulis seperti 2027-03-15 atau kosongkan.")
        return
    isi = {"nama": nama.strip(), "plat": plat.strip().upper(), "jenis": jenis, "odo_awal": int(odo), "pajak": pajak.strip()}
    if edit:
        edit.update(isi)
        catat("ubah", f"Ubah kendaraan {isi['nama']}")
        selesai_simpan("Kendaraan diubah.", edit_kend=None)
    else:
        D["kendaraan"].append({"id": baru_id(), "servis": [], **isi})
        catat("tambah", f"Kendaraan baru {isi['nama']}")
        selesai_simpan("Kendaraan ditambahkan.")


def _panel_servis(k: dict, ro: bool):
    st.markdown("**Pengingat servis**")
    if not k.get("servis"):
        st.caption("Belum ada. Tambahkan misalnya Ganti oli tiap 2.000 km atau 3 bulan.")
    odo = odo_sekarang(k["id"])
    for s in k.get("servis", []):
        teks, urg = status_servis(k, s)
        st.markdown(f'<div class="perhatian">{"🔴" if urg == 2 else "🟡" if urg else "🟢"} <b>{e(s["nama"])}</b> · {e(teks)}'
                    f'<br><span style="opacity:.7">Terakhir: {("km " + format(int(s.get("km_terakhir") or 0), ",").replace(",", ".")) if s.get("km_terakhir") else "-"}'
                    f'{" · " + fmt_iso(s["tgl_terakhir"]) if s.get("tgl_terakhir") else ""}</span></div>', unsafe_allow_html=True)
        if not ro:
            a, b, c = st.columns([2, 2, 1])
            km_baru = a.number_input("Km saat servis", min_value=0, step=100, value=odo, key=f"sv_km_{s['id']}", label_visibility="collapsed")
            if b.button("✅ Sudah dilakukan", key=f"sv_ok_{s['id']}"):
                s["km_terakhir"], s["tgl_terakhir"] = int(km_baru), hari_ini().isoformat()
                catat("ubah", f"Servis {s['nama']} {k['nama']} dilakukan di km {int(km_baru)}")
                selesai_simpan("Servis dicatat. Catat biayanya di Catat transaksi bila perlu.")
            if c.button("🗑", key=f"sv_del_{s['id']}", help="Hapus pengingat ini"):
                k["servis"] = [x for x in k["servis"] if x["id"] != s["id"]]
                selesai_simpan("Pengingat dihapus.")
    if not ro:
        with st.expander("➕ Tambah pengingat servis"):
            with st.form(f"form_sv_{k['id']}_{versi()}", clear_on_submit=True):
                nama = st.text_input("Nama", placeholder="Ganti oli, servis berkala, ganti ban", max_chars=40)
                c1, c2 = st.columns(2)
                tiap_km = c1.number_input("Tiap berapa km (0 = tidak dipakai)", min_value=0, step=500, value=0)
                tiap_bln = c2.number_input("Tiap berapa bulan (0 = tidak dipakai)", min_value=0, step=1, value=0)
                c3, c4 = st.columns(2)
                km_t = c3.number_input("Km terakhir dilakukan", min_value=0, step=100, value=odo)
                tgl_t = c4.date_input("Tanggal terakhir", value=hari_ini(), format="DD/MM/YYYY")
                if st.form_submit_button("Tambah pengingat", type="primary"):
                    if not nama.strip():
                        st.error("Nama wajib diisi.")
                    elif not tiap_km and not tiap_bln:
                        st.error("Isi tiap berapa km atau tiap berapa bulan.")
                    else:
                        k.setdefault("servis", []).append({"id": baru_id(), "nama": nama.strip(), "tiap_km": int(tiap_km), "tiap_bulan": int(tiap_bln),
                                                           "km_terakhir": int(km_t), "tgl_terakhir": tgl_t.isoformat()})
                        catat("tambah", f"Pengingat {nama.strip()} untuk {k['nama']}")
                        selesai_simpan("Pengingat ditambahkan.")


def halaman_kendaraan():
    ro = hanya_lihat()
    edit = kendaraan_dari(st.session_state.get("edit_kend"))
    if not ro:
        with st.expander("✏️ Ubah kendaraan" if edit else "➕ Tambah kendaraan", expanded=bool(edit) or not D["kendaraan"]):
            _form_kendaraan(edit)
            if edit:
                st.button("Batal", key="batal_kend", on_click=atur, args=("edit_kend", None))
    if not D["kendaraan"]:
        st.info("Belum ada kendaraan. Tambahkan satu, lalu isi bagian Kendaraan saat mencatat pembelian BBM di Catat transaksi.")
        return
    ids = [k["id"] for k in D["kendaraan"]]
    if st.session_state.get("kend_pilih") not in ids:
        st.session_state["kend_pilih"] = ids[0]
    kid = st.selectbox("Kendaraan", ids, format_func=f_kendaraan(), key="kend_pilih") if len(ids) > 1 else ids[0]
    k = kendaraan_dari(kid)
    st_ = statistik(kid)
    fmt = lambda v, s="": "-" if v is None else f"{v:.1f}".replace(".", ",") + s
    deretan_stat(kartu_stat("Odometer", f"{st_['odo']:,} km".replace(",", ".") if st_["odo"] else "-"),
                 kartu_stat("Rata-rata", fmt(st_["kmpl"], " km/L"), ket="dari isi penuh berurutan" if st_["kmpl"] else "perlu 2 isi penuh dengan km"),
                 kartu_stat("BBM per km", rp(round(st_["per_km_bbm"])) if st_["per_km_bbm"] else "-"),
                 kartu_stat("Biaya semua per km", rp(round(st_["per_km_total"])) if st_["per_km_total"] else "-", ket="BBM, servis, dan lainnya yang ditandai kendaraan ini"))
    st.caption(f"{k['jenis']}" + (f" · {k['plat']}" if k.get("plat") else "") + f" · total biaya tercatat {rp(st_['total'])}"
               + (f" · pajak {fmt_iso(k['pajak'])}" if k.get("pajak") else ""))
    if not ro:
        c1, c2 = st.columns(2)
        c1.button("Ubah kendaraan", key=f"kend_ubah_{kid}", on_click=atur, args=("edit_kend", kid))
        if st.session_state.get("hapus_kend") == kid:
            st.warning("Hapus kendaraan ini? Catatan BBM di transaksi tetap ada, hanya tanda kendaraannya dilepas.")
            ya, tdk = st.columns(2)
            if ya.button("Ya, hapus", key=f"kend_ya_{kid}", type="primary"):
                for t in D["transaksi"]:
                    if t.get("kendaraan") == kid:
                        for kk in ("kendaraan", "odo", "liter", "sebagian"):
                            t.pop(kk, None)
                D["kendaraan"] = [x for x in D["kendaraan"] if x["id"] != kid]
                catat("hapus", f"Hapus kendaraan {k['nama']}")
                selesai_simpan("Kendaraan dihapus.", hapus_kend=None)
            tdk.button("Batal", key=f"kend_tdk_{kid}", on_click=atur, args=("hapus_kend", None))
        else:
            c2.button("Hapus kendaraan", key=f"kend_hapus_{kid}", on_click=atur, args=("hapus_kend", kid))
    _panel_servis(k, ro)
    st.markdown("**Riwayat isi BBM**")
    if not st_["isi"]:
        st.caption("Belum ada. Di Catat transaksi (Pengeluaran), buka bagian Kendaraan lalu isi kilometer dan liter.")
        return
    df = pd.DataFrame([{"Tanggal": fmt_iso(b["tgl"]), "Km": b["odo"] or None, "Liter": b["liter"], "Rp": b["jumlah"], "Rp/liter": b["per_liter"],
                        "Km/L": round(b["kmpl"], 1) if b["kmpl"] else None, "Penuh": "ya" if b["penuh"] else "tidak"} for b in reversed(st_["isi"])])
    st.dataframe(df, hide_index=True, width="stretch")
    seri = [(fmt_iso(b["tgl"]), round(b["kmpl"], 2)) for b in st_["isi"] if b["kmpl"]]
    if len(seri) >= 2:
        st.markdown("**Km per liter dari waktu ke waktu**")
        st.line_chart(pd.DataFrame({"Km/L": [v for _, v in seri]}, index=[d for d, _ in seri]))
