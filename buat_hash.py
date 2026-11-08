"""Membuat password_hash untuk secrets Streamlit.

Cara pakai: klik dua kali berkas ini (atau jalankan `python buat_hash.py`).
Hasilnya ditampilkan DAN disimpan ke berkas hasil-hash.txt di folder yang sama,
jadi tidak hilang walau jendela tertutup. Hapus hasil-hash.txt setelah disalin.
"""
import getpass
import hashlib
import os
import sys


def jeda():
    try:
        input("\nTekan Enter untuk menutup...")
    except Exception:
        pass


def main():
    print("Pembuat password_hash untuk Pelacak Keuangan")
    print("(ketikan kata sandi tidak tampil di layar, itu normal)\n")
    username = input("Username (contoh: anda): ").strip().lower() or "anda"
    sandi = getpass.getpass("Kata sandi (minimal 8 karakter): ")
    ulang = getpass.getpass("Ulangi kata sandi: ")
    if sandi != ulang:
        print("\nKata sandi tidak sama. Jalankan lagi.")
        return
    if len(sandi) < 8:
        print("\nKata sandi kurang dari 8 karakter. Jalankan lagi.")
        return
    iterasi = 200_000
    garam = os.urandom(16)
    h = hashlib.pbkdf2_hmac("sha256", sandi.encode("utf-8"), garam, iterasi)
    blok = (f'[users.{username}]\nnama = "Nama Anda"\nperan = "admin"\n'
            f'password_hash = "pbkdf2${iterasi}${garam.hex()}${h.hex()}"\n')
    lokasi = os.path.join(os.path.dirname(os.path.abspath(__file__)), "hasil-hash.txt")
    with open(lokasi, "w", encoding="utf-8") as f:
        f.write(blok)
    print("\nSalin blok di bawah ini ke Streamlit > Settings > Secrets:\n")
    print(blok)
    print(f"Hasil juga tersimpan di: {lokasi}")


try:
    main()
except KeyboardInterrupt:
    print("\nDibatalkan.")
except Exception as e:
    print(f"\nTerjadi kesalahan: {e}")
    if sys.platform == "win32":
        print("Kalau Python belum terpasang, pasang dari python.org dan centang 'Add python.exe to PATH'.")
jeda()
