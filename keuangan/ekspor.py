"""Ekspor (Excel, CSV) dan impor transaksi dari Excel atau CSV."""
import io
from datetime import date

import pandas as pd
import streamlit as st

from keuangan.bantu import kunci_urut, toko_dari, transaksi_toko, barang_dari, catat, nama_dompet, nama_kat, perbarui_harga_barang, saldo_dompet, selesai_simpan, transaksi_barang
from keuangan.inti import D, JENIS, baru_id, hanya_lihat, sekarang

KOLOM = ["Tanggal", "Jenis", "Jumlah", "Dompet", "Ke dompet", "Biaya admin", "Kategori", "Catatan", "Barang", "Banyaknya", "Harga satuan", "Toko", "Lokasi", "Waktu"]


def tabel_transaksi() -> pd.DataFrame:
    baris = []
    for t in sorted(D["transaksi"], key=kunci_urut):
        baris.append({"Tanggal": t["tgl"], "Jenis": JENIS[t["jenis"]], "Jumlah": t["jumlah"], "Dompet": nama_dompet(t["dompet"]),
                      "Ke dompet": nama_dompet(t["ke"]) if t.get("ke") else "", "Biaya admin": t.get("biaya", 0) or 0,
                      "Kategori": nama_kat(t.get("kategori")) if t["jenis"] != "transfer" else "", "Catatan": t.get("catatan", ""),
                      "Barang": (barang_dari(t.get("barang")) or {}).get("nama", ""), "Banyaknya": t.get("qty", "") or "",
                      "Harga satuan": t.get("harga_satuan", "") or "",
                      "Toko": (toko_dari(t.get("toko")) or {}).get("nama", ""), "Lokasi": t.get("lokasi", ""), "Waktu": t.get("waktu", "")})
    return pd.DataFrame(baris, columns=KOLOM)


def excel_lengkap() -> bytes:
    out = io.BytesIO()
    with pd.ExcelWriter(out, engine="openpyxl") as w:
        tabel_transaksi().to_excel(w, sheet_name="Transaksi", index=False)
        pd.DataFrame([{"Barang": b["nama"], "Kategori": nama_kat(b["kategori"]), "Merek": b.get("merek", ""), "Ukuran": b.get("ukuran", ""),
                       "Barcode": b.get("barcode", ""), "Satuan": b.get("satuan", ""), "Harga terakhir": b.get("harga", 0),
                       "Kedaluwarsa": b.get("kedaluwarsa", ""), "Langganan": "ya" if b.get("langganan") else "", "Catatan": b.get("catatan", ""),
                       "Kali dibeli": len(transaksi_barang(b["id"])), "Total belanja": sum(t["jumlah"] for t in transaksi_barang(b["id"]))}
                      for b in D["barang"]], columns=["Barang", "Kategori", "Merek", "Ukuran", "Barcode", "Satuan", "Harga terakhir", "Kedaluwarsa",
                                                      "Langganan", "Catatan", "Kali dibeli", "Total belanja"]
                     ).to_excel(w, sheet_name="Barang", index=False)
        pd.DataFrame([{"Toko": x["nama"], "Jenis": x.get("jenis", ""), "Lokasi": x.get("lokasi", ""), "Peta": x.get("peta", ""),
                       "Jam buka": x.get("jam_buka", ""), "Telepon": x.get("telepon", ""), "Favorit": "ya" if x.get("favorit") else "",
                       "Catatan": x.get("catatan", ""), "Kunjungan": len(transaksi_toko(x["id"])),
                       "Total belanja": sum(t["jumlah"] for t in transaksi_toko(x["id"]) if t["jenis"] == "keluar")}
                      for x in D["toko"]], columns=["Toko", "Jenis", "Lokasi", "Peta", "Jam buka", "Telepon", "Favorit", "Catatan", "Kunjungan", "Total belanja"]
                     ).to_excel(w, sheet_name="Toko", index=False)
        pd.DataFrame([{"Dompet": d["nama"], "Jenis": d.get("jenis", ""), "Saldo awal": d.get("saldo_awal", 0),
                       "Saldo sekarang": saldo_dompet(d["id"]), "Diarsipkan": "ya" if d.get("arsip") else ""}
                      for d in D["dompet"]]).to_excel(w, sheet_name="Dompet", index=False)
        pd.DataFrame([{"Kategori": nama_kat(a["kategori"]), "Batas per bulan": a["batas"]} for a in D["anggaran"]],
                     columns=["Kategori", "Batas per bulan"]).to_excel(w, sheet_name="Anggaran", index=False)
        pd.DataFrame([{"Tagihan": t["nama"], "Jumlah": t["jumlah"], "Berulang": t["tiap"], "Jatuh tempo": t["berikut"],
                       "Dompet": nama_dompet(t["dompet"]), "Aktif": "ya" if t.get("aktif", True) else ""} for t in D["tagihan"]],
                     columns=["Tagihan", "Jumlah", "Berulang", "Jatuh tempo", "Dompet", "Aktif"]).to_excel(w, sheet_name="Tagihan", index=False)
        pd.DataFrame([{"Target": g["nama"], "Target (Rp)": g["target"], "Terkumpul": sum(s["jumlah"] for s in g["setoran"]),
                       "Tenggat": g.get("tenggat", "")} for g in D["tabungan"]],
                     columns=["Target", "Target (Rp)", "Terkumpul", "Tenggat"]).to_excel(w, sheet_name="Tabungan", index=False)
        pd.DataFrame([{"Jenis": "Utang saya" if u["arah"] == "utang" else "Piutang", "Orang": u["orang"], "Jumlah": u["jumlah"],
                       "Dibayar": sum(b["jumlah"] for b in u["bayar"]), "Tenggat": u.get("tenggat", "")} for u in D["utang"]],
                     columns=["Jenis", "Orang", "Jumlah", "Dibayar", "Tenggat"]).to_excel(w, sheet_name="Utang-piutang", index=False)
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


