"""Baca barcode dari foto dan cari data produknya di Open Food Facts (database terbuka, tanpa kunci)."""
import io

import requests

UA = "PelacakKeuangan/1.0 (aplikasi pribadi)"
URL_OFF = "https://world.openfoodfacts.org/api/v2/product/{}.json"


def baca_barcode(mentah: bytes) -> str:
    """Kode barcode pertama yang terbaca dari foto, atau ''. Mencoba beberapa ukuran dan putaran."""
    import zxingcpp
    from PIL import Image, ImageOps
    img = ImageOps.exif_transpose(Image.open(io.BytesIO(mentah))).convert("L")
    for sisi in (1600, 1000, 2400):
        k = img.copy()
        k.thumbnail((sisi, sisi))
        for putar in (0, 90, 270, 180):
            hasil = zxingcpp.read_barcodes(k.rotate(putar, expand=True) if putar else k)
            kode = next((h.text.strip() for h in hasil if h.text and h.text.strip()), "")
            if kode:
                return kode
    return ""


def cari_produk(kode: str):
    """Data produk dari Open Food Facts: dict nama/merek/ukuran/foto_bytes, atau None bila tidak ada. Error jaringan dilempar."""
    r = requests.get(URL_OFF.format(kode), timeout=15, headers={"User-Agent": UA},
                     params={"fields": "product_name,brands,quantity,image_front_small_url"})
    if r.status_code == 404:
        return None
    r.raise_for_status()
    j = r.json()
    if j.get("status") != 1:
        return None
    p = j.get("product") or {}
    nama = (p.get("product_name") or "").strip()
    if not nama:
        return None
    foto = None
    url = p.get("image_front_small_url") or ""
    if url.startswith("https://"):
        try:
            f = requests.get(url, timeout=15, headers={"User-Agent": UA})
            if f.status_code == 200 and len(f.content) < 3_000_000:
                foto = f.content
        except requests.RequestException:
            pass
    return {"nama": nama, "merek": (p.get("brands") or "").split(",")[0].strip(),
            "ukuran": (p.get("quantity") or "").strip(), "foto_bytes": foto}
