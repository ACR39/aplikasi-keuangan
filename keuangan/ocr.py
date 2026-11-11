"""Baca foto struk jadi daftar barang. Dua mesin, dipilih otomatis:

1. Claude (paling akurat): aktif bila ada kunci API di secrets `[anthropic] api_key`. Foto struk dikirim ke API Anthropic.
2. Tesseract (gratis, di server sendiri): aktif bila `pytesseract` dan program `tesseract` terpasang
   (Streamlit Cloud: buat berkas packages.txt berisi tesseract-ocr dan tesseract-ocr-ind). Hasilnya kasar, selalu periksa.

Hasil selalu berupa saran; pengguna memeriksa dan memperbaikinya sebelum disimpan.
"""
import base64
import difflib
import io
import json
import re
import shutil

import pandas as pd
import requests
import streamlit as st

from keuangan.inti import D, hanya_lihat

MODEL_BAWAAN = "claude-sonnet-5-5"
URL_API = "https://api.anthropic.com/v1/messages"
KATA_ABAI = ("total", "subtotal", "sub total", "tunai", "cash", "kembali", "change", "bayar", "ppn", "pajak", "tax", "kartu", "debit",
             "kredit", "qris", "voucher", "poin", "point", "hemat", "item", "terima kasih", "thank", "npwp", "kasir", "struk", "no.", "nomor", "sms", "kritik", "member", "tgl.", "telp", "dpp", "jl.", "expired", "kembalian", "saran")


# ---------------------------------------------------------------- mesin
def _cfg_claude():
    try:
        a = st.secrets["anthropic"]
        return {"key": a["api_key"], "model": a.get("model", MODEL_BAWAAN)}
    except Exception:
        return None


# Penyedia berformat OpenAI: nama di secrets -> (alamat bawaan, model bawaan)
PENYEDIA_OA = {
    "openai": ("https://api.openai.com/v1", "gpt-4o-mini"),
    "openrouter": ("https://openrouter.ai/api/v1", "google/gemini-2.5-flash"),
    "gemini": ("https://generativelanguage.googleapis.com/v1beta/openai", "gemini-2.5-flash"),
}


def _cfg_oa(nama: str):
    """Secrets [openai] / [openrouter] / [gemini]: api_key, opsional base_url dan model."""
    try:
        a = st.secrets[nama]
        base, model = PENYEDIA_OA[nama]
        return {"key": a["api_key"], "base": str(a.get("base_url", base)).rstrip("/"), "model": a.get("model", model), "nama": nama}
    except Exception:
        return None


def _ada_tesseract() -> bool:
    try:
        import pytesseract  # noqa: F401
    except ImportError:
        return False
    return shutil.which("tesseract") is not None


def daftar_mesin() -> list:
    """Mesin yang sudah diisi, urut dari yang diutamakan: claude, openai, openrouter, gemini, tesseract."""
    m = []
    if _cfg_claude():
        m.append("claude")
    m += [n for n in PENYEDIA_OA if _cfg_oa(n)]
    if _ada_tesseract():
        m.append("tesseract")
    return m


def mesin_tersedia() -> str:
    """Mesin pertama yang aktif, atau '' bila belum ada."""
    d = daftar_mesin()
    return d[0] if d else ""


# ---------------------------------------------------------------- angka dan teks
def angka(s) -> int:
    """'12.500', '12,500', 'Rp 12.500,00' -> 12500. Gagal -> 0."""
    t = re.sub(r"[^\d.,]", "", str(s or ""))
    if not t:
        return 0
    if re.search(r"[.,]\d{2}$", t) and re.search(r"[.,]\d{3}[.,]\d{2}$", t):  # 12.500,00
        t = t[:-3]
    t = re.sub(r"[.,]", "", t)
    return int(t) if t.isdigit() else 0


def _kecilkan(mentah: bytes, sisi: int = 1600) -> bytes:
    from PIL import Image, ImageOps
    im = ImageOps.exif_transpose(Image.open(io.BytesIO(mentah))).convert("RGB")
    im.thumbnail((sisi, sisi))
    out = io.BytesIO()
    im.save(out, "JPEG", quality=85)
    return out.getvalue()


