"""Impor dan ekspor format aplikasi pencatat lain (file Excel dengan sheet Records dan Debts)."""
import io
from datetime import datetime

import pandas as pd
import streamlit as st

from keuangan.bantu import catat, nama_dompet, nama_kat, selesai_simpan
from keuangan.inti import D, baru_id, hanya_lihat, sekarang
from keuangan.utang import dibayar

KOLOM_RECORDS = ["account", "category", "currency", "amount", "ref_currency_amount", "type", "payment_type", "payment_type_local", "note", "date",
                 "gps_latitude", "gps_longitude", "gps_accuracy_in_meters", "warranty_in_month", "transfer", "payee", "labels", "envelope_id", "custom_category"]
KOLOM_DEBTS = ["account", "type", "name", "note", "amount", "remaining_amount", "creation_date", "pay_back_date", "paid_back"]
PEMBAYARAN = {"Tunai": ("CASH", "Cash"), "Rekening bank": ("DEBIT_CARD", "Debit card"), "Dompet digital": ("MOBILE_PAYMENT", "Mobile payment"),
              "Kartu kredit": ("CREDIT_CARD", "Credit card")}


# ------------------------------------------------------------------ baca
def _bersih(df: pd.DataFrame) -> pd.DataFrame:
    """File aplikasi lama menyisipkan karakter kosong (NUL) di sela huruf; buang dulu."""
    df = df.copy()
    df.columns = [str(c).replace("\x00", "").strip() for c in df.columns]
    return df.map(lambda s: s.replace("\x00", "").strip() if isinstance(s, str) else s).fillna("")


def baca_file(berkas) -> tuple:
    """Kembalikan (records, debts); debts bisa kosong."""
    x = pd.read_excel(berkas, sheet_name=None, dtype=str)
    peta = {str(k).strip().lower(): _bersih(v) for k, v in x.items()}
    if "records" not in peta:
        raise ValueError("Sheet 'Records' tidak ditemukan. Ini bukan file ekspor aplikasi tersebut.")
    rec = peta["records"]
    kurang = [k for k in ("account", "category", "amount", "date") if k not in rec.columns]
    if kurang:
        raise ValueError("Kolom belum ada di sheet Records: " + ", ".join(kurang))
    return rec, peta.get("debts", pd.DataFrame(columns=KOLOM_DEBTS))


def _angka(s) -> int:
    s = str(s).strip().replace(" ", "")
    if not s:
        return 0
    return int(round(float(s)))


def _waktu_tgl(s: str) -> tuple:
    s = str(s).strip()
    try:
        w = pd.to_datetime(s)
    except Exception:
        raise ValueError(f"tanggal tidak dikenali: {s}")
    return w.date().isoformat(), (f"{w.hour:02d}:{w.minute:02d}" if (w.hour or w.minute) else "")


def _ya(s) -> bool:
    return str(s).strip().lower() in ("true", "1", "yes", "ya")


