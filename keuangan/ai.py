"""Lapisan privasi untuk semua fitur AI (kecuali baca struk dari foto yang sudah ada sejak awal).

Prinsipnya:
1. Semua fitur AI MATI secara bawaan. Tiap fitur dinyalakan sendiri di Pengaturan > AI dan baca struk > Privasi AI.
2. Hanya data yang perlu yang dikirim (tanpa nominal, tanggal, atau nama toko bila tidak diperlukan), dan nomor panjang,
   email, telepon, serta nama penerima transfer disamarkan dulu di server ini sebelum dikirim.
3. Sebelum mengirim, isi kiriman ditampilkan persis apa adanya dan baru dikirim setelah tombolnya ditekan.
4. Pertanyaan atas data dijawab di server ini: AI hanya menerjemahkan pertanyaan jadi rencana hitung, tidak pernah melihat transaksi.
5. Riwayat kiriman hanya mencatat waktu, fitur, penyedia, dan jumlah butir. Isinya tidak disimpan.
"""
import base64
import io
import json
import re

import requests
import streamlit as st

from keuangan import ocr
from keuangan.bantu import catat, pindah_halaman, selesai_simpan
from keuangan.inti import D, hanya_lihat, sekarang

FITUR = {
    "mutasi": {
        "nama": "Kategorisasi mutasi bank",
        "kirim": "Keterangan mutasi yang kategorinya belum bisa ditebak dari kebiasaanmu (nomor, telepon, email, dan nama penerima disamarkan), "
                 "daftar nama kategori, dan nama platform.",
        "tidak": "Nominal, tanggal, saldo, nama dompet, dan baris yang sudah ketemu kategorinya.",
    },
    "tangkap": {
        "nama": "Tangkap cepat bebas",
        "kirim": "Kalimat yang kamu ketik (nomor panjang disamarkan), daftar nama kategori, nama dompet, dan nama platform.",
        "tidak": "Transaksi lama, saldo, dan daftar toko.",
    },
    "layar": {
        "nama": "Baca tangkapan layar pesanan online",
        "kirim": "Gambar tangkapan layar yang sudah kamu potong (data lokasi di dalam berkas gambar dibuang), daftar nama kategori, dan nama platform.",
        "tidak": "Isi transaksi lain. Nama pemesan, alamat, dan telepon di gambar tetap terkirim bila ada di bagian yang tidak kamu potong.",
    },
    "tanya": {
        "nama": "Tanya data dengan bahasa biasa",
        "kirim": "Hanya kalimat pertanyaanmu (nomor panjang disamarkan), tanggal hari ini, nama kategori, dan nama platform.",
        "tidak": "Transaksi, nominal, nama toko, dan dompet. Perhitungan dikerjakan di server ini, bukan oleh AI.",
    },
    "ringkasan": {
        "nama": "Ringkasan bulanan tertulis",
        "kirim": "Angka agregat satu bulan dan bulan sebelumnya: total masuk dan keluar, total per kategori (dibulatkan ke ribuan), dan total online. "
                 "Nama toko hanya ikut bila kamu mencentangnya.",
        "tidak": "Transaksi satu per satu, catatan, tanggal, nama dompet, dan nominal yang tidak dibulatkan.",
    },
}
NAMA_PENYEDIA = {"claude": "Anthropic", "openai": "OpenAI", "openrouter": "OpenRouter (diteruskan ke model pilihan)", "gemini": "Google (Gemini)"}
MAKS_LOG = 50


# ---------------------------------------------------------------- pengaturan
def _cfg() -> dict:
    c = D["pengaturan"].setdefault("ai", {})
    c.setdefault("fitur", {})
    c.setdefault("log", [])
    c.setdefault("mesin", "")
    return c


def mesin_awan() -> list:
    """Mesin AI di internet yang kuncinya sudah diisi. Tesseract tidak dihitung karena berjalan di server sendiri."""
    return [m for m in ocr.daftar_mesin() if m != "tesseract"]


def mesin_dipakai() -> str:
    ada = mesin_awan()
    pilihan = _cfg().get("mesin")
    return pilihan if pilihan in ada else (ada[0] if ada else "")


def aktif(fitur: str) -> bool:
    return bool(_cfg()["fitur"].get(fitur))


def boleh(fitur: str):
    """(True, '') bila fitur boleh mengirim data; selain itu (False, alasan)."""
    if fitur not in FITUR:
        return False, "Fitur tidak dikenal."
    if not aktif(fitur):
        return False, "Fitur ini belum dinyalakan di Pengaturan > AI dan baca struk > Privasi AI."
    if not mesin_dipakai():
        return False, "Belum ada kunci penyedia AI (lihat README bagian Baca struk otomatis)."
    return True, ""