# ---------------------------------------------------------------- Claude
def _perintah(kategori: list) -> str:
    return (
        "Ini foto struk belanja di Indonesia. Ekstrak isinya sebagai JSON SAJA (tanpa penjelasan, tanpa markdown) dengan bentuk:\n"
        '{"toko": string|null, "tanggal": "YYYY-MM-DD"|null, "waktu": "HH:MM"|null, "total": integer|null, '
        '"item": [{"nama": string, "qty": number, "harga_satuan": integer, "harga_normal": integer|null, "kategori": string|null}]}\n'
        "Aturan: semua uang dalam rupiah bulat tanpa titik. harga_satuan = harga per satuan yang benar-benar dibayar setelah diskon item. "
        "Kalau struk menunjukkan harga sebelum diskon untuk item itu, isi harga_normal (per satuan), kalau tidak isi null. "
        "Jangan masukkan baris subtotal, total, pajak, tunai, kembalian, poin, atau pembayaran sebagai item. "
        "Perbaiki singkatan nama barang jadi nama yang mudah dibaca. "
        f"kategori: pilih SATU dari daftar ini yang paling cocok, atau null bila ragu: {json.dumps(kategori, ensure_ascii=False)}. "
        "Jangan menebak data yang tidak terlihat; pakai null.")


def _json_dari(teks: str) -> dict:
    m = re.search(r"\{.*\}", teks, re.S)
    if not m:
        raise RuntimeError("Jawaban tidak berbentuk JSON.")
    return json.loads(m.group(0))


def _openai(mentah: bytes, kategori: list, nama: str = "openai") -> dict:
    c = _cfg_oa(nama)
    url = c["base"] + "/chat/completions"
    gambar = "data:image/jpeg;base64," + base64.b64encode(_kecilkan(mentah)).decode("ascii")
    r = requests.post(url, timeout=90, headers={"Authorization": f"Bearer {c['key']}", "Content-Type": "application/json"},
                      json={"model": c["model"], "temperature": 0, "messages": [{"role": "user", "content": [
                          {"type": "text", "text": _perintah(kategori)},
                          {"type": "image_url", "image_url": {"url": gambar}}]}]})
    if r.status_code != 200:
        try:
            e = r.json().get("error", r.text[:200])
            pesan = e.get("message", e) if isinstance(e, dict) else e
        except Exception:
            pesan = r.text[:200]
        raise RuntimeError(f"{nama} menolak ({r.status_code}): {pesan}")
    try:
        teks = r.json()["choices"][0]["message"]["content"]
    except (KeyError, IndexError, ValueError):
        raise RuntimeError(f"Format jawaban {nama} tidak dikenali.")
    if isinstance(teks, list):
        teks = "".join(x.get("text", "") for x in teks if isinstance(x, dict))
    return _rapikan(_json_dari(teks), nama)


def _claude(mentah: bytes, kategori: list) -> dict:
    c = _cfg_claude()
    perintah = _perintah(kategori)
    r = requests.post(URL_API, timeout=90, headers={"x-api-key": c["key"], "anthropic-version": "2023-06-01", "content-type": "application/json"},
                      json={"model": c["model"], "max_tokens": 3000, "messages": [{"role": "user", "content": [
                          {"type": "image", "source": {"type": "base64", "media_type": "image/jpeg",
                                                       "data": base64.b64encode(_kecilkan(mentah)).decode("ascii")}},
                          {"type": "text", "text": perintah}]}]})
    if r.status_code != 200:
        try:
            pesan = r.json().get("error", {}).get("message", r.text[:200])
        except Exception:
            pesan = r.text[:200]
        raise RuntimeError(f"API Anthropic menolak ({r.status_code}): {pesan}")
    teks = "".join(b.get("text", "") for b in r.json().get("content", []) if b.get("type") == "text")
    m = re.search(r"\{.*\}", teks, re.S)
    if not m:
        raise RuntimeError("Jawaban tidak berbentuk JSON.")
    return _rapikan(json.loads(m.group(0)), "claude")


