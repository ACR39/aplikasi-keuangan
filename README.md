# Pelacak Keuangan

Aplikasi Streamlit untuk mencatat keuangan pribadi: pemasukan, pengeluaran, transfer antar dompet, anggaran bulanan,
tagihan berulang, target tabungan, utang-piutang, dan laporan. Tampilan dan cara pasangnya sama dengan Pelacak Barang.
Data disimpan sebagai satu file `data.json` di repositori GitHub privat.

## Menu
- **Beranda**: total saldo, pemasukan dan pengeluaran bulan terpilih, hal yang perlu perhatian (tagihan jatuh tempo, anggaran hampir atau sudah lewat, utang jatuh tempo, saldo negatif), saldo per dompet, anggaran, target tabungan, grafik. Bagian Beranda bisa disembunyikan di Pengaturan > Tampilan.
- **Transaksi**: Catat transaksi (pemasukan, pengeluaran, transfer dengan biaya admin), Daftar transaksi (filter bulan, jenis, dompet, kategori, kata kunci; ubah dan hapus), Riwayat aktivitas. Menu **Pengaturan** memuat Barang dan produk (misalnya Indomie di Belanja bahan makanan), Toko dan tempat beli (nama, jenis, lokasi), dan Tempat sampah (30 hari). Statistik per barang dan per toko ada di Pantau > Laporan.
- **Pantau**: Anggaran per kategori, Transaksi berulang (tombol Bayar otomatis membuat pengeluaran dan memajukan jatuh tempo), Target tabungan (perkiraan setoran per bulan), Utang-piutang (cicilan, bisa ikut tercatat di dompet), Laporan (bulanan, tren 12 bulan, per dompet).
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

**Beli online**: pengeluaran bisa ditandai lewat platform (GoFood, GrabFood, ShopeeFood, Lainnya; kotak "Beli online lewat"), baik di satu barang maupun di satu struk banyak barang. Daftar platform diatur sendiri di Pengaturan > Platform beli online (tambah, ubah nama, hapus; platform yang sudah dipakai bisa dipindah ke platform lain saat dihapus). Transaksi tanpa platform dianggap beli langsung, jadi data lama tidak perlu diubah. Daftar transaksi punya filter "Beli online" (semua online, hanya offline, atau satu platform). Beranda (bagian "Belanja online vs offline", bisa disembunyikan di Tampilan), Laporan > Bulanan, dan Laporan akhir tahun menampilkan total online dibanding offline dan per platform. Ekspor Excel/CSV dan impor memuat kolom Platform.

Saldo dompet tidak disimpan, tetapi dihitung dari saldo awal + semua transaksi, jadi tidak bisa tidak sinkron.
Transfer tidak dihitung sebagai pemasukan atau pengeluaran; biaya admin transfer dihitung sebagai pengeluaran.

## Pengingat stok habis
Dari jarak antar pembelian sebuah barang (median, minimal 3 kali beli di hari berbeda, rata-rata jeda 2 sampai 120 hari), aplikasi memperkirakan kapan waktunya beli lagi. Barang yang sudah waktunya (atau sekitar 2 hari lagi) muncul di Perlu perhatian di Beranda dan di panel **Waktunya beli lagi** pada Daftar belanja, dengan tombol **Tambah ke daftar** (banyaknya mengikuti kebiasaan beli) atau **Jangan ingatkan**. Barang yang sudah ada di daftar belanja aktif tidak diingatkan lagi.

## Hapus struk sekaligus dan cek struk dobel
Di kartu struk (Daftar transaksi) ada **Hapus seluruh struk**: semua barangnya pindah ke Tempat sampah sekaligus. Saat menyimpan struk, aplikasi memperingatkan bila sudah ada struk dengan foto yang sama, atau toko, tanggal, dan total yang sama; centang "Ini struk yang berbeda, tetap simpan" bila memang berbeda.

## Perbandingan bulan ke bulan
Laporan > Bulanan > **Dibanding bulan lalu**: total pengeluaran dan kategori yang paling berubah (naik atau turun), beserta barang dan toko yang paling menjelaskan perubahannya. Untuk bulan berjalan, bulan lalu dibandingkan sampai tanggal yang sama supaya adil.