# ---------------------------------------------------------------- penyamaran
_POLA_EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
_POLA_URL = re.compile(r"(?i)https?://\S+|www\.\S+")
_POLA_HP = re.compile(r"(?<!\d)(?:\+62|62|0)8[\d\s-]{7,13}\d(?!\d)")
_POLA_KARTU = re.compile(r"(?<!\d)\d{4}[ -]\d{4}[ -]\d{4}[ -]\d{1,7}(?!\d)")
_POLA_NAMA = re.compile(r"(?i)\b(trsf|trf|transfer|bi-?fast|skn|rtgs|tf)\b(.*?)\b(ke|dari|to|from|an|a\.n\.?|atas nama)\s+([a-z.' ]{3,40})")


_POLA_TRANSFER = re.compile(r"(?i)\b(trsf|trf|transfer|tf|bi-?fast|skn|rtgs)\b")
_POLA_EKOR = re.compile(r"(\b(?:CR|DB)\s+|[\d/\]]\s+)([A-Za-z.']{2,}(?:\s+[A-Za-z.']{2,}){0,3})$", re.I)


def samarkan(teks: str, ketat: bool = False, kecuali: tuple | list = ()):
    """Ganti data pribadi dengan penanda. Kembalian: (teks aman, jumlah bagian yang diganti).

    ketat=True dipakai untuk keterangan mutasi (tanpa nominal): angka 6 digit ke atas dan nama penerima transfer ikut disamarkan.
    Pada baris transfer, kata-kata di ujung baris (biasanya nama penerima) disamarkan kecuali memuat salah satu nama di `kecuali` (platform, toko).
    ketat=False dipakai untuk kalimat ketikan: nominal tetap utuh, hanya angka 10 digit ke atas (rekening, kartu, telepon) yang diganti.
    """
    s, n = str(teks or ""), 0

    def ganti(pola, pengganti, s, n):
        s2, k = pola.subn(pengganti, s)
        return s2, n + k

    s, n = ganti(_POLA_EMAIL, "[email]", s, n)
    s, n = ganti(_POLA_URL, "[tautan]", s, n)
    s, n = ganti(_POLA_HP, "[telepon]", s, n)
    s, n = ganti(_POLA_KARTU, "[nomor]", s, n)
    if ketat:
        s2, k = _POLA_NAMA.subn(lambda m: f"{m.group(1)}{m.group(2)}{m.group(3)} [nama]", s)
        s, n = s2, n + k
        if _POLA_TRANSFER.search(s):
            aman = [str(x).lower() for x in kecuali if str(x).strip()]
            m = _POLA_EKOR.search(s)
            if m and not any(a in m.group(2).lower() for a in aman):
                s, n = s[:m.start(2)] + "[nama]", n + 1
    s, n = ganti(re.compile(r"\d{6,}" if ketat else r"\d{10,}"), "[nomor]", s, n)
    return re.sub(r"\s+", " ", s).strip(), n


def siapkan_gambar(mentah: bytes, atas: int = 0, bawah: int = 0) -> bytes:
    """Potong bagian atas dan bawah (persen), kecilkan, lalu simpan ulang sebagai JPEG. Penyimpanan ulang membuang EXIF termasuk lokasi GPS."""
    from PIL import Image, ImageOps
    im = ImageOps.exif_transpose(Image.open(io.BytesIO(mentah))).convert("RGB")
    w, h = im.size
    a, b = int(h * max(0, min(atas, 60)) / 100), int(h * (1 - max(0, min(bawah, 60)) / 100))
    if b - a >= 50:
        im = im.crop((0, a, w, b))
    im.thumbnail((1600, 1600))
    out = io.BytesIO()
    im.save(out, "JPEG", quality=85)
    return out.getvalue()


# ---------------------------------------------------------------- pengiriman
def _galat_api(r, nama: str) -> RuntimeError:
    try:
        e = r.json().get("error", r.text[:200])
        pesan = e.get("message", e) if isinstance(e, dict) else e
    except Exception:
        pesan = r.text[:200]
    return RuntimeError(f"{nama} menolak ({r.status_code}): {pesan}")