# ---------------------------------------------------------------- Tesseract
def parse_teks(teks: str) -> dict:
    """Parser sederhana untuk teks hasil OCR struk. Kasar: dipakai sebagai saran awal."""
    baris = [b.strip() for b in teks.splitlines() if b.strip()]
    toko = next((b for b in baris[:6] if re.search(r"[A-Za-z]{3,}", b)), None)
    tanggal = waktu = None
    for b in baris:
        m = re.search(r"(\d{1,2})[/\-.](\d{1,2})[/\-.](\d{2,4})", b)
        if m and not tanggal:
            d, mo, y = int(m[1]), int(m[2]), int(m[3])
            y += 2000 if y < 100 else 0
            if 1 <= d <= 31 and 1 <= mo <= 12:
                tanggal = f"{y:04d}-{mo:02d}-{d:02d}"
        m = re.search(r"\b([01]?\d|2[0-3])[:.]([0-5]\d)(?:[:.][0-5]\d)?\b", b)
        if m and not waktu and ":" in b:
            waktu = f"{int(m[1]):02d}:{m[2]}"
    item, total, cadangan_total = [], None, None
    uang = r"(\d{1,3}(?:[.,]\d{3})+|\d{3,8})"
    for b in baris:
        rendah = b.lower()
        # total yang dibayar: 'Total Belanja', 'Grand Total', 'Total Bayar'; 'Total Item' dan 'Total Disc' bukan total
        if re.match(r"^\s*(grand\s*)?total\b", rendah) or re.match(r"^\s*(jumlah\s*(bayar|tagihan)|tagihan)\b", rendah):
            angka_total = re.findall(r"[\d.,]*\d", b)
            if not angka_total or re.search(r"\b(item|disc|diskon|qty|barang)\b", rendah):
                continue
            nilai = angka(angka_total[-1])
            if re.search(r"belanja|bayar|grand|tagihan", rendah):
                total = total or nilai
            elif cadangan_total is None:
                cadangan_total = nilai
            continue
        # potongan harga item: 'Disc. -2,000' berlaku untuk barang di atasnya
        m = re.match(r"^\s*(?:disc(?:ount)?|diskon|potongan|pot\.?|hemat)\b\.?\s*[:\-]?\s*-?\s*(?:rp\.?\s*)?" + uang + r"\s*$", rendah)
        if m and item:
            pot = angka(m[1])
            x = item[-1]
            nilai = x["qty"] * x["harga_satuan"]
            if 0 < pot < nilai:
                x["harga_normal"] = x["harga_satuan"]
                x["harga_satuan"] = max(1, round((nilai - pot) / x["qty"]))
            continue
        if any(k in rendah for k in KATA_ABAI) or re.search(r"\d{9,}", b):
            continue  # baris pembayaran, alamat, nomor telepon, dan sejenisnya
        m = re.match(r"^(?P<nama>.*?[A-Za-z].*?)\s+(?P<q>\d+(?:[.,]\d+)?)\s*[xX@*]\s*(?P<h>[\d.,]+)\s+(?P<t>[\d.,]+)\s*$", b)
        if m:
            qty = float(m["q"].replace(",", "."))
            item.append({"nama": m["nama"].strip(" .-"), "qty": qty, "harga_satuan": angka(m["h"]), "harga_normal": None, "kategori": None})
            continue
        # format minimarket: NAMA  [qty]  harga_satuan  jumlah  (qty kadang salah baca, jadi dihitung dari jumlah / harga satuan)
        m = re.match(r"^(?P<nama>.*?[A-Za-z].*?)\s+(?:\S{1,3}\s+)?(?P<h>" + uang[1:-1] + r")\s+(?P<t>" + uang[1:-1] + r")\s*$", b)
        if m and angka(m["h"]) > 0:
            h_, t_ = angka(m["h"]), angka(m["t"])
            q_ = t_ / h_
            if abs(q_ - round(q_)) < 0.01 and round(q_) >= 1:
                item.append({"nama": m["nama"].strip(" .-"), "qty": float(round(q_)), "harga_satuan": h_, "harga_normal": None, "kategori": None})
                continue
        m = re.match(r"^(?P<nama>.*?[A-Za-z].*?)\s+(?P<t>\d{1,3}(?:[.,]\d{3})+|\d{3,8})\s*$", b)
        if m:
            t = angka(m["t"])
            item.append({"nama": m["nama"].strip(" .-"), "qty": 1, "harga_satuan": t, "harga_normal": None, "kategori": None})
    total = total or cadangan_total
    return _rapikan({"toko": toko, "tanggal": tanggal, "waktu": waktu, "total": total, "item": item}, "tesseract")