## Anggaran per toko atau barang
Di Anggaran, pilih **Batasi per** Kategori, Toko, atau Barang. Misalnya "Kopi susu maksimal Rp 300 ribu per bulan" atau "Toko Kopi Kenangan maksimal Rp 500 ribu". Anggaran toko dan barang menghitung semua pengeluaran bulan itu yang tercatat dengan toko atau barang tersebut, tampil di Beranda dan Perlu perhatian seperti anggaran kategori, dan ikut di ekspor Excel.

## Ringkasan mingguan
Kartu di Beranda (bisa disembunyikan di Pengaturan > Tampilan) dengan pilihan **Pekan lalu** atau **Pekan ini**: total pengeluaran dan perbandingannya dengan pekan sebelumnya (atau rentang yang sama), pemasukan, jumlah transaksi dan struk, tiga kategori terbesar, hari paling boros, hemat dari diskon, dan barang yang harganya naik 10% atau lebih dari biasanya.

## Grafik harga per barang
Laporan > Barang > Lihat perubahan harga: satu garis per toko dengan rentang 3 bulan, 6 bulan, 1 tahun, atau semua; belah ketupat hitam menandai pembelian saat diskon; garis putus-putus rata-rata; kartu termurah, rata-rata, termahal, dan harga terakhir.

## Batas pengeluaran harian
Di Anggaran, buka **Batas pengeluaran harian** dan isi jatah per hari (0 untuk mematikan). Beranda menampilkan kartu **Jatah hari ini** (terpakai, sisa, dan jumlah hari bulan ini yang melewati batas), memberi peringatan di Perlu perhatian saat sudah 80% atau lewat, dan setelah mencatat pengeluaran hari ini muncul sisa jatahnya. Kartu bisa disembunyikan di Pengaturan > Tampilan.

## Toko terdekat
Untuk toko yang sudah punya titik lokasi: di Toko dan tempat beli ada tombol **Toko terdekat dari saya** (daftar terurut jarak dengan tautan Rute). Di Catat transaksi (satu barang maupun struk) tombol **Pilih toko terdekat** langsung memilih toko tersimpan dalam 500 m dari posisi Anda. Browser meminta izin lokasi; posisi tidak disimpan.

## Belajar dari koreksi baca struk
Bila Anda memperbaiki hasil baca (mengganti Barang, mengubah nama, atau memilih toko yang benar) lalu menyimpan struk, aplikasi mengingat pasangan "tulisan di struk → pilihan Anda" dan memakainya di struk berikutnya. Contohnya "iii paHLAWAN SM Lan" langsung dipilihkan ke toko Pahlawan. Daftar koreksi dan tombol **Lupakan semua koreksi** ada di Pengaturan > Mesin baca struk. Koreksi tersimpan di data (maks. 300 per jenis).

## Struk jadi satu kartu
Di Daftar transaksi, barang dari satu struk (minimal 2) digabung jadi satu kartu: toko, tanggal, jam, total, jumlah barang, dan hemat diskon. Tekan "Lihat N barang" untuk membuka tiap barang beserta tombol Ubah, Salin, dan Hapus. Foto struk tampil sekali di kartu.

## Transaksi berulang
Menu ini (dulu Tagihan berulang) kini bisa untuk pengeluaran dan pemasukan (gaji dll.). Centang **Catat otomatis saat jatuh tempo** supaya transaksinya dicatat sendiri saat aplikasi dibuka pada atau setelah tanggal jatuh tempo; yang terlewat beberapa periode dicatat semua dengan tanggal aslinya (maksimal 12 periode sekali jalan). Tanpa centang, tetap pakai tombol Bayar atau Terima dan muncul sebagai pengingat di Beranda.

## Templat transaksi
Tekan **Salin** pada transaksi mana pun, lalu buka **Simpan sebagai templat** dan beri nama. Di Catat transaksi muncul **⚡ Templat**: **Catat sekarang** (tanggal hari ini, jam sekarang) atau **Isi form** bila ada yang mau diubah dulu.