def _kirim(mesin: str, sistem: str, pengguna: str, jpeg: bytes | None = None, maks: int = 1500) -> str:
    """Satu panggilan ke penyedia. Hanya fungsi ini yang menyentuh jaringan; pesan galat tidak memuat isi kiriman."""
    if mesin == "claude":
        c = ocr._cfg_claude()
        isi = []
        if jpeg:
            isi.append({"type": "image", "source": {"type": "base64", "media_type": "image/jpeg", "data": base64.b64encode(jpeg).decode("ascii")}})
        isi.append({"type": "text", "text": pengguna})
        r = requests.post(ocr.URL_API, timeout=90, headers={"x-api-key": c["key"], "anthropic-version": "2023-06-01", "content-type": "application/json"},
                          json={"model": c["model"], "max_tokens": maks, "system": sistem, "messages": [{"role": "user", "content": isi}]})
        if r.status_code != 200:
            raise _galat_api(r, "API Anthropic")
        return "".join(b.get("text", "") for b in r.json().get("content", []) if b.get("type") == "text")
    c = ocr._cfg_oa(mesin)
    if not c:
        raise RuntimeError(f"Kunci {mesin} tidak ditemukan.")
    isi = [{"type": "text", "text": pengguna}]
    if jpeg:
        isi.append({"type": "image_url", "image_url": {"url": "data:image/jpeg;base64," + base64.b64encode(jpeg).decode("ascii")}})
    r = requests.post(c["base"] + "/chat/completions", timeout=90, headers={"Authorization": f"Bearer {c['key']}", "Content-Type": "application/json"},
                      json={"model": c["model"], "temperature": 0, "max_tokens": maks,
                            "messages": [{"role": "system", "content": sistem}, {"role": "user", "content": isi}]})
    if r.status_code != 200:
        raise _galat_api(r, mesin)
    try:
        teks = r.json()["choices"][0]["message"]["content"]
    except (KeyError, IndexError, ValueError):
        raise RuntimeError(f"Format jawaban {mesin} tidak dikenali.")
    return "".join(x.get("text", "") for x in teks if isinstance(x, dict)) if isinstance(teks, list) else str(teks or "")


def tanya(fitur: str, sistem: str, pengguna: str, jpeg: bytes | None = None, maks: int = 1500, item: int = 1) -> str:
    """Satu-satunya pintu keluar data ke AI. Menolak (PermissionError) bila fitur belum dinyalakan, apa pun yang dilakukan tampilan."""
    ok, alasan = boleh(fitur)
    if not ok:
        raise PermissionError(alasan)
    mesin = mesin_dipakai()
    teks = _kirim(mesin, sistem, pengguna, jpeg, maks)
    log = _cfg()["log"]
    log.append({"waktu": sekarang().strftime("%Y-%m-%d %H:%M"), "fitur": fitur, "mesin": mesin, "item": int(item)})
    del log[:-MAKS_LOG]
    return teks


def json_dari(teks: str):
    """Ambil objek atau daftar JSON pertama dari jawaban AI."""
    m = re.search(r"(\{.*\}|\[.*\])", str(teks or ""), re.S)
    if not m:
        raise RuntimeError("Jawaban AI tidak berbentuk JSON.")
    try:
        return json.loads(m.group(1))
    except ValueError:
        raise RuntimeError("Jawaban AI tidak bisa dibaca sebagai JSON.")


def tanya_json(fitur: str, sistem: str, pengguna: str, jpeg: bytes | None = None, maks: int = 1500, item: int = 1) -> str:
    """Seperti tanya(), tetapi jawabannya harus memuat JSON. Bila tidak, coba sekali lagi dengan instruksi lebih tegas dan batas panjang dua kali lipat
    (model yang 'berpikir' sering kehabisan batas atau menjawab dengan kalimat). Isi kiriman sama persis, jadi tercakup persetujuan yang sama."""
    teks = tanya(fitur, sistem, pengguna, jpeg, maks, item)
    try:
        json_dari(teks)
        return teks
    except RuntimeError:
        pass
    teks2 = tanya(fitur, sistem + " PENTING: balas HANYA satu JSON yang valid, tanpa kalimat pembuka, tanpa penjelasan, tanpa markdown.", pengguna, jpeg, maks * 2, item)
    try:
        json_dari(teks2)
        return teks2
    except RuntimeError:
        isi = (teks2 or teks or "").strip()
        raise RuntimeError("Jawaban AI tidak berbentuk JSON, bahkan setelah dicoba dua kali. "
                           + (f"Isi jawabannya: {isi[:160]!r}." if isi else "Jawabannya kosong; model yang memakai mode berpikir bisa kehabisan batas panjang. Coba model lain di pengaturan kunci."))


# ---------------------------------------------------------------- tampilan bersama
def gerbang(fitur: str, kunci: str = "") -> bool:
    """True bila fitur boleh dipakai. Bila tidak, tampilkan alasannya dan jalan pintas ke pengaturan."""
    ok, alasan = boleh(fitur)
    if ok:
        return True
    st.info(f"{FITUR[fitur]['nama']} memakai AI di internet. {alasan}")
    st.button("Buka Privasi AI", key=f"gerbang_{fitur}_{kunci}", on_click=pindah_halaman, args=("Privasi AI",))
    return False


