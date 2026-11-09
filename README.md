# Pelacak Keuangan

Aplikasi Streamlit untuk mencatat keuangan pribadi: pemasukan, pengeluaran, transfer antar dompet, anggaran bulanan,
tagihan berulang, target tabungan, utang-piutang, dan laporan. Tampilan dan cara pasangnya sama dengan Pelacak Barang.
Data disimpan sebagai satu file `data.json` di repositori GitHub privat.

## Menu
- **Beranda**: total saldo, pemasukan dan pengeluaran bulan terpilih, hal yang perlu perhatian (tagihan jatuh tempo, anggaran hampir atau sudah lewat, utang jatuh tempo, saldo negatif), saldo per dompet, anggaran, target tabungan, grafik. Bagian Beranda bisa disembunyikan di Pengaturan > Tampilan.
- **Transaksi**: Catat transaksi (pemasukan, pengeluaran, transfer dengan biaya admin), Daftar transaksi (filter bulan, jenis, dompet, kategori, kata kunci; ubah dan hapus), Riwayat aktivitas. Menu **Pengaturan** memuat Barang dan produk (misalnya Indomie di Belanja bahan makanan), Toko dan tempat beli (nama, jenis, lokasi), dan Tempat sampah (30 hari). Statistik per barang dan per toko ada di Pantau > Laporan.
- **Pantau**: Anggaran per kategori, Tagihan berulang (tombol Bayar otomatis membuat pengeluaran dan memajukan jatuh tempo), Target tabungan (perkiraan setoran per bulan), Utang-piutang (cicilan, bisa ikut tercatat di dompet), Laporan (bulanan, tren 12 bulan, per dompet).
- **Pengaturan**: Tampilan, Ekspor dan impor (Excel lengkap, CSV transaksi, impor dari Excel/CSV), Dompet, Kategori (kategori utama + sub kategori dengan ikon dan warna, gabungkan saat menghapus), Cadangan dan pulihkan (unduh JSON, titik pulih dari riwayat commit).

Kategori punya dua tingkat: kategori utama (misalnya Rumah) dan sub kategori (misalnya Listrik). Transaksi boleh memakai keduanya. Anggaran, laporan, dan filter pada kategori utama otomatis mencakup semua sub kategorinya. Data lama tanpa sub kategori tetap terbuka (kategori lama jadi kategori utama).

Beranda: pilih periode Minggu, Bulan, Tahun, atau Tanggal custom. Kartu angka dibandingkan dengan periode sebelumnya, ada rata-rata pengeluaran per hari, grafik harian atau bulanan, serta toko dan barang dengan belanja terbesar.

Barang: saat mencatat pengeluaran/pemasukan, pilih kategori lalu barangnya (daftar barang menyesuaikan kategori; kategori utama menampilkan barang semua sub-nya). Isi banyaknya dan harga satuan, total dihitung otomatis, dan harga barang diperbarui dari transaksi terbaru. Barang belum ada bisa ditambah langsung dari halaman Catat transaksi. Laporan > Barang menampilkan total belanja per barang dan grafik perubahan harga.

Kategori dan Sub kategori dipilih di dua kotak terpisah. Toko / tempat beli dipilih dari daftar (atau ditambah langsung di halaman Catat transaksi); lokasi terisi otomatis dari toko tetapi bisa diubah, dan Waktu beli terisi jam sekarang (WIB). Daftar transaksi bisa difilter per toko dan dicari berdasarkan toko atau lokasi. Laporan > Toko menampilkan kunjungan dan total per toko, serta grafik jam belanja.

Saldo dompet tidak disimpan, tetapi dihitung dari saldo awal + semua transaksi, jadi tidak bisa tidak sinkron.
Transfer tidak dihitung sebagai pemasukan atau pengeluaran; biaya admin transfer dihitung sebagai pengeluaran.

## Memasang (sekali saja)
1. Buat dua repositori GitHub **privat**: satu untuk kode (isi folder ini), satu untuk data (kosong, contoh `keuangan-data`, sudah ada branch `main` dengan minimal satu commit, misalnya README).
2. Buat token GitHub (fine-grained) dengan izin **Contents: Read and write** hanya untuk repo data.
3. Buat hash kata sandi: klik dua kali `buat_hash.py` (atau `python buat_hash.py` di terminal). Jendela menunggu Enter, dan hasilnya juga disimpan di `hasil-hash.txt`. Salin blok `[users...]` ke Secrets, lalu hapus `hasil-hash.txt`.
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
Kolom opsional `Barang`, `Banyaknya`, `Harga satuan`, `Toko`, `Lokasi`, `Waktu` (format 14:30; toko baru dibuat otomatis; barang baru dibuat otomatis; Jumlah boleh kosong bila ketiganya diisi). Kolom (kategori boleh `Rumah` atau sub kategori `Rumah › Listrik`): `Tanggal, Jenis, Jumlah, Dompet, Ke dompet, Biaya admin, Kategori, Catatan`. Jenis: Pemasukan, Pengeluaran, atau Transfer.
Tanggal `2026-03-15` atau `15/03/2026`; angka boleh `1.250.000`. Contoh file bisa diunduh di menu impor.

## Struktur kode
`app.py` memanggil `keuangan/rangka.py`. Satu modul per bagian: `inti` (gaya, format, data kosong), `akses` (login), `penyimpanan` (GitHub/lokal),
`bantu` (saldo, bulan, tanggal berulang), `beranda`, `transaksi`, `anggaran`, `tagihan`, `tabungan`, `utang`, `laporan`, `master`,
`ekspor`, `cadangan`, `aktivitas`, `tampilan`, `pwa`.