def _desimal(s) -> float:
    s = str(s).strip().replace(",", ".")
    return float(s) if s else 0.0


def _tanggal(s) -> str:
    s = str(s).strip()[:10]
    for f in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%d.%m.%Y"):
        try:
            return pd.to_datetime(s, format=f).date().isoformat()
        except Exception:
            continue
    raise ValueError(f"tanggal tidak dikenali: {s}")


def _waktu(s) -> str:
    """Terima 'HH:MM', 'HH:MM:SS', 'HH.MM', objek jam, atau pecahan hari Excel; kembalikan 'HH:MM' atau ''."""
    if s is None or (isinstance(s, float) and pd.isna(s)) or str(s).strip() in ("", "nan", "NaT"):
        return ""
    if hasattr(s, "hour"):
        return f"{s.hour:02d}:{s.minute:02d}"
    x = str(s).strip().replace(".", ":")
    try:
        if ":" not in x:
            m = round(float(x) * 1440) % 1440
            return f"{m // 60:02d}:{m % 60:02d}"
        h, m = x.split(":")[:2]
        h, m = int(h), int(m)
        if 0 <= h < 24 and 0 <= m < 60:
            return f"{h:02d}:{m:02d}"
    except ValueError:
        pass
    raise ValueError(f"waktu '{s}' tidak dikenali (pakai format 14:30)")


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
        st.caption("Kolom wajib: Tanggal, Jenis (Pemasukan / Pengeluaran / Transfer), Dompet, dan Jumlah (boleh kosong bila Banyaknya dan Harga satuan diisi). Kolom lain: Kategori (boleh 'Rumah' atau sub kategori 'Rumah › Listrik'), Catatan, "
                   "Ke dompet dan Biaya admin (untuk transfer). Kolom Barang, Banyaknya, Harga satuan, Toko, Lokasi, Waktu (14:30) bersifat opsional (barang dan toko baru dibuat otomatis). "
                   " Tanggal boleh 2026-03-15 atau 15/03/2026.")
        contoh = pd.DataFrame([["2026-03-01", "Pemasukan", 5000000, "BCA", "", 0, "Gaji", "Gaji Maret", "", "", "", "", "", ""],
                               ["2026-03-02", "Pengeluaran", 35000, "Tunai", "", 0, "Makan dan minum", "Makan siang", "", "", "", "Warung Bu Tini", "Jl. Melati", "12:30"],
                               ["2026-03-03", "Transfer", 500000, "BCA", "GoPay", 2500, "", "Isi saldo", "", "", "", "", "", ""],
                               ["2026-03-04", "Pengeluaran", 15000, "Tunai", "", 0, "Makan dan minum › Belanja bahan makanan", "", "Indomie goreng", 5, 3000, "Indomaret Merdeka", "Jl. Merdeka, Bandung", "18:45"]],
                              columns=KOLOM)
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
        df = df.rename(columns={"Ke Dompet": "Ke dompet", "Biaya Admin": "Biaya admin", "Harga Satuan": "Harga satuan"})
        kurang = [k for k in ("Tanggal", "Jenis", "Jumlah", "Dompet") if k not in df.columns]
        if kurang:
            st.error("Kolom belum ada: " + ", ".join(kurang))
            return
        baru, galat = [], []
        dom_baru, kat_baru, brg_baru, tk_baru = {}, {}, {}, {}
        tk_cari = {x["nama"].strip().lower(): x for x in D["toko"]}
        brg_cari = {(b["nama"].strip().lower(), b["kategori"]): b for b in D["barang"]}
        dom_nama = {d["nama"].strip().lower(): d["id"] for d in D["dompet"]}
        kat_cari = {(k["nama"].strip().lower(), k.get("induk", ""), k["jenis"]): k["id"] for k in D["kategori"]}

        def id_dompet(nama):
            n = nama.strip().lower()
            if n in dom_nama:
                return dom_nama[n]
            if not buat or not n:
                raise ValueError(f"dompet '{nama}' tidak ada")
            dom_nama[n] = dom_baru[n] = baru_id()
            return dom_baru[n]

        def satu_kat(nama, induk, jenis):
            kunci = (nama.strip().lower(), induk, jenis)
            if kunci in kat_cari:
                return kat_cari[kunci]
            if not buat:
                raise ValueError(f"kategori '{nama}' tidak ada")
            nid = baru_id()
            kat_cari[kunci] = nid
            kat_baru[kunci] = (nid, nama.strip(), induk)
            return nid

        def id_kat(teks, jenis):
            """Terima 'Rumah', 'Rumah › Listrik' (atau tanda '>' / '/'), atau nama sub kategori saja."""
            bagian = [x.strip() for x in teks.replace("›", ">").split(">") if x.strip()] or ["Lainnya"]
            if len(bagian) == 1:
                n = bagian[0].lower()
                cocok = [k for k in D["kategori"] if k["jenis"] == jenis and k["nama"].strip().lower() == n]
                if cocok:
                    return sorted(cocok, key=lambda k: bool(k.get("induk")))[0]["id"]
                return satu_kat(bagian[0], "", jenis)
            return satu_kat(bagian[1], satu_kat(bagian[0], "", jenis), jenis)

        for i, r in df.iterrows():
            try:
                jenis = _cocok_jenis(r["Jenis"])
                jml = _angka(r["Jumlah"])
                t = {"id": baru_id(), "jenis": jenis, "tgl": _tanggal(r["Tanggal"]), "jumlah": jml,
                     "dompet": id_dompet(str(r["Dompet"])), "kategori": "", "catatan": str(r.get("Catatan", "")).strip(),
                     "dibuat": sekarang().strftime("%Y-%m-%d %H:%M:%S.%f"), "oleh": "impor"}
                if jenis == "transfer":
                    t["ke"] = id_dompet(str(r.get("Ke dompet", "")))
                    t["biaya"] = _angka(r.get("Biaya admin", "0"))
                    if t["ke"] == t["dompet"]:
                        raise ValueError("dompet asal dan tujuan sama")
                else:
                    t["kategori"] = id_kat(str(r.get("Kategori", "")), jenis)
                    nt = str(r.get("Toko", "") if "Toko" in df.columns else "").strip()
                    nt = "" if nt.lower() == "nan" else nt
                    if nt:
                        if nt.lower() not in tk_cari:
                            if not buat:
                                raise ValueError(f"toko '{nt}' tidak ada")
                            tk_cari[nt.lower()] = tk_baru[nt.lower()] = {"id": baru_id(), "nama": nt, "jenis": "Lainnya", "lokasi": ""}
                        t["toko"] = tk_cari[nt.lower()]["id"]
                    lk = str(r.get("Lokasi", "") if "Lokasi" in df.columns else "").strip()
                    if lk and lk.lower() != "nan":
                        t["lokasi"] = lk
                    wk = _waktu(r.get("Waktu", "") if "Waktu" in df.columns else "")
                    if wk:
                        t["waktu"] = wk
                    nb = str(r.get("Barang", "")).strip()
                    if nb:
                        qty = _desimal(r.get("Banyaknya", "")) or 1.0
                        hs = _angka(r.get("Harga satuan", "")) or int(round(jml / qty))
                        kunci_b = (nb.lower(), t["kategori"])
                        if kunci_b not in brg_cari:
                            if not buat:
                                raise ValueError(f"barang '{nb}' tidak ada")
                            brg_cari[kunci_b] = brg_baru[kunci_b] = {"id": baru_id(), "nama": nb, "kategori": t["kategori"], "harga": hs, "satuan": ""}
                        t.update({"barang": brg_cari[kunci_b]["id"], "qty": qty, "harga_satuan": hs})
                        t["jumlah"] = int(round(qty * hs)) if _angka(r.get("Harga satuan", "")) else jml
                if t["jumlah"] <= 0:
                    raise ValueError("jumlah harus lebih dari nol (atau isi Banyaknya dan Harga satuan)")
                baru.append(t)
            except Exception as ex:
                galat.append(f"Baris {i + 2}: {ex}")
        st.markdown(f"**{len(baru)}** baris siap diimpor, **{len(galat)}** bermasalah.")
        if galat:
            with st.expander("Baris bermasalah (tidak diimpor)", expanded=True):
                st.write("\n".join(f"- {g}" for g in galat[:50]))
        if dom_baru or kat_baru or brg_baru or tk_baru:
            st.caption(f"Akan dibuat: {len(dom_baru)} dompet, {len(kat_baru)} kategori, {len(brg_baru)} barang, dan {len(tk_baru)} toko baru.")
        if baru and st.button(f"Impor {len(baru)} transaksi", type="primary", key="impor_go"):
            for n, i in dom_baru.items():
                D["dompet"].append({"id": i, "nama": n.title() if n.islower() else n, "jenis": "Lainnya", "saldo_awal": 0, "arsip": False})
            for (_, _, j), (i, nama_k, induk) in sorted(kat_baru.items(), key=lambda x: bool(x[0][1])):
                p = next((k for k in D["kategori"] if k["id"] == induk), None)
                D["kategori"].append({"id": i, "nama": nama_k, "jenis": j, "induk": induk, "ikon": p["ikon"] if p else "🏷️",
                                      "warna": p["warna"] if p else "#9aa0a6"})
            D["barang"].extend(brg_baru.values())
            D["toko"].extend(tk_baru.values())
            D["transaksi"].extend(baru)
            for bb in {t["barang"] for t in baru if t.get("barang")}:
                perbarui_harga_barang(bb)
            catat("impor", f"Impor {len(baru)} transaksi dari {berkas.name}")
            selesai_simpan(f"{len(baru)} transaksi diimpor.")