# ------------------------------------------------------------------ susun
def susun_impor(rec: pd.DataFrame, debts: pd.DataFrame, buat: bool = True, utang_arah: str = "utang") -> dict:
    """Ubah isi file menjadi data siap simpan tanpa mengubah D. Hasil: transaksi, utang, dompet_baru, kategori_baru, toko_baru, lewati, galat."""
    dom_cari = {d["nama"].strip().lower(): d["id"] for d in D["dompet"]}
    kat_cari = {}
    for k in D["kategori"]:
        kat_cari.setdefault((k["nama"].strip().lower(), k["jenis"]), k["id"])
    tk_cari = {x["nama"].strip().lower(): x["id"] for x in D["toko"]}
    dom_baru, kat_baru, tk_baru = {}, {}, {}
    ada = {(t["tgl"], t.get("waktu", ""), t["jumlah"], t["dompet"], t.get("catatan", "")) for t in D["transaksi"]}
    hasil = {"transaksi": [], "utang": [], "lewati": 0, "galat": []}

    def dompet(nama):
        n = nama.strip().lower()
        if n in dom_cari:
            return dom_cari[n]
        if not n or not buat:
            raise ValueError(f"dompet '{nama}' tidak ada")
        dom_cari[n] = dom_baru[n] = baru_id()
        return dom_cari[n]

    def kategori(nama, jenis):
        n = nama.strip() or "Lainnya"
        if (n.lower(), jenis) in kat_cari:
            return kat_cari[(n.lower(), jenis)]
        if not buat:
            raise ValueError(f"kategori '{n}' tidak ada")
        nid = baru_id()
        kat_cari[(n.lower(), jenis)] = nid
        kat_baru[(n.lower(), jenis)] = (nid, n)
        return nid

    def toko(nama):
        n = nama.strip()
        if not n:
            return ""
        if n.lower() not in tk_cari:
            if not buat:
                raise ValueError(f"toko '{n}' tidak ada")
            nid = baru_id()
            tk_cari[n.lower()] = nid
            tk_baru[n.lower()] = (nid, n)
        return tk_cari[n.lower()]

    baris = []
    for i, r in rec.iterrows():
        try:
            tgl, wk = _waktu_tgl(r["date"])
            jml = _angka(r["amount"])
            if jml == 0:
                raise ValueError("jumlah nol")
            baris.append({"i": i, "tgl": tgl, "waktu": wk, "raw": str(r["date"]), "jml": jml, "akun": str(r["account"]), "kat": str(r["category"]),
                          "catatan": str(r.get("note", "")), "toko": str(r.get("payee", "")), "label": str(r.get("labels", "")),
                          "transfer": _ya(r.get("transfer", ""))})
        except Exception as ex:
            hasil["galat"].append(f"Baris {i + 2}: {ex}")

    # transfer: pasangkan baris keluar dan masuk pada waktu yang sama
    terpakai = set()
    for a in baris:
        if not a["transfer"] or a["jml"] >= 0 or a["i"] in terpakai:
            continue
        b = next((x for x in baris if x["transfer"] and x["i"] not in terpakai and x["raw"] == a["raw"] and x["jml"] == -a["jml"] and x["akun"] != a["akun"]), None)
        if not b:
            continue
        terpakai |= {a["i"], b["i"]}
        try:
            t = {"id": baru_id(), "jenis": "transfer", "tgl": a["tgl"], "jumlah": -a["jml"], "dompet": dompet(a["akun"]), "ke": dompet(b["akun"]),
                 "biaya": 0, "kategori": "", "catatan": a["catatan"], "dibuat": sekarang().strftime("%Y-%m-%d %H:%M:%S.%f"), "oleh": "impor"}
            if a["waktu"]:
                t["waktu"] = a["waktu"]
            hasil["transaksi"].append(t)
        except Exception as ex:
            hasil["galat"].append(f"Baris {a['i'] + 2}: {ex}")

    for a in baris:
        if a["i"] in terpakai:
            continue
        try:
            jenis = "keluar" if a["jml"] < 0 else "masuk"
            cat = a["catatan"] + (f" ({a['label']})" if a["label"] and a["label"].lower() not in a["catatan"].lower() else "")
            did = dompet(a["akun"])
            if (a["tgl"], a["waktu"], abs(a["jml"]), did, cat) in ada:
                hasil["lewati"] += 1
                continue
            kid = kategori(a["kat"], jenis)
            t = {"id": baru_id(), "jenis": jenis, "tgl": a["tgl"], "jumlah": abs(a["jml"]), "dompet": did, "kategori": kid, "catatan": cat,
                 "dibuat": sekarang().strftime("%Y-%m-%d %H:%M:%S.%f"), "oleh": "impor"}
            if a["waktu"]:
                t["waktu"] = a["waktu"]
            tid = toko(a["toko"])
            if tid:
                t["toko"] = tid
            ada.add((a["tgl"], a["waktu"], t["jumlah"], did, cat))
            hasil["transaksi"].append(t)
        except Exception as ex:
            hasil["galat"].append(f"Baris {a['i'] + 2}: {ex}")

    for i, r in debts.iterrows():
        try:
            jml = abs(_angka(r.get("amount", "")))
            if not jml or not str(r.get("name", "")).strip():
                raise ValueError("nama atau jumlah kosong")
            arah = utang_arah if str(r.get("type", "")).strip().upper() == "ANYONE_TO_ME" else ("piutang" if utang_arah == "utang" else "utang")
            tgl = _waktu_tgl(r["creation_date"])[0] if r.get("creation_date") else sekarang().date().isoformat()
            tenggat = _waktu_tgl(r["pay_back_date"])[0] if r.get("pay_back_date") else ""
            lunas = str(r.get("paid_back", "")).strip().lower() in ("yes", "true", "ya")
            u = {"id": baru_id(), "arah": arah, "orang": str(r["name"]).strip(), "jumlah": jml, "tgl": tgl, "tenggat": tenggat,
                 "catatan": str(r.get("note", "")).strip(), "bayar": []}
            if lunas:
                u["bayar"].append({"id": baru_id(), "tgl": tenggat or tgl, "jumlah": jml})
            if any(x["orang"].strip().lower() == u["orang"].lower() and x["jumlah"] == jml and x["arah"] == arah and x.get("tgl") == tgl for x in D["utang"]):
                hasil["lewati"] += 1
                continue
            hasil["utang"].append(u)
        except Exception as ex:
            hasil["galat"].append(f"Utang baris {i + 2}: {ex}")

    hasil["dompet_baru"], hasil["kategori_baru"], hasil["toko_baru"] = dom_baru, kat_baru, tk_baru
    return hasil