def kirim_dengan_pratinjau(fitur: str, paket: dict, kunci: str, label: str = "Kirim dan minta saran", bentuk_json: bool = False):
    """Tampilkan tujuan dan isi kiriman apa adanya, lalu kirim hanya bila tombol ditekan. Kembalian: teks jawaban pada putaran saat tombol ditekan, selain itu None.

    paket: {"sistem", "pengguna", "jpeg" (opsional), "ringkas", "samar" (jumlah bagian disamarkan), "item", "maks" (opsional)}
    """
    mesin = mesin_dipakai()
    st.caption(f"Akan dikirim ke **{NAMA_PENYEDIA.get(mesin, mesin)}**: {paket['ringkas']}"
               + (f" ({paket['samar']} bagian disamarkan)" if paket.get("samar") else ""))
    with st.expander("Lihat persis yang akan dikirim"):
        st.code(paket["pengguna"], language="json")
        if paket.get("jpeg"):
            st.image(paket["jpeg"], caption="Gambar yang akan dikirim", width=260)
    if st.button(label, key=f"kirim_{fitur}_{kunci}", type="primary"):
        try:
            with st.spinner("Menunggu jawaban AI…"):
                return (tanya_json if bentuk_json else tanya)(fitur, paket["sistem"], paket["pengguna"], paket.get("jpeg"), paket.get("maks", 1500), paket.get("item", 1))
        except (RuntimeError, PermissionError) as ex:
            st.error(str(ex))
    return None


# ---------------------------------------------------------------- halaman Privasi AI
def halaman_privasi_ai():
    c = _cfg()
    st.markdown("Fitur AI membaca teks yang berantakan (keterangan mutasi, kalimat ketikan, tangkapan layar). **Semuanya mati sampai kamu menyalakannya**, "
                "dan tiap pengiriman selalu menampilkan dulu isinya.")
    ada = mesin_awan()
    if not ada:
        st.warning("Belum ada kunci penyedia AI, jadi fitur di bawah belum bisa dipakai. Isi kunci di secrets seperti untuk Baca struk otomatis (lihat README).")
    elif len(ada) > 1:
        pilih = st.selectbox("Penyedia yang dipakai", ada, index=ada.index(mesin_dipakai()), format_func=lambda m: NAMA_PENYEDIA.get(m, m), key="ai_mesin",
                             disabled=hanya_lihat())
    else:
        pilih = ada[0]
        st.caption(f"Penyedia: **{NAMA_PENYEDIA.get(pilih, pilih)}**")
    with st.form("f_privasi_ai"):
        nilai = {}
        for kode, f in FITUR.items():
            nilai[kode] = st.checkbox(f["nama"], value=bool(c["fitur"].get(kode)), key=f"ai_sw_{kode}", disabled=hanya_lihat())
            st.caption(f"**Dikirim:** {f['kirim']}")
            st.caption(f"**Tidak dikirim:** {f['tidak']}")
        if st.form_submit_button("Simpan pengaturan", type="primary", disabled=hanya_lihat()):
            c["fitur"] = {k: bool(v) for k, v in nilai.items()}
            if ada:
                c["mesin"] = pilih
            catat("pengaturan", "Ubah pengaturan Privasi AI: " + (", ".join(FITUR[k]["nama"] for k, v in nilai.items() if v) or "semua mati"))
            selesai_simpan("Pengaturan Privasi AI disimpan.")
    st.markdown("**Yang perlu kamu tahu**")
    st.caption("Penyamaran otomatis hanya menangkap pola umum (nomor panjang, telepon, email, nama setelah kata transfer). Nama orang di tempat lain tidak selalu terdeteksi, "
               "jadi periksa kotak pratinjau sebelum mengirim.")
    st.caption("Berapa lama penyedia menyimpan kiriman dan apakah dipakai untuk melatih model mengikuti kebijakan penyedia itu. Cek kebijakannya sebelum menyalakan fitur.")
    st.caption("Baca struk dari foto (fitur lama) tidak lewat saklar ini: bila ada kunci penyedia, foto struk yang kamu minta dibaca ikut dikirim ke penyedia itu.")
    log = c["log"]
    st.markdown(f"**Riwayat kiriman** ({len(log)})")
    if not log:
        st.caption("Belum ada kiriman. Riwayat hanya mencatat waktu, fitur, penyedia, dan jumlah butir, tidak pernah isinya.")
    for x in reversed(log[-10:]):
        st.caption(f"{x['waktu']} · {FITUR.get(x['fitur'], {}).get('nama', x['fitur'])} · {NAMA_PENYEDIA.get(x['mesin'], x['mesin'])} · {x['item']} butir")
    if log and not hanya_lihat() and st.button("Hapus riwayat kiriman", key="ai_hapus_log"):
        c["log"] = []
        selesai_simpan("Riwayat kiriman AI dihapus.")