def _tesseract(mentah: bytes) -> dict:
    import pytesseract
    from PIL import Image, ImageOps
    im = ImageOps.autocontrast(ImageOps.grayscale(ImageOps.exif_transpose(Image.open(io.BytesIO(_kecilkan(mentah, 2200))))))
    try:
        ada = pytesseract.get_languages()
    except Exception:
        ada = ["eng"]
    bahasa = "+".join(x for x in ("ind", "eng") if x in ada) or "eng"
    return parse_teks(pytesseract.image_to_string(im, lang=bahasa, config="--psm 6"))


# ---------------------------------------------------------------- hasil
def _rapikan(h: dict, mesin: str) -> dict:
    item = []
    for it in h.get("item") or []:
        nama = str(it.get("nama") or "").strip()
        try:
            qty = float(it.get("qty") or 1)
        except (TypeError, ValueError):
            qty = 1.0
        hs = angka(it.get("harga_satuan"))
        hn = angka(it.get("harga_normal")) if it.get("harga_normal") else 0
        if nama and qty > 0 and hs > 0:
            item.append({"nama": nama, "qty": qty, "harga_satuan": hs, "harga_normal": hn if hn > hs else 0,
                         "kategori": it.get("kategori") or None})
    tgl = h.get("tanggal") if re.fullmatch(r"\d{4}-\d{2}-\d{2}", str(h.get("tanggal") or "")) else None
    wkt = h.get("waktu") if re.fullmatch(r"([01]\d|2[0-3]):[0-5]\d", str(h.get("waktu") or "")) else None
    return {"mesin": mesin, "toko": (h.get("toko") or "").strip() or None, "tanggal": tgl, "waktu": wkt,
            "total": angka(h.get("total")) or None, "item": item}


def baca_struk(mentah: bytes, nama_kategori: list) -> dict:
    """Coba tiap mesin yang aktif berurutan; bila gagal lanjut ke berikutnya. Melempar RuntimeError berpesan jelas."""
    mesin = daftar_mesin()
    if not mesin:
        raise RuntimeError("Belum ada mesin baca struk. Lihat README bagian Baca struk otomatis.")
    gagal = []
    for m in mesin:
        try:
            if m == "claude":
                h = _claude(mentah, nama_kategori)
            elif m == "tesseract":
                h = _tesseract(mentah)
            else:
                h = _openai(mentah, nama_kategori, m)
        except Exception as ex:
            gagal.append(f"{m}: {ex}")
            continue
        if h["item"] or m == mesin[-1]:
            if gagal:
                h["gagal"] = gagal
            return h
        gagal.append(f"{m}: tidak ada barang terbaca")
    raise RuntimeError("Semua mesin gagal. " + " | ".join(gagal))


# ---------------------------------------------------------------- pencocokan dengan data sendiri
def _mirip(a: str, b: str) -> float:
    a, b = a.lower().strip(), b.lower().strip()
    if not a or not b:
        return 0.0
    if a == b:
        return 1.0
    if a in b or b in a:
        return 0.9
    return difflib.SequenceMatcher(None, a, b).ratio()


def _norm(s) -> str:
    """Huruf kecil, tanda baca dan spasi ganda dibuang: kunci untuk mengingat koreksi."""
    return re.sub(r"[^a-z0-9]+", " ", str(s or "").lower()).strip()


def _koreksi(bagian: str) -> dict:
    return (D.get("pengaturan", {}).get("koreksi_ocr") or {}).get(bagian, {})