## Toko paling hemat untuk daftar belanja
Di Daftar belanja, buka **Toko mana yang paling hemat?**: perkiraan total bila semua dibeli di satu toko, dari harga terakhir tiap barang di toko itu (barang yang belum pernah dibeli di sana dihitung dengan perkiraan di daftar). Hanya toko yang harganya diketahui untuk minimal separuh barang yang ditampilkan. Tombol **Pakai toko ini** memilihnya sebagai rencana toko.

## Peringatan harga
Saat mencatat satu struk atau menyusun daftar belanja, tiap barang dibandingkan dengan riwayat harganya (median 5 pembelian terakhir): kotak kuning bila lebih mahal 10% atau lebih, hijau bila lebih murah 10% atau lebih, plus info bila toko lain pernah menjual lebih murah. Di form satu barang, peringatan muncul sebagai catatan setelah disimpan (karena isian form tidak berubah langsung saat diketik).

## Tes mesin baca struk
Pengaturan > Mesin baca struk menampilkan mesin yang aktif sesuai urutan dan tombol **Tes koneksi** untuk tiap mesin (memakai struk contoh buatan aplikasi). Berguna untuk tahu mesin mana yang kena batas pemakaian atau salah kunci.

## Diskon di struk
Di tiap barang ada kolom **Harga normal** (isi bila barang itu diskon; harga satuan = yang dibayar). Untuk voucher atau diskon total, isi **Potongan seluruh struk**: dibagi ke tiap barang sebanding harganya dan tercatat sebagai diskon.

## Tambah barang lewat barcode
Di Pengaturan > Barang dan produk > Tambah barang baru, buka **Isi dari barcode**: foto barcode dengan kamera HP (atau unggah foto, atau ketik angkanya), lalu tekan **Baca dan isi form**. Kalau barcode sudah ada di data Anda, aplikasi memberi tahu dan menawarkan membuka barang itu. Kalau belum, nama, merek, ukuran, dan foto dicari di Open Food Facts (database terbuka, tanpa kunci) dan mengisi form untuk Anda periksa. Cakupan produk Indonesia belum lengkap; bila tidak ketemu, hanya barcode yang terisi.

## Baca struk otomatis
Di Catat transaksi, mode Struk: unggah foto struk lalu tekan **Baca isi struk dari foto ini**. Toko, tanggal, jam, dan daftar barang terisi sendiri; periksa lagi sebelum menyimpan. Total di struk dibandingkan dengan jumlah barang.

Mesin dipilih otomatis, dicoba berurutan (Claude, OpenAI/gateway, OpenRouter, Gemini, Tesseract). Bila satu gagal (kuota habis, gangguan, tidak ada barang terbaca), otomatis pindah ke berikutnya:
- **Claude** (lebih akurat, mengenali diskon): isi `[anthropic] api_key` di secrets. Foto dikirim ke Anthropic dan ada biaya per foto.
- **OpenAI atau gateway kompatibel OpenAI** (misal relink): isi `[openai]` di secrets dengan `api_key`, `base_url` (sampai `/v1`), dan `model` yang bisa membaca gambar. Bagian `[openrouter]` (kunci dari openrouter.ai) dan `[gemini]` (kunci dari Google AI Studio) diisi dengan cara yang sama, `base_url` dan `model` sudah ada bawaannya.
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

## Fitur tambahan (gelombang terbaru)

