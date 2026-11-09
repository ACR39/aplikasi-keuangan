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

Rincian barang: barcode (bisa dicari langsung di halaman Catat, cocok dengan pembaca barcode USB/Bluetooth), merek, ukuran, tanggal kedaluwarsa (muncul di Perlu perhatian saat tinggal 14 hari), barang langganan, catatan, dan foto. Rincian toko: tautan peta, jam buka, telepon, catatan, favorit, dan foto. Transaksi bisa dilampiri foto struk. Laporan > Barang punya tabel Harga per toko.

Titik lokasi toko: ketuk peta (OpenStreetMap, gratis tanpa kunci API) atau tekan Pakai lokasi saya sekarang saat berada di toko. Titik disimpan sebagai koordinat, tombol Titik di peta membuka Google Maps ke koordinat itu, dan toggle Lihat semua toko di peta menampilkan semua pin. Lokasi saat ini butuh HTTPS dan izin lokasi di browser (Streamlit Cloud sudah HTTPS).

Satu struk, banyak barang: di Catat transaksi > Pengeluaran pilih "Satu struk, banyak barang", isi kartu barang satu per satu (pilih Barang atau Kategori, banyaknya, harga; harga kosong memakai harga terakhir; tombol Tambah barang untuk kartu berikutnya), lalu simpan. Tiap baris menjadi satu transaksi biasa yang berbagi tanggal, waktu, toko, lokasi, dompet, dan foto struk, jadi semua laporan tetap bekerja.

Daftar belanja (menu Transaksi): buat daftar, tambah barang atau barang langganan, lihat toko termurah tiap barang dari riwayat dan perkiraan penghematannya, centang yang sudah dibeli, lalu "Selesai belanja, catat" untuk menyimpannya sebagai satu struk. Daftar yang habis masuk ke Daftar selesai dan bisa dipakai lagi.

Salin transaksi: tombol Salin di Daftar transaksi membuka Catat transaksi dengan isi yang sama, tanggal dan jam diganti ke sekarang.

Diskon: saat mencatat barang, isi Harga normal (sebelum diskon) di samping Harga satuan (yang dibayar). Daftar transaksi menampilkan label diskon, dan Laporan > Barang menampilkan grafik harga normal dibanding harga bayar, berapa kali barang dibeli saat diskon, rata-rata diskon, total hemat, dan daftar pembelian diskon. Di mode struk, setiap kartu barang punya isian Harga normal yang sama.

Foto disimpan sebagai berkas terpisah (folder `foto/` di repo GitHub, atau `data_lokal.json.foto/` saat mode uji coba), diperkecil otomatis, dan di data hanya tercatat namanya. Berkas cadangan JSON tidak memuat foto; folder `foto/` di repo sudah menjadi cadangannya.

Barang: saat mencatat pengeluaran/pemasukan, pilih kategori lalu barangnya (daftar barang menyesuaikan kategori; kategori utama menampilkan barang semua sub-nya). Isi banyaknya dan harga satuan, total dihitung otomatis, dan harga barang diperbarui dari transaksi terbaru. Barang dan toko ditambah lewat Pengaturan (formulirnya muncul setelah menekan tombol Tambah). Laporan > Barang menampilkan total belanja per barang dan grafik perubahan harga.

Kategori dan Sub kategori dipilih di dua kotak terpisah. Toko / tempat beli dipilih dari daftar (atau ditambah langsung di halaman Catat transaksi); lokasi terisi otomatis dari toko tetapi bisa diubah, dan Waktu beli terisi jam sekarang (WIB). Daftar transaksi bisa difilter per toko dan dicari berdasarkan toko atau lokasi. Laporan > Toko menampilkan kunjungan dan total per toko, serta grafik jam belanja.

Saldo dompet tidak disimpan, tetapi dihitung dari saldo awal + semua transaksi, jadi tidak bisa tidak sinkron.
Transfer tidak dihitung sebagai pemasukan atau pengeluaran; biaya admin transfer dihitung sebagai pengeluaran.

## Baca struk otomatis
Di Catat transaksi, mode Struk: unggah foto struk lalu tekan **Baca isi struk dari foto ini**. Toko, tanggal, jam, dan daftar barang terisi sendiri; periksa lagi sebelum menyimpan. Total di struk dibandingkan dengan jumlah barang.

Dua mesin, dipilih otomatis:
- **Claude** (lebih akurat, mengenali diskon): isi `[anthropic] api_key` di secrets. Foto dikirim ke Anthropic dan ada biaya per foto.
- **Tesseract** (gratis, jalan di server sendiri, hasil lebih kasar): `packages.txt` sudah memuat `tesseract-ocr` dan paket bahasa Indonesia; di komputer sendiri pasang Tesseract dan `pytesseract`.

Tanpa keduanya, formulir struk tetap bisa diisi manual.

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
