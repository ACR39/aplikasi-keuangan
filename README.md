# Pelacak Keuangan

Aplikasi Streamlit untuk mencatat keuangan pribadi: pemasukan, pengeluaran, transfer antar dompet, anggaran bulanan,
tagihan berulang, target tabungan, utang-piutang, dan laporan. Tampilan dan cara pasangnya sama dengan Pelacak Barang.
Data disimpan sebagai satu file `data.json` di repositori GitHub privat.

## Menu
- **Beranda**: total saldo, pemasukan dan pengeluaran bulan terpilih, hal yang perlu perhatian (tagihan jatuh tempo, anggaran hampir atau sudah lewat, utang jatuh tempo, saldo negatif), saldo per dompet, anggaran, target tabungan, grafik. Bagian Beranda bisa disembunyikan di Pengaturan > Tampilan.
- **Transaksi**: Catat transaksi (pemasukan, pengeluaran, transfer dengan biaya admin), Daftar transaksi (filter bulan, jenis, dompet, kategori, kata kunci; ubah dan hapus), Riwayat aktivitas, Tempat sampah (30 hari).
- **Pantau**: Anggaran per kategori, Tagihan berulang (tombol Bayar otomatis membuat pengeluaran dan memajukan jatuh tempo), Target tabungan (perkiraan setoran per bulan), Utang-piutang (cicilan, bisa ikut tercatat di dompet), Laporan (bulanan, tren 12 bulan, per dompet).
- **Pengaturan**: Tampilan, Ekspor dan impor (Excel lengkap, CSV transaksi, impor dari Excel/CSV), Dompet, Kategori (gabungkan saat menghapus), Cadangan dan pulihkan (unduh JSON, titik pulih dari riwayat commit).

Saldo dompet tidak disimpan, tetapi dihitung dari saldo awal + semua transaksi, jadi tidak bisa tidak sinkron.
Transfer tidak dihitung sebagai pemasukan atau pengeluaran; biaya admin transfer dihitung sebagai pengeluaran.

## Memasang (sekali saja)
1. Buat dua repositori GitHub **privat**: satu untuk kode (isi folder ini), satu untuk data (kosong, contoh `keuangan-data`, sudah ada branch `main` dengan minimal satu commit, misalnya README).
2. Buat token GitHub (fine-grained) dengan izin **Contents: Read and write** hanya untuk repo data.
3. Buat hash kata sandi: `python buat_hash.py`, salin hasilnya.
4. Di Streamlit Community Cloud: New app, pilih repo kode, file utama `app.py`. Di Settings > Secrets tempel isi `.streamlit/secrets.toml.contoh` yang sudah diisi (token, repo data, user + hash).
5. Pasang di HP: lihat `PWA-PANDUAN.md` di Pelacak Barang. Berkas ikon dan `enableStaticServing` sudah ada di sini.

Tanpa bagian `[github]` aplikasi memakai file lokal `data_lokal.json` (mode uji coba). Tanpa `[users]` aplikasi tanpa login.

## Menjalankan di komputer
```
pip install -r requirements.txt
streamlit run app.py
```

## Peran
- `admin`: semuanya, termasuk Dompet, Kategori, Cadangan.
- `pengisi`: mencatat dan mengubah transaksi, anggaran, tagihan, dan lainnya, tanpa menu master.
- `lihat`: hanya melihat dan mengekspor.

## Format impor
Kolom: `Tanggal, Jenis, Jumlah, Dompet, Ke dompet, Biaya admin, Kategori, Catatan`. Jenis: Pemasukan, Pengeluaran, atau Transfer.
Tanggal `2026-03-15` atau `15/03/2026`; angka boleh `1.250.000`. Contoh file bisa diunduh di menu impor.

## Struktur kode
`app.py` memanggil `keuangan/rangka.py`. Satu modul per bagian: `inti` (gaya, format, data kosong), `akses` (login), `penyimpanan` (GitHub/lokal),
`bantu` (saldo, bulan, tanggal berulang), `beranda`, `transaksi`, `anggaran`, `tagihan`, `tabungan`, `utang`, `laporan`, `master`,
`ekspor`, `cadangan`, `aktivitas`, `tampilan`, `pwa`.