def terapkan(h: dict):
    for n, i in h["dompet_baru"].items():
        D["dompet"].append({"id": i, "nama": n.title() if n.islower() else n, "jenis": "Tunai" if "tunai" in n or "cash" in n else "Lainnya", "saldo_awal": 0, "arsip": False})
    for (_, j), (i, nama) in h["kategori_baru"].items():
        D["kategori"].append({"id": i, "nama": nama, "jenis": j, "induk": "", "ikon": "🏷️", "warna": "#9aa0a6"})
    for i, nama in h["toko_baru"].values():
        D["toko"].append({"id": i, "nama": nama, "jenis": "Lainnya", "lokasi": ""})
    D["transaksi"].extend(h["transaksi"])
    D["utang"].extend(h["utang"])


# ------------------------------------------------------------------ ekspor
def _pembayaran(dompet_id: str) -> tuple:
    d = next((x for x in D["dompet"] if x["id"] == dompet_id), {})
    return PEMBAYARAN.get(d.get("jenis", ""), ("CASH", "Cash"))


def _tanggal_lama(t: dict) -> str:
    w = t.get("waktu") or "00:00"
    return f"{t['tgl']} {w}:00.000000"


def tabel_records() -> pd.DataFrame:
    baris = []

    def tambah(t, akun, kategori, jumlah, tipe, transfer, payee="", labels=""):
        pt, ptl = _pembayaran(t["dompet"])
        baris.append({"account": akun, "category": kategori, "currency": "IDR", "amount": jumlah, "ref_currency_amount": jumlah, "type": tipe,
                      "payment_type": pt, "payment_type_local": ptl, "note": t.get("catatan", ""), "date": _tanggal_lama(t), "gps_latitude": 0,
                      "gps_longitude": 0, "gps_accuracy_in_meters": 0, "warranty_in_month": 0, "transfer": transfer, "payee": payee, "labels": labels,
                      "envelope_id": 1001, "custom_category": False})

    for t in sorted(D["transaksi"], key=lambda x: (x["tgl"], x.get("waktu", ""), x.get("dibuat", ""))):
        if t["jenis"] == "transfer":
            a, b = nama_dompet(t["dompet"]), nama_dompet(t.get("ke"))
            tambah(t, a, "Transfer", -t["jumlah"], "Expenses", True)
            tambah(dict(t, dompet=t.get("ke")), b, "Transfer", t["jumlah"], "Income", True)
            if t.get("biaya"):
                tambah(t, a, "Biaya admin", -int(t["biaya"]), "Expenses", False)
            continue
        tk = next((x["nama"] for x in D["toko"] if x["id"] == t.get("toko")), "")
        pl = next((x["nama"] for x in D["platform"] if x["id"] == t.get("platform")), "")
        brg = next((b["nama"] for b in D["barang"] if b["id"] == t.get("barang")), "")
        if brg and not t.get("catatan"):
            t = dict(t, catatan=brg)
        tambah(t, nama_dompet(t["dompet"]), (nama_kat(t.get("kategori")) or "Lainnya").split(" › ")[-1],
               -t["jumlah"] if t["jenis"] == "keluar" else t["jumlah"], "Expenses" if t["jenis"] == "keluar" else "Income", False, tk, pl)
    return pd.DataFrame(baris, columns=KOLOM_RECORDS)