def cocokkan_barang(nama: str):
    """Barang dari daftar yang paling mirip (skor >= 0.72) atau None. Hanya barang kategori pengeluaran.
    Koreksi yang pernah Anda buat untuk tulisan yang sama dipakai lebih dulu."""
    from keuangan.bantu import barang_dari, kat_dari
    ingat = barang_dari(_koreksi("barang").get(_norm(nama)))
    if ingat:
        return ingat
    terbaik, skor = None, 0.0
    for b in D["barang"]:
        k = kat_dari(b["kategori"])
        if k and k["jenis"] != "keluar":
            continue
        s = max(_mirip(nama, b["nama"]), _mirip(nama, f'{b.get("merek", "")} {b["nama"]}'))
        if s > skor:
            terbaik, skor = b, s
    return terbaik if skor >= 0.72 else None


def cocokkan_toko(nama: str):
    from keuangan.bantu import toko_dari
    ingat = toko_dari(_koreksi("toko").get(_norm(nama)))
    if ingat:
        return ingat
    terbaik, skor = None, 0.0
    for x in D["toko"]:
        s = _mirip(nama or "", x["nama"])
        if s > skor:
            terbaik, skor = x, s
    return terbaik if skor >= 0.7 else None


def ke_tabel(hasil: dict) -> pd.DataFrame:
    """Hasil baca jadi DataFrame berkolom editor_kartu."""
    from keuangan.struk import peta_barang, peta_kategori
    _, lab_b = peta_barang()
    id_k, _ = peta_kategori()
    baris = []
    bawaan = next((n for n in id_k if "lain" in n.lower()), next(iter(id_k), None))
    for it in hasil["item"]:
        b = cocokkan_barang(it["nama"])
        kat = it.get("kategori") if it.get("kategori") in id_k else bawaan
        baris.append({"Barang": lab_b.get(b["id"]) if b else None, "Kategori": None if b else kat,
                      "Keterangan": "" if b else _koreksi("nama").get(_norm(it["nama"]), it["nama"]), "Asal": it["nama"],
                      "Banyaknya": float(it["qty"]),
                      "Harga satuan": int(it["harga_satuan"]), "Harga normal": int(it["harga_normal"]) if it.get("harga_normal") else None})
    df = pd.DataFrame(baris, columns=["Barang", "Kategori", "Keterangan", "Asal", "Banyaknya", "Harga satuan", "Harga normal"])
    df["Harga satuan"] = df["Harga satuan"].astype("Int64")
    df["Harga normal"] = df["Harga normal"].astype("Int64")
    return df


# ---------------------------------------------------------------- belajar dari koreksi
MAKS_KOREKSI = 300


def pelajari(hasil: dict, baris: list, toko_id: str) -> int:
    """Bandingkan hasil baca dengan yang akhirnya Anda simpan; ingat koreksinya untuk struk berikutnya.
    Pemanggil yang commit. Kembalikan jumlah koreksi baru."""
    peng = D.setdefault("pengaturan", {})
    kor = peng.setdefault("koreksi_ocr", {})
    for k in ("toko", "barang", "nama"):
        kor.setdefault(k, {})
    baru = 0

    def simpan(bagian: str, kunci: str, nilai: str):
        nonlocal baru
        d = kor[bagian]
        if d.get(kunci) != nilai:
            d.pop(kunci, None)
            d[kunci] = nilai
            baru += 1
            while len(d) > MAKS_KOREKSI:
                d.pop(next(iter(d)))

    for x in baris:
        asal = (x.get("asal") or "").strip()
        n = _norm(asal)
        if not n:
            continue
        if x.get("barang"):
            auto = cocokkan_barang(asal)
            if not auto or auto["id"] != x["barang"]:
                simpan("barang", n, x["barang"])
            kor["nama"].pop(n, None)
        else:
            if kor["barang"].pop(n, None):
                baru += 1
            ket = (x.get("ket") or "").strip()
            if ket and ket != asal:
                simpan("nama", n, ket)
    nama_toko = (hasil or {}).get("toko")
    if nama_toko and toko_id:
        auto = cocokkan_toko(nama_toko)
        if not auto or auto["id"] != toko_id:
            simpan("toko", _norm(nama_toko), toko_id)
    return baru


