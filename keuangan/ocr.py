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

from keuangan.inti import D

MODEL_BAWAAN = "claude-sonnet-5-5"
URL_API = "https://api.anthropic.com/v1/messages"
KATA_ABAI = ("total", "subtotal", "sub total", "tunai", "cash", "kembali", "change", "bayar", "ppn", "pajak", "tax", "kartu", "debit",
             "kredit", "qris", "voucher", "poin", "point", "hemat", "item", "terima kasih", "thank", "npwp", "kasir", "struk", "no.", "nomor")


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
    item, total = [], None
    for b in baris:
        rendah = b.lower()
        if re.match(r"^\s*(grand\s*)?total\b", rendah):
            angka_total = re.findall(r"[\d.,]*\d", b)
            if angka_total and not total:
                total = angka(angka_total[-1])
            continue
        if any(k in rendah for k in KATA_ABAI):
            continue
        m = re.match(r"^(?P<nama>.*?[A-Za-z].*?)\s+(?P<q>\d+(?:[.,]\d+)?)\s*[xX@*]\s*(?P<h>[\d.,]+)\s+(?P<t>[\d.,]+)\s*$", b)
        if m:
            qty = float(m["q"].replace(",", "."))
            item.append({"nama": m["nama"].strip(" .-"), "qty": qty, "harga_satuan": angka(m["h"]), "harga_normal": None, "kategori": None})
            continue
        m = re.match(r"^(?P<nama>.*?[A-Za-z].*?)\s+(?P<t>\d{1,3}(?:[.,]\d{3})+|\d{3,})\s*$", b)
        if m:
            t = angka(m["t"])
            item.append({"nama": m["nama"].strip(" .-"), "qty": 1, "harga_satuan": t, "harga_normal": None, "kategori": None})
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


def cocokkan_barang(nama: str):
    """Barang dari daftar yang paling mirip (skor >= 0.72) atau None. Hanya barang kategori pengeluaran."""
    from keuangan.bantu import kat_dari
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
                      "Keterangan": "" if b else it["nama"], "Banyaknya": float(it["qty"]),
                      "Harga satuan": int(it["harga_satuan"]), "Harga normal": int(it["harga_normal"]) if it.get("harga_normal") else None})
    df = pd.DataFrame(baris, columns=["Barang", "Kategori", "Keterangan", "Banyaknya", "Harga satuan", "Harga normal"])
    df["Harga satuan"] = df["Harga satuan"].astype("Int64")
    df["Harga normal"] = df["Harga normal"].astype("Int64")
    return df
