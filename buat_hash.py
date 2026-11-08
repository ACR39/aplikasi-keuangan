"""Membuat password_hash untuk secrets: python buat_hash.py"""
import getpass
import hashlib
import os

sandi = getpass.getpass("Kata sandi: ")
ulang = getpass.getpass("Ulangi kata sandi: ")
if sandi != ulang or len(sandi) < 8:
    raise SystemExit("Kata sandi tidak sama atau kurang dari 8 karakter.")
iterasi = 200_000
garam = os.urandom(16)
h = hashlib.pbkdf2_hmac("sha256", sandi.encode("utf-8"), garam, iterasi)
print(f'\npassword_hash = "pbkdf2${iterasi}${garam.hex()}${h.hex()}"')