def tabel_debts() -> pd.DataFrame:
    baris = []
    for u in D["utang"]:
        sisa = int(u["jumlah"]) - dibayar(u)
        saya_berutang = u["arah"] == "utang"
        baris.append({"account": "", "type": "ANYONE_TO_ME" if saya_berutang else "ME_TO_ANYONE", "name": u["orang"], "note": u.get("catatan", ""),
                      "amount": int(u["jumlah"]), "remaining_amount": -sisa if saya_berutang else sisa,
                      "creation_date": f"{u.get('tgl', '')} 00:00:00.000000", "pay_back_date": f"{u['tenggat']} 00:00:00.000000" if u.get("tenggat") else "",
                      "paid_back": "Yes" if sisa <= 0 else "No"})
    return pd.DataFrame(baris, columns=KOLOM_DEBTS)


def excel_lama() -> bytes:
    out = io.BytesIO()
    with pd.ExcelWriter(out, engine="openpyxl") as w:
        tabel_records().to_excel(w, sheet_name="Records", index=False)
        tabel_debts().to_excel(w, sheet_name="Debts", index=False)
        for ws in w.book.worksheets:
            for kol in ws.columns:
                ws.column_dimensions[kol[0].column_letter].width = min(max(len(str(c.value or "")) for c in kol) + 3, 40)
    return out.getvalue()


# ------------------------------------------------------------------ halaman
def halaman_aplikasi_lama():
    with st.container(key="kartu_g_lama_ekspor"):
        st.markdown("**Ekspor format aplikasi lama**")
        st.caption("Excel dengan sheet Records dan Debts, kolomnya sama dengan file ekspor aplikasi lama. Pengeluaran bernilai negatif, transfer menjadi dua baris, "
                   "kategori hanya nama paling dalam, toko menjadi payee, platform menjadi labels.")
        st.download_button("Unduh Excel format aplikasi lama", excel_lama(), file_name=f"report_{sekarang().strftime('%Y-%m-%d_%H%M%S')}.xlsx",
                           mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", key="unduh_lama")
    if hanya_lihat():
        return
    with st.container(key="kartu_g_lama_impor"):
        st.markdown("**Impor dari aplikasi lama**")
        st.caption("Pilih file ekspor (.xls atau .xlsx) yang berisi sheet Records, dan Debts bila ada. Dompet, kategori, dan toko yang belum ada dibuat otomatis. "
                   "Data yang sama persis dengan yang sudah ada dilewati, jadi aman diimpor ulang.")
        berkas = st.file_uploader("File ekspor aplikasi lama", type=["xls", "xlsx"], key="impor_lama")
        c1, c2 = st.columns(2)
        buat = c1.checkbox("Buat dompet, kategori, toko yang belum ada", value=True, key="lama_buat")
        arah = c2.selectbox("Tipe ANYONE_TO_ME di Debts berarti", ["utang", "piutang"], format_func=lambda a: "Utang saya" if a == "utang" else "Piutang (orang berutang ke saya)",
                            key="lama_arah")
        if berkas is None:
            return
        try:
            rec, debts = baca_file(berkas)
            h = susun_impor(rec, debts, buat, arah)
        except Exception as ex:
            st.error(f"File tidak bisa dibaca: {ex}")
            return
        st.markdown(f"**{len(h['transaksi'])}** transaksi dan **{len(h['utang'])}** utang-piutang siap diimpor, **{h['lewati']}** dilewati (sudah ada), **{len(h['galat'])}** bermasalah.")
        if h["galat"]:
            with st.expander("Baris bermasalah (tidak diimpor)", expanded=True):
                st.write("\n".join(f"- {g}" for g in h["galat"][:50]))
        if h["dompet_baru"] or h["kategori_baru"] or h["toko_baru"]:
            st.caption(f"Akan dibuat: {len(h['dompet_baru'])} dompet, {len(h['kategori_baru'])} kategori, {len(h['toko_baru'])} toko baru.")
        if h["transaksi"]:
            kas = sum(t["jumlah"] for t in h["transaksi"] if t["jenis"] == "keluar")
            st.caption(f"Total pengeluaran yang akan masuk: Rp {kas:,}".replace(",", "."))
        if (h["transaksi"] or h["utang"]) and st.button("Impor sekarang", type="primary", key="lama_go"):
            terapkan(h)
            catat("impor", f"Impor {len(h['transaksi'])} transaksi dan {len(h['utang'])} utang dari {berkas.name}")
            selesai_simpan(f"{len(h['transaksi'])} transaksi dan {len(h['utang'])} utang diimpor.")
