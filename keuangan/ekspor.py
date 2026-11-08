"""Ekspor (Excel, CSV) dan impor transaksi dari Excel atau CSV."""
import io
from datetime import date

import pandas as pd
import streamlit as st

from keuangan.bantu import catat, dompet_dari, kat_dari, nama_dompet, nama_kat, saldo_dompet, selesai_simpan
from keuangan.inti import D, JENIS, baru_id, hanya_lihat, sekarang

KOLOM = ["Tanggal", "Jenis", "Jumlah", "Dompet", "Ke dompet", "Biaya admin", "Kategori", "Catatan"]


def tabel_transaksi() -> pd.DataFrame:
    baris = []
    for t in sorted(D["transaksi"], key=lambda t: (t["tgl"], t.get("dibuat", ""))):
        baris.append({"Tanggal": t["tgl"], "Jenis": JENIS[t["jenis"]], "Jumlah": t["jumlah"], "Dompet": nama_dompet(t["dompet"]),
                      "Ke dompet": nama_dompet(t["ke"]) if t.get("ke") else "", "Biaya admin": t.get("biaya", 0) or 0,
                      "Kategori": nama_kat(t.get("kategori")) if t["jenis"] != "transfer" else "", "Catatan": t.get("catatan", "")})
    return pd.DataFrame(baris, columns=KOLOM)


def excel_lengkap() -> bytes:
    out = io.BytesIO()
    with pd.ExcelWriter(out, engine="openpyxl") as w:
        tabel_transaksi().to_excel(w, "Transaksi", index=False)
        pd.DataFrame([{"Dompet": d["nama"], "Jenis": d.get("jenis", ""), "Saldo awal": d.get("saldo_awal", 0),
                       "Saldo sekarang": saldo_dompet(d["id"]), "Diarsipkan": "ya" if d.get("arsip") else ""}
                      for d in D["dompet"]]).to_excel(w, "Dompet", index=False)
        pd.DataFrame([{"Kategori": nama_kat(a["kategori"]), "Batas per bulan": a["batas"]} for a in D["anggaran"]],
                     columns=["Kategori", "Batas per bulan"]).to_excel(w, "Anggaran", index=False)
        pd.DataFrame([{"Tagihan": t["nama"], "Jumlah": t["jumlah"], "Berulang": t["tiap"], "Jatuh tempo": t["berikut"],
                       "Dompet": nama_dompet(t["dompet"]), "Aktif": "ya" if t.get("aktif", True) else ""} for t in D["tagihan"]],
                     columns=["Tagihan", "Jumlah", "Berulang", "Jatuh tempo", "Dompet", "Aktif"]).to_excel(w, "Tagihan", index=False)
        pd.DataFrame([{"Target": g["nama"], "Target (Rp)": g["target"], "Terkumpul": sum(s["jumlah"] for s in g["setoran"]),
                       "Tenggat": g.get("tenggat", "")} for g in D["tabungan"]],
                     columns=["Target", "Target (Rp)", "Terkumpul", "Tenggat"]).to_excel(w, "Tabungan", index=False)
        pd.DataFrame([{"Jenis": "Utang saya" if u["arah"] == "utang" else "Piutang", "Orang": u["orang"], "Jumlah": u["jumlah"],
                       "Dibayar": sum(b["jumlah"] for b in u["bayar"]), "Tenggat": u.get("tenggat", "")} for u in D["utang"]],
                     columns=["Jenis", "Orang", "Jumlah", "Dibayar", "Tenggat"]).to_excel(w, "Utang-piutang", index=False)
        for ws in w.book.worksheets:
            for kol in ws.columns:
                ws.column_dimensions[kol[0].column_letter].width = min(max(len(str(c.value or "")) for c in kol) + 3, 40)
    return out.getvalue()


