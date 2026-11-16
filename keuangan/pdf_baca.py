"""Faktur PDF jadi gambar supaya bisa dibaca mesin baca struk dan disimpan sebagai foto struk."""
import io

MAKS_HALAMAN = 3
LEBAR = 1400


def adalah_pdf(mentah: bytes) -> bool:
    return mentah[:5] == b"%PDF-"


def gambar_dari(mentah: bytes) -> bytes:
    """Kembalikan `mentah` apa adanya bila bukan PDF; kalau PDF, halaman pertama (maks MAKS_HALAMAN) ditumpuk ke bawah jadi satu JPEG."""
    if not adalah_pdf(mentah):
        return mentah
    import pypdfium2 as pdfium
    from PIL import Image, ImageOps
    try:
        dok = pdfium.PdfDocument(mentah)
    except Exception as ex:
        raise RuntimeError(f"PDF tidak bisa dibuka (mungkin terkunci kata sandi atau rusak): {ex}")
    try:
        if len(dok) == 0:
            raise RuntimeError("PDF kosong.")
        hal = []
        for i in range(min(len(dok), MAKS_HALAMAN)):
            p = dok[i]
            skala = LEBAR / max(p.get_width(), 1)
            im = p.render(scale=skala).to_pil().convert("RGB")
            kotak = ImageOps.invert(im.convert("L")).getbbox()  # buang ruang putih kosong di tepi halaman
            if kotak:
                im = im.crop((0, max(0, kotak[1] - 30), im.width, min(im.height, kotak[3] + 30)))
            hal.append(im)
    finally:
        dok.close()
    tinggi = sum(h.height for h in hal)
    kanvas = Image.new("RGB", (max(h.width for h in hal), tinggi), "white")
    y = 0
    for h in hal:
        kanvas.paste(h, (0, y))
        y += h.height
    out = io.BytesIO()
    kanvas.save(out, "JPEG", quality=88)
    return out.getvalue()