def _panel_koreksi():
    from keuangan.bantu import barang_dari, catat, selesai_simpan, toko_dari
    kor = D.get("pengaturan", {}).get("koreksi_ocr") or {}
    jml = sum(len(kor.get(k, {})) for k in ("toko", "barang", "nama"))
    with st.expander(f"🧠 Koreksi yang sudah dipelajari ({jml})"):
        if not jml:
            st.caption("Belum ada. Saat Anda mengoreksi hasil baca (mengganti barang, nama, atau toko) lalu menyimpan struk, "
                       "koreksinya diingat dan dipakai di struk berikutnya.")
            return
        for k, f in (("toko", lambda v: (toko_dari(v) or {}).get("nama")), ("barang", lambda v: (barang_dari(v) or {}).get("nama")),
                     ("nama", lambda v: v)):
            for asal, nilai in kor.get(k, {}).items():
                tampil = f(nilai)
                if tampil:
                    st.caption(f"{k.capitalize()}: “{asal}” → {tampil}")
        if not hanya_lihat() and st.button("Lupakan semua koreksi", key="kor_hapus"):
            D["pengaturan"]["koreksi_ocr"] = {"toko": {}, "barang": {}, "nama": {}}
            catat("data", "Hapus koreksi baca struk")
            selesai_simpan("Koreksi dilupakan.")


# ---------------------------------------------------------------- tes koneksi
def _struk_contoh() -> bytes:
    """Gambar struk kecil buatan sendiri untuk menguji mesin (tanpa data pribadi)."""
    import io
    from PIL import Image, ImageDraw, ImageFont
    img = Image.new("RGB", (640, 520), "white")
    d = ImageDraw.Draw(img)
    f = ImageFont.load_default(size=30)
    baris = ["TOKO UJI MAKMUR", "09/11/2026 14:32", "--------------------------", "Indomie Goreng 5 x 3.000   15.000",
             "Aqua 600ml 2 x 3.500        7.000", "--------------------------", "TOTAL                      22.000"]
    for i, b in enumerate(baris):
        d.text((24, 24 + i * 62), b, fill="black", font=f)
    bio = io.BytesIO()
    img.save(bio, "JPEG", quality=90)
    return bio.getvalue()


def tes_mesin(nama: str):
    """Uji satu mesin dengan struk contoh. Kembalikan (berhasil, keterangan)."""
    import time
    mulai = time.time()
    gambar = _struk_contoh()
    try:
        if nama == "claude":
            h = _claude(gambar, ["Makanan"])
        elif nama == "tesseract":
            h = _tesseract(gambar)
        else:
            h = _openai(gambar, ["Makanan"], nama)
    except Exception as ex:
        return False, str(ex)[:300]
    dt = time.time() - mulai
    n = len(h["item"])
    if not n:
        return False, f"Terhubung ({dt:.1f} dtk), tapi tidak ada barang yang terbaca dari struk contoh."
    return True, f"Terhubung ({dt:.1f} dtk). Terbaca {n} barang, total {h.get('total') or '?'} (seharusnya 2 barang, total 22000)."


def halaman_mesin():
    """Pengaturan > Mesin baca struk: lihat mesin yang aktif dan tes tiap satunya."""
    mesin = daftar_mesin()
    if not mesin:
        st.info("Belum ada mesin baca struk yang aktif. Isi kunci di secrets atau pasang Tesseract. Cara lengkapnya ada di README bagian Baca struk otomatis.")
        _panel_koreksi()
        return
    st.markdown("Mesin dicoba berurutan sesuai daftar ini; bila satu gagal, pindah ke berikutnya.")
    for i, m in enumerate(mesin, start=1):
        info = ""
        if m == "claude":
            info = _cfg_claude()["model"]
        elif m != "tesseract":
            c = _cfg_oa(m)
            info = f'{c["model"]} · {c["base"]}'
        with st.container(border=True, key=f"kartu_g_mesin_{m}"):
            st.markdown(f"**{i}. {m}**" + (f"  \n`{info}`" if info else ""))
            if st.button("Tes koneksi", key=f"tes_{m}"):
                with st.spinner("Menguji…"):
                    ok, ket = tes_mesin(m)
                (st.success if ok else st.error)(("✅ " if ok else "❌ ") + ket)
    st.caption("Tes memakai gambar struk contoh buatan aplikasi, tanpa data Anda. Mesin berbayar dikenai biaya sangat kecil per tes.")
    _panel_koreksi()