- **Cadangan otomatis**: Cadangan dan pulihkan > Cadangan > "Cadangan otomatis ke Excel". Pilih jadwal (harian sampai bulanan). Saat admin membuka aplikasi dan sudah waktunya, berkas Excel dan JSON disimpan di folder `cadangan/` repo data (10 terakhir). Ada juga tombol "Cadangkan sekarang".
- **Prakiraan akhir bulan**: kartu di Beranda berisi perkiraan total pengeluaran bulan ini (laju 14 hari terakhir + tagihan yang belum dicatat), batas harian yang aman, dan anggaran yang diperkirakan terlewati. Bisa disembunyikan di Pengaturan > Tampilan.
- **Patungan**: Catat transaksi > Pengeluaran > "Patungan". Bagianmu jadi pengeluaran, bagian tiap teman jadi piutang (uang keluar dompet = total tagihan). Pembagian rata atau diatur sendiri.
- **Pencarian**: menu Pencarian di Utama, mencari transaksi, barang, toko, daftar belanja, utang-piutang, dan tagihan (angka 3 digit ke atas dicocokkan ke jumlah).
- **Ubah banyak**: di Daftar transaksi, panel "Ubah banyak sekaligus" mengganti kategori, dompet, atau toko untuk transaksi terpilih atau seluruh hasil filter.
- **Impor mutasi rekening**: Ekspor dan impor > Mutasi rekening. Kolom dikenali otomatis (satu kolom bertanda atau debit/kredit), kategori diusulkan dari catatan yang pernah dipakai, transaksi yang tampaknya sudah ada tidak dicentang.
- **Mode gelap otomatis**: bila belum pernah memilih, tema mengikuti perangkat. Pilihan manual tetap diingat. Aplikasi sudah bisa dipasang ke layar utama (PWA) lewat menu peramban "Tambahkan ke layar utama".
- **Kunci PIN**: Pengaturan > Tampilan > Kunci PIN (4–12 angka, per akun, disimpan sebagai hash). Aplikasi terkunci saat dibuka ulang di perangkat yang masih tersambung, atau lewat tombol Kunci di menu samping. 5 salah = tunggu 60 detik.
- **Harga per satuan**: Laporan > Per satuan membandingkan harga per 100 g / 100 ml / buah antar barang sekategori dari "Ukuran / isi kemasan" (contoh: 85 g, 1 liter, 2 x 250 ml, isi 12).
- **Laporan akhir tahun**: Laporan > Akhir tahun. Ringkasan, grafik per bulan, kategori dan toko teratas, barang tersering, rekor, perbandingan dengan tahun lalu, dan unduhan HTML (cetak ke PDF dari peramban).

## Pencatatan lebih cepat dan pemeriksaan data

- **Tangkap cepat**: Catat transaksi > "⚡ Tangkap cepat". Ketik satu kalimat seperti `es jeruk 8rb 2`, `bensin 30rb`, `gaji 5jt`. Jenis, barang, kategori, dompet, dan toko ditebak dari kebiasaan; periksa lalu Simpan. Dengan banyaknya, nominal dihitung per satuan. Tanggal selalu hari ini.
- **Sering dicatat**: deretan tombol barang paling sering (90 hari terakhir) di atas form. Ketuk untuk mengisi barang, harga, kategori, dan toko yang biasa.
- **Pengeluaran rutin terlupa**: di Transaksi berulang. Mencari pengeluaran berjumlah mirip yang muncul tiap bulan (minimal 3 bulan), lalu bisa dijadwalkan, ditandai "mau dihentikan", atau diabaikan. Juga muncul di Perlu perhatian di Beranda.
- **Pemeriksa data**: Pengaturan > Pemeriksa data. Menemukan barang kosong padahal catatan menyebut barang, kategori beda dari barangnya, jumlah tak sama dengan banyaknya × harga satuan, dan rujukan ke barang/toko terhapus.

- **PPN di struk**: pada "Satu struk, banyak barang" ada kolom "PPN / pajak / biaya lain". Tombol "Hitung 11% dari barang" atau "Pakai selisih struk" (dari total hasil baca foto) mengisinya. PPN bisa dibagi ke harga tiap barang (total cocok dengan yang dibayar) atau dicatat sebagai satu baris PPN tersendiri.

## Foto struk untuk seluruh struk
Lupa unggah foto saat menyimpan struk? Di **Daftar transaksi**, buka kartu struk lalu pilih
"📷 Tambah foto struk" (atau "Ganti foto struk"). Satu foto dipasang ke semua barang dalam struk itu,
tidak perlu per barang. Tombol "Hapus foto" melepasnya dari semua barang.