def halaman_ekspor():
    with st.container(key="kartu_g_ekspor"):
        st.markdown("**Ekspor**")
        st.caption("Excel berisi semua data (transaksi, dompet, anggaran, tagihan, tabungan, utang-piutang). CSV berisi transaksi saja.")
        stempel = sekarang().strftime("%Y%m%d")
        c1, c2 = st.columns(2)
        c1.download_button("Unduh Excel lengkap", excel_lengkap(), file_name=f"keuangan-{stempel}.xlsx",
                           mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        c2.download_button("Unduh transaksi (CSV)", tabel_transaksi().to_csv(index=False).encode("utf-8-sig"),
                           file_name=f"transaksi-{stempel}.csv", mime="text/csv")


def _baca(berkas) -> pd.DataFrame:
    if berkas.name.lower().endswith((".xlsx", ".xlsm")):
        return pd.read_excel(berkas, dtype=str).fillna("")
    mentah = berkas.getvalue()
    for enc in ("utf-8-sig", "utf-8", "cp1252"):
        try:
            return pd.read_csv(io.StringIO(mentah.decode(enc)), sep=None, engine="python", dtype=str).fillna("")
        except Exception:
            continue
    raise ValueError("File tidak bisa dibaca.")


def _angka(s) -> int:
    """Baca angka gaya Indonesia (1.250.000,50) maupun gaya lain (1,250,000.50)."""
    s = str(s).strip().lower().replace("rp", "").replace(" ", "")
    if not s:
        return 0
    if "," in s and "." in s:
        if s.rfind(",") > s.rfind("."):
            s = s.replace(".", "").replace(",", ".")
        else:
            s = s.replace(",", "")
    elif "," in s:
        s = s.replace(",", "") if s.count(",") > 1 or len(s.split(",")[-1]) == 3 else s.replace(",", ".")
    elif "." in s and (s.count(".") > 1 or len(s.split(".")[-1]) == 3):
        s = s.replace(".", "")
    return int(round(float(s)))


def _tanggal(s) -> str:
    s = str(s).strip()[:10]
    for f in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%d.%m.%Y"):
        try:
            return pd.to_datetime(s, format=f).date().isoformat()
        except Exception:
            continue
    raise ValueError(f"tanggal tidak dikenali: {s}")


def _cocok_jenis(s: str) -> str:
    s = str(s).strip().lower()
    for k, v in JENIS.items():
        if s in (k, v.lower()):
            return k
    if s in ("income", "pemasukan", "masuk", "kredit"):
        return "masuk"
    if s in ("expense", "pengeluaran", "keluar", "debit"):
        return "keluar"
    raise ValueError(f"jenis tidak dikenali: {s}")


def halaman_impor():
    if hanya_lihat():
        st.info("Akun ini hanya bisa melihat.")
        return
    with st.container(key="kartu_g_impor"):
        st.markdown("**Impor transaksi**")
        st.caption("Kolom wajib: Tanggal, Jenis (Pemasukan / Pengeluaran / Transfer), Jumlah, Dompet. Kolom lain: Kategori, Catatan, "
                   "Ke dompet dan Biaya admin (untuk transfer). Tanggal boleh 2026-03-15 atau 15/03/2026.")
        contoh = pd.DataFrame([["2026-03-01", "Pemasukan", 5000000, "BCA", "", 0, "Gaji", "Gaji Maret"],
                               ["2026-03-02", "Pengeluaran", 35000, "Tunai", "", 0, "Makan dan minum", "Makan siang"],
                               ["2026-03-03", "Transfer", 500000, "BCA", "GoPay", 2500, "", "Isi saldo"]], columns=KOLOM)
        st.download_button("Unduh contoh file (CSV)", contoh.to_csv(index=False).encode("utf-8-sig"), file_name="contoh-impor.csv", mime="text/csv")
        berkas = st.file_uploader("File Excel atau CSV", type=["xlsx", "xlsm", "csv"], key="impor_berkas")
        buat = st.checkbox("Buat dompet dan kategori yang belum ada secara otomatis", value=True)
        if berkas is None:
            return
        try:
            df = _baca(berkas)
        except Exception as ex:
            st.error(f"File tidak bisa dibaca: {ex}")
            return
        df.columns = [str(c).strip().title() for c in df.columns]
        df = df.rename(columns={"Ke Dompet": "Ke dompet", "Biaya Admin": "Biaya admin"})
        kurang = [k for k in ("Tanggal", "Jenis", "Jumlah", "Dompet") if k not in df.columns]
        if kurang:
            st.error("Kolom belum ada: " + ", ".join(kurang))
            return
        baru, galat = [], []
        dom_baru, kat_baru = {}, {}
        dom_nama = {d["nama"].strip().lower(): d["id"] for d in D["dompet"]}
        kat_nama = {(k["nama"].strip().lower(), k["jenis"]): k["id"] for k in D["kategori"]}

        def id_dompet(nama):
            n = nama.strip().lower()
            if n in dom_nama:
                return dom_nama[n]
            if not buat or not n:
                raise ValueError(f"dompet '{nama}' tidak ada")
            dom_nama[n] = dom_baru[n] = baru_id()
            return dom_baru[n]

        def id_kat(nama, jenis):
            n = nama.strip().lower() or "lainnya"
            if (n, jenis) in kat_nama:
                return kat_nama[(n, jenis)]
            if not buat:
                raise ValueError(f"kategori '{nama}' tidak ada")
            kat_nama[(n, jenis)] = kat_baru[(n, jenis)] = baru_id()
            return kat_baru[(n, jenis)]

        for i, r in df.iterrows():
            try:
                jenis = _cocok_jenis(r["Jenis"])
                jml = _angka(r["Jumlah"])
                if jml <= 0:
                    raise ValueError("jumlah harus lebih dari nol")
                t = {"id": baru_id(), "jenis": jenis, "tgl": _tanggal(r["Tanggal"]), "jumlah": jml,
                     "dompet": id_dompet(str(r["Dompet"])), "kategori": "", "catatan": str(r.get("Catatan", "")).strip(),
                     "dibuat": sekarang().strftime("%Y-%m-%d %H:%M"), "oleh": "impor"}
                if jenis == "transfer":
                    t["ke"] = id_dompet(str(r.get("Ke dompet", "")))
                    t["biaya"] = _angka(r.get("Biaya admin", "0"))
                    if t["ke"] == t["dompet"]:
                        raise ValueError("dompet asal dan tujuan sama")
                else:
                    t["kategori"] = id_kat(str(r.get("Kategori", "")), jenis)
                baru.append(t)
            except Exception as ex:
                galat.append(f"Baris {i + 2}: {ex}")
        st.markdown(f"**{len(baru)}** baris siap diimpor, **{len(galat)}** bermasalah.")
        if galat:
            with st.expander("Baris bermasalah (tidak diimpor)", expanded=True):
                st.write("\n".join(f"- {g}" for g in galat[:50]))
        if dom_baru or kat_baru:
            st.caption(f"Akan dibuat: {len(dom_baru)} dompet dan {len(kat_baru)} kategori baru.")
        if baru and st.button(f"Impor {len(baru)} transaksi", type="primary", key="impor_go"):
            for n, i in dom_baru.items():
                D["dompet"].append({"id": i, "nama": n.title() if n.islower() else n, "jenis": "Lainnya", "saldo_awal": 0, "arsip": False})
            for (n, j), i in kat_baru.items():
                D["kategori"].append({"id": i, "nama": n.capitalize(), "jenis": j})
            D["transaksi"].extend(baru)
            catat("impor", f"Impor {len(baru)} transaksi dari {berkas.name}")
            selesai_simpan(f"{len(baru)} transaksi diimpor.")
