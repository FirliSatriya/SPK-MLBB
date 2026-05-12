# PRODUCT REQUIREMENTS DOCUMENT (PRD)

## Sistem Pendukung Keputusan Pemilihan Hero pada Fase Draft Pick Mobile Legends Bang Bang
### Menggunakan Metode AHP-SAW

---

| Field | Detail |
|---|---|
| **Nama Mahasiswa** | Firli Satriya Putri |
| **NIM** | 434221060 |
| **Program Studi** | D-IV Teknik Informatika |
| **Institusi** | Universitas Airlangga, Surabaya |
| **Pembimbing** | Rachman Sinatriya Marjianto, B.Eng., M.Sc. |
| **Versi Dokumen** | 1.0 |
| **Tanggal** | Mei 2026 |
| **Status** | Draft |

---

## Daftar Isi

1. [Executive Summary](#1-executive-summary)
2. [Tujuan & Sasaran Produk](#2-tujuan--sasaran-produk)
3. [Pemangku Kepentingan (Stakeholders)](#3-pemangku-kepentingan-stakeholders)
4. [Ruang Lingkup Produk](#4-ruang-lingkup-produk)
5. [Pengguna & Use Case](#5-pengguna--use-case)
6. [Persyaratan Fungsional](#6-persyaratan-fungsional)
7. [Persyaratan Non-Fungsional](#7-persyaratan-non-fungsional)
8. [Arsitektur & Stack Teknologi](#8-arsitektur--stack-teknologi)
9. [Model Data](#9-model-data)
10. [Spesifikasi Kriteria & Subkriteria](#10-spesifikasi-kriteria--subkriteria)
11. [Spesifikasi Metode AHP](#11-spesifikasi-metode-ahp)
12. [Spesifikasi Metode SAW](#12-spesifikasi-metode-saw)
13. [Spesifikasi Antarmuka Pengguna](#13-spesifikasi-antarmuka-pengguna)
14. [Rencana Pengujian](#14-rencana-pengujian)
15. [Timeline Pengembangan](#15-timeline-pengembangan)
16. [Analisis Risiko](#16-analisis-risiko)
17. [Kriteria Penerimaan Produk](#17-kriteria-penerimaan-produk)
18. [Referensi](#18-referensi)

---

## 1. Executive Summary

Dokumen PRD ini mendefinisikan kebutuhan lengkap untuk pembangunan **Sistem Pendukung Keputusan (SPK) berbasis website** yang membantu pemain dan tim esports Mobile Legends Bang Bang (MLBB) dalam memilih hero secara terstruktur dan objektif pada fase *draft pick*.

Sistem mengintegrasikan dua metode *Multi-Criteria Decision Making* (MCDM):
- **AHP (Analytical Hierarchy Process)** — untuk pembobotan kriteria
- **SAW (Simple Additive Weighting)** — untuk perangkingan alternatif hero

Sistem dikembangkan menggunakan **Python** dan **Flask** sebagai backend, **MySQL** sebagai database, dan antarmuka web berbasis **HTML/CSS/JavaScript**.

| Aspek | Detail |
|---|---|
| **Nama Produk** | SPK Draft Pick MLBB — AHP-SAW |
| **Tipe Aplikasi** | Web Application (berbasis browser) |
| **Target Pengguna** | Pemain MLBB, tim esports, dan pelatih |
| **Metode Inti** | Analytical Hierarchy Process (AHP) + Simple Additive Weighting (SAW) |
| **Ruang Lingkup Hero** | 131 hero Mobile Legends Bang Bang |
| **Kriteria Utama** | Difficulty, Crowd Control, Mobility, Utility, Durability, Offense |
| **Role/Lane** | Jungling, Midlane, Exp Lane, Roamer, Gold Lane |
| **Teknologi Backend** | Python, Flask, MySQL |
| **Teknologi Frontend** | HTML, CSS, JavaScript |
| **Tools Pendukung** | Pandas, NumPy, Draw.io, Figma, Laragon |

---

## 2. Tujuan & Sasaran Produk

### 2.1 Tujuan Utama

Membangun SPK berbasis website yang mampu memberikan **rekomendasi hero secara cepat, transparan, dan konsisten** pada fase *draft pick* MLBB berdasarkan kriteria yang telah dinilai oleh expert.

### 2.2 Sasaran Bisnis & Akademis

| Sasaran | Indikator Keberhasilan |
|---|---|
| Rekomendasi hero berbasis kriteria terstruktur | Sistem menghasilkan ranking hero dengan nilai preferensi (Vi) yang dapat ditampilkan ke pengguna |
| Validasi metode AHP-SAW | CR ≤ 0.10 untuk seluruh matriks perbandingan berpasangan per role/lane |
| Kecepatan rekomendasi pada draft pick | Output ranking tersedia dalam < 3 detik setelah input dikirim |
| Transparansi rekomendasi | Sistem menampilkan skor per kriteria utama untuk setiap hero rekomendasi |
| Akurasi filter kondisi draft | Hero yang di-ban atau di-pick musuh tidak muncul dalam rekomendasi |
| Kemudahan penggunaan | Pengguna tanpa latar teknis dapat menggunakan sistem tanpa pelatihan khusus |

### 2.3 Pernyataan Masalah

Pada praktiknya, proses pemilihan hero pada fase *draft pick* MLBB sering dilakukan berdasarkan **intuisi, kebiasaan bermain, atau mengikuti meta** tanpa evaluasi konsisten terhadap kriteria yang relevan. Kondisi ini berisiko menghasilkan komposisi tim yang kurang optimal, terutama pada pertandingan kompetitif yang menuntut keputusan cepat dan tepat.

SPK ini hadir untuk menjawab kesenjangan tersebut dengan menyediakan mekanisme rekomendasi berbasis data dan metode MCDM yang terukur.

---

## 3. Pemangku Kepentingan (Stakeholders)

| Peran | Pihak | Tanggung Jawab / Kepentingan |
|---|---|---|
| **Peneliti / Developer** | Firli Satriya Putri (Mahasiswa) | Merancang, membangun, menguji, dan mendokumentasikan sistem |
| **Dosen Pembimbing** | Rachman Sinatriya Marjianto, B.Eng., M.Sc. | Memberikan arahan teknis dan akademis, mengesahkan dokumen |
| **Expert / Narasumber Data** | Coach & Player UKM UNAIR Esport | Memberikan penilaian AHP dan rating hero (data primer) |
| **Pengguna Akhir** | Pemain MLBB, tim esports, pelatih | Menggunakan sistem untuk mendapatkan rekomendasi hero saat draft pick |
| **Admin Sistem** | Developer / Pengelola | Mengelola data master, mengupdate rating hero, menjalankan proses AHP-SAW |

---

## 4. Ruang Lingkup Produk

### 4.1 Dalam Cakupan (In Scope)

| Komponen | Detail |
|---|---|
| **Data Hero** | 131 hero MLBB beserta class dan role/lane |
| **Kriteria Penilaian** | 6 kriteria utama: Difficulty, Crowd Control, Mobility, Utility, Durability, Offense |
| **Subkriteria** | 24 subkriteria (4 per kriteria utama) sebagai indikator rinci penilaian |
| **Metode Pembobotan** | AHP per role/lane (Jungling, Midlane, Exp Lane, Roamer, Gold Lane) |
| **Metode Perangkingan** | SAW dengan normalisasi benefit/cost |
| **Fitur Draft Pick** | Input hero ban, input hero pick musuh, pemilihan role/lane, output ranking hero |
| **Output Sistem** | Ranking hero + nilai preferensi Vi + ringkasan skor 6 kriteria utama |
| **Skenario Rekomendasi** | Default, Prioritas Aman (Durability+Utility), Prioritas Agresif (Offense+Mobility) |
| **Panel Admin** | Kelola data hero, kriteria, input AHP, input rating subkriteria, uji konsistensi |
| **Uji Konsistensi AHP** | Perhitungan CI dan CR per role/lane dengan threshold CR ≤ 0.10 |

### 4.2 Di Luar Cakupan (Out of Scope)

| Komponen | Alasan Ekslusi |
|---|---|
| **Prediksi kemenangan pertandingan** | Di luar scope penelitian, memerlukan data match history yang kompleks |
| **Rekomendasi item build** | Bukan bagian dari fase draft pick |
| **Strategi in-game / post-game** | Sistem fokus pada fase pra-pertandingan saja |
| **Game selain Mobile Legends** | Dataset dan kriteria dirancang khusus untuk MLBB |
| **Fitur real-time multiplayer** | Tidak diperlukan dalam konteks penelitian ini |
| **Integrasi API resmi Moonton** | Keterbatasan akses data resmi; data diperoleh via expert judgement |

---

## 5. Pengguna & Use Case

### 5.1 Tipe Pengguna

| Tipe | Deskripsi | Kapabilitas Utama |
|---|---|---|
| **Admin** | Developer atau pengelola sistem yang bertanggung jawab atas data dan perhitungan | Login, kelola hero, input AHP, input rating, jalankan perhitungan, lihat hasil |
| **Pengguna (User)** | Pemain, pelatih, atau anggota tim esports yang menggunakan sistem saat draft pick | Input ban/pick, pilih role/lane, lihat rekomendasi |

### 5.2 Use Case Utama

#### UC-01: Mendapatkan Rekomendasi Hero (Pengguna)

| Field | Detail |
|---|---|
| **Aktor** | Pengguna (Pemain / Pelatih) |
| **Prasyarat** | Sistem memiliki data hero, bobot AHP, dan rating SAW yang valid |
| **Alur Utama** | 1. Pengguna mengakses halaman rekomendasi<br>2. Input daftar hero yang di-ban<br>3. Input daftar hero yang di-pick musuh<br>4. Pilih role/lane yang dibutuhkan<br>5. Klik 'Dapatkan Rekomendasi'<br>6. Sistem memfilter hero tersedia dan menghitung SAW<br>7. Sistem menampilkan ranking hero + nilai Vi + skor per kriteria |
| **Alternatif Alur** | Jika semua hero untuk role/lane tersebut sudah di-ban/pick, sistem menampilkan pesan "Tidak ada hero tersedia" |
| **Output** | Daftar ranking hero (Top-N) dengan nilai preferensi Vi dan ringkasan skor 6 kriteria |

#### UC-02: Manajemen Data Hero (Admin)

| Field | Detail |
|---|---|
| **Aktor** | Admin |
| **Prasyarat** | Admin telah login ke sistem |
| **Alur Utama** | 1. Admin login ke sistem<br>2. Navigasi ke menu 'Data Hero'<br>3. Tambah / edit / hapus data hero (nama, class, role/lane)<br>4. Sistem menyimpan perubahan ke database |
| **Validasi** | Nama hero unik, class dan role/lane harus sesuai daftar yang valid |
| **Output** | Data hero tersimpan dan tersedia sebagai alternatif dalam perhitungan SAW |

#### UC-03: Input & Perhitungan AHP (Admin)

| Field | Detail |
|---|---|
| **Aktor** | Admin |
| **Prasyarat** | Data kriteria telah tersedia dalam sistem |
| **Alur Utama** | 1. Admin navigasi ke menu 'Perhitungan AHP'<br>2. Pilih role/lane yang akan dihitung<br>3. Input nilai perbandingan berpasangan (skala Saaty 1–9) antar 6 kriteria<br>4. Sistem menghitung bobot prioritas dan uji konsistensi (CI, CR)<br>5. Jika CR ≤ 0.10, bobot disimpan; jika CR > 0.10, admin diminta revisi |
| **Output** | Bobot kriteria per role/lane + nilai CI dan CR |

#### UC-04: Input Rating Hero (Admin)

| Field | Detail |
|---|---|
| **Aktor** | Admin |
| **Prasyarat** | Data hero dan subkriteria telah tersedia |
| **Alur Utama** | 1. Admin navigasi ke menu 'Rating Hero'<br>2. Pilih hero yang akan dinilai<br>3. Input nilai rating (skala 1–5) untuk masing-masing 24 subkriteria<br>4. Sistem menyimpan rating dan menghitung skor 6 kriteria utama (rata-rata 4 subkriteria) |
| **Output** | Matriks keputusan 131 hero × 6 kriteria tersimpan di database |

---

## 6. Persyaratan Fungsional

### 6.1 Modul Rekomendasi Draft Pick

| ID | Fitur | Deskripsi | Prioritas | Status |
|---|---|---|---|---|
| FR-01 | Input Hero Ban | Sistem menerima input daftar hero yang di-ban dan mengecualikannya dari kandidat rekomendasi | Must Have | Planned |
| FR-02 | Input Hero Pick Musuh | Sistem menerima input hero yang sudah di-pick oleh tim lawan dan mengecualikannya dari kandidat | Must Have | Planned |
| FR-03 | Filter Role/Lane | Sistem menyaring hero berdasarkan role/lane yang dipilih pengguna (Jungling, Midlane, Exp Lane, Roamer, Gold Lane) | Must Have | Planned |
| FR-04 | Perhitungan SAW | Sistem menghitung nilai preferensi Vi setiap hero menggunakan bobot AHP sesuai role/lane yang dipilih dan nilai ternormalisasi 6 kriteria utama | Must Have | Planned |
| FR-05 | Output Ranking Hero | Sistem menampilkan daftar ranking hero (Top-N, default Top-10) diurutkan dari nilai Vi tertinggi | Must Have | Planned |
| FR-06 | Detail Skor Per Kriteria | Sistem menampilkan ringkasan skor 6 kriteria utama untuk setiap hero dalam daftar rekomendasi | Should Have | Planned |
| FR-07 | Skenario Rekomendasi | Sistem menyediakan 3 skenario: Default, Prioritas Aman (Durability+Utility), dan Prioritas Agresif (Offense+Mobility) | Should Have | Planned |
| FR-08 | Reset Input | Pengguna dapat mereset seluruh input draft (ban, pick, role) dan memulai ulang | Could Have | Planned |

### 6.2 Modul Admin — Data Master

| ID | Fitur | Deskripsi | Prioritas | Status |
|---|---|---|---|---|
| FR-09 | Login Admin | Admin dapat login ke sistem menggunakan username dan password yang valid | Must Have | Planned |
| FR-10 | CRUD Data Hero | Admin dapat menambah, melihat, mengedit, dan menghapus data hero (ID, nama, class, role/lane) | Must Have | Planned |
| FR-11 | CRUD Kriteria & Subkriteria | Admin dapat mengelola daftar 6 kriteria utama dan 24 subkriteria beserta tipe atributnya (benefit/cost) | Must Have | Planned |
| FR-12 | Input Rating Subkriteria | Admin dapat menginput atau memperbarui rating hero (skala 1–5) untuk setiap subkriteria | Must Have | Planned |
| FR-13 | Perhitungan Skor Kriteria Utama | Sistem menghitung skor 6 kriteria utama setiap hero dari rata-rata 4 subkriteria masing-masing secara otomatis | Must Have | Planned |

### 6.3 Modul Admin — AHP

| ID | Fitur | Deskripsi | Prioritas | Status |
|---|---|---|---|---|
| FR-14 | Input Matriks Perbandingan | Admin menginput nilai perbandingan berpasangan (skala Saaty 1–9) untuk 6 kriteria utama, per role/lane | Must Have | Planned |
| FR-15 | Perhitungan Bobot AHP | Sistem menghitung bobot prioritas (vektor bobot) untuk 6 kriteria utama menggunakan normalisasi kolom dan rata-rata baris | Must Have | Planned |
| FR-16 | Uji Konsistensi (CI & CR) | Sistem menghitung CI = (λmax − n)/(n − 1) dan CR = CI/RI. Jika CR > 0.10, sistem menampilkan peringatan dan meminta revisi | Must Have | Planned |
| FR-17 | Simpan Bobot Per Role/Lane | Bobot AHP tersimpan di database per role/lane dan digunakan pada perhitungan SAW saat rekomendasi | Must Have | Planned |
| FR-18 | Tampilan Hasil AHP | Admin dapat melihat tabel bobot, nilai λmax, CI, CR, dan status konsistensi per role/lane | Should Have | Planned |

### 6.4 Modul Validasi & Pengujian

| ID | Fitur | Deskripsi | Prioritas | Status |
|---|---|---|---|---|
| FR-19 | Validasi Perhitungan Manual | Admin dapat membandingkan hasil perhitungan sistem dengan perhitungan manual pada sampel hero tertentu | Should Have | Planned |
| FR-20 | Log Aktivitas Admin | Sistem mencatat log setiap perubahan data penting (tambah/edit hero, update rating, update AHP) | Could Have | Planned |

---

## 7. Persyaratan Non-Fungsional

### 7.1 Performa

| Persyaratan | Target |
|---|---|
| Waktu respons rekomendasi | ≤ 3 detik untuk 131 hero setelah input dikirim |
| Waktu load halaman utama | ≤ 2 detik pada koneksi stabil |
| Waktu perhitungan AHP | ≤ 5 detik per role/lane |
| Concurrent users | Minimal mendukung 10 pengguna simultan tanpa degradasi performa signifikan |

### 7.2 Keamanan

| Persyaratan | Detail |
|---|---|
| Autentikasi Admin | Session-based login dengan timeout otomatis setelah inaktif |
| Validasi Input | Semua input divalidasi server-side untuk mencegah SQL injection dan XSS |
| Hak Akses | Halaman admin hanya dapat diakses setelah login; pengguna umum tidak bisa mengakses panel admin |

### 7.3 Kegunaan (Usability)

| Persyaratan | Detail |
|---|---|
| Antarmuka Responsif | UI berfungsi optimal di desktop browser (Chrome, Firefox, Edge versi terbaru) |
| Kemudahan Input Draft | Pengguna dapat memilih hero ban/pick melalui dropdown atau search box dengan nama hero |
| Informasi Hasil | Hasil ranking ditampilkan dalam tabel yang mudah dibaca dengan label kriteria yang jelas |
| Pesan Error | Sistem menampilkan pesan error yang informatif saat input tidak valid |

### 7.4 Keandalan (Reliability)

| Persyaratan | Detail |
|---|---|
| Konsistensi Data | Setiap perubahan data tersimpan secara persisten di database MySQL |
| Validasi AHP | Sistem tidak menyimpan bobot jika CR > 0.10 tanpa konfirmasi admin |
| Penanganan Error | Sistem menangani exception dengan graceful error handling tanpa crash |

### 7.5 Kemampuan Pemeliharaan (Maintainability)

| Persyaratan | Detail |
|---|---|
| Modularitas Kode | Logika AHP dan SAW dipisahkan sebagai modul Python yang independen |
| Dokumentasi Kode | Fungsi utama didokumentasikan dengan docstring yang jelas |
| Kemudahan Update Data Hero | Admin dapat menambah hero baru tanpa perubahan kode (hanya melalui panel admin) |

---

## 8. Arsitektur & Stack Teknologi

### 8.1 Arsitektur Umum

Sistem menggunakan **arsitektur tiga lapis (three-tier architecture)**:

- **Presentation Layer** — Antarmuka web berbasis HTML/CSS/JavaScript yang dirender oleh Flask Jinja2 template
- **Application Layer** — Backend Python-Flask yang menangani routing, logika bisnis (AHP & SAW), dan validasi
- **Data Layer** — Database MySQL yang menyimpan data hero, kriteria, subkriteria, rating, dan bobot AHP

### 8.2 Stack Teknologi

| Layer | Teknologi | Kegunaan |
|---|---|---|
| Backend | Python 3.x | Bahasa pemrograman utama |
| Backend | Flask | Web framework untuk routing dan request handling |
| Backend | NumPy, Pandas | Komputasi matriks AHP dan pengolahan data SAW |
| Database | MySQL | Penyimpanan data hero, kriteria, rating, dan bobot |
| Database | SQLyog / Laragon | Tools GUI dan server lokal untuk MySQL |
| Frontend | HTML5, CSS3 | Struktur dan styling antarmuka pengguna |
| Frontend | JavaScript | Interaktivitas form dan validasi sisi klien |
| IDE | Visual Studio Code v1.75 | Lingkungan pengembangan utama |
| Desain | Figma | Prototyping dan desain antarmuka (UI/UX) |
| Diagram | Draw.io | Pembuatan use case diagram dan activity diagram |
| OS | Windows 11 | Sistem operasi pengembangan |

### 8.3 Spesifikasi Hardware Pengembangan

| Komponen | Spesifikasi |
|---|---|
| Laptop | ASUS VivoBook X1404VA |
| Processor | Intel Core i7-1355U (Gen 13) |
| RAM | 16 GB |
| Sistem Operasi | Windows 11 Home 64-bit |

---

## 9. Model Data

### 9.1 Entitas Utama Database

#### Tabel: `hero`

| Kolom | Tipe Data | Keterangan |
|---|---|---|
| `id_hero` | VARCHAR(10) | Primary Key, format: H001–H131 |
| `nama_hero` | VARCHAR(100) | Nama hero MLBB |
| `class` | VARCHAR(100) | Class hero (bisa multi-label, dipisah koma) |
| `role_lane` | VARCHAR(100) | Role/lane hero (bisa multi-label, dipisah koma) |
| `created_at` | TIMESTAMP | Waktu data dibuat |

#### Tabel: `kriteria`

| Kolom | Tipe Data | Keterangan |
|---|---|---|
| `id_kriteria` | INT | Primary Key, auto increment |
| `nama_kriteria` | VARCHAR(100) | Nama kriteria (misal: Difficulty) |
| `tipe_atribut` | ENUM('benefit','cost') | Tipe atribut untuk normalisasi SAW |
| `deskripsi` | TEXT | Deskripsi kriteria |

#### Tabel: `subkriteria`

| Kolom | Tipe Data | Keterangan |
|---|---|---|
| `id_subkriteria` | INT | Primary Key, auto increment |
| `id_kriteria` | INT | Foreign Key ke tabel kriteria |
| `nama_subkriteria` | VARCHAR(100) | Nama subkriteria |
| `definisi_operasional` | TEXT | Definisi operasional subkriteria |
| `sumber_data` | ENUM('objektif','subjektif') | Sumber penilaian |

#### Tabel: `rating_hero`

| Kolom | Tipe Data | Keterangan |
|---|---|---|
| `id` | INT | Primary Key, auto increment |
| `id_hero` | VARCHAR(10) | Foreign Key ke tabel hero |
| `id_subkriteria` | INT | Foreign Key ke tabel subkriteria |
| `nilai_rating` | TINYINT(1) | Nilai rating 1–5 berdasarkan expert judgement |
| `updated_at` | TIMESTAMP | Waktu update terakhir |

#### Tabel: `bobot_ahp`

| Kolom | Tipe Data | Keterangan |
|---|---|---|
| `id` | INT | Primary Key, auto increment |
| `role_lane` | VARCHAR(50) | Role/lane (Jungling, Midlane, Exp Lane, Roamer, Gold Lane) |
| `id_kriteria` | INT | Foreign Key ke tabel kriteria |
| `bobot` | DECIMAL(10,6) | Nilai bobot kriteria hasil AHP |
| `ci_value` | DECIMAL(10,6) | Nilai Consistency Index |
| `cr_value` | DECIMAL(10,6) | Nilai Consistency Ratio |
| `is_consistent` | BOOLEAN | TRUE jika CR ≤ 0.10 |
| `updated_at` | TIMESTAMP | Waktu update |

---

## 10. Spesifikasi Kriteria & Subkriteria

### 10.1 Daftar 6 Kriteria Utama

| Kriteria | Tipe Atribut (SAW) | Deskripsi |
|---|---|---|
| **Difficulty** | Cost | Tingkat kesulitan hero untuk dimainkan secara efektif (kompleksitas mekanik, timing, positioning, decision-making) |
| **Crowd Control** | Benefit | Kemampuan hero memberikan efek kontrol seperti stun, knock-up, slow, suppress kepada lawan |
| **Mobility** | Benefit | Kemampuan hero berpindah posisi, rotasi cepat, dash/blink, escape capability |
| **Utility** | Benefit | Kontribusi non-damage: heal/shield/buff/debuff, zoning, disruption, protection core |
| **Durability** | Benefit | Ketahanan hero: base tankiness, sustain/regen, damage mitigation, survival tools |
| **Offense** | Benefit | Kemampuan menghasilkan tekanan serangan: damage output, kill threat/burst, sustained DPS, objective pressure |

### 10.2 Daftar 24 Subkriteria

| Kriteria Utama | Subkriteria | Definisi Operasional | Sumber Data |
|---|---|---|---|
| **Difficulty (Cost)** | Complexity | Kompleksitas mekanik skill hero (kombinasi skill, kombo, kondisi eksekusi) | Subjektif |
| | Timing Precision | Ketepatan timing agar skill/kombo efektif | Subjektif |
| | Positioning Requirement | Ketergantungan pada posisi yang benar saat teamfight/laning | Subjektif |
| | Decision Complexity | Kompleksitas pengambilan keputusan saat menggunakan hero | Subjektif |
| **Crowd Control (Benefit)** | Type Strength | Kekuatan jenis CC berdasarkan efek (hard/soft) | Objektif |
| | Reliability | Konsistensi CC mengenai target | Subjektif |
| | Area Coverage | Luas area CC dan jumlah target yang dapat terkena | Objektif |
| | Frequency | Frekuensi penggunaan CC (cooldown & jumlah skill CC) | Objektif |
| **Mobility (Benefit)** | Dash/Blink | Ketersediaan dan kualitas dash/blink | Objektif |
| | Rotation Speed | Kecepatan berpindah lane untuk rotasi | Objektif |
| | Escape Capability | Kemampuan keluar dari situasi bahaya | Subjektif |
| | Flexibility | Fleksibilitas mobilitas untuk engage, disengage, reposition | Subjektif |
| **Utility (Benefit)** | Team Support | Kontribusi via heal, shield, buff, atau debuff | Subjektif |
| | Zoning/Control | Kemampuan mengontrol area dan membatasi lawan | Subjektif |
| | Disruption | Kemampuan mengganggu formasi atau eksekusi lawan | Subjektif |
| | Protection | Kemampuan melindungi core/teammate dalam pertarungan | Subjektif |
| **Durability (Benefit)** | Base Tankiness | Ketahanan dasar berdasarkan HP/DEF | Objektif |
| | Sustain/Regen | Kemampuan bertahan melalui pemulihan HP (lifesteal, regen) | Objektif |
| | Damage Mitigation | Kemampuan mengurangi damage masuk (shield, reduction, immunity) | Objektif |
| | Survival Tools | Alat bertahan hidup (escape, invulnerability, revive) | Objektif |
| **Offense (Benefit)** | Damage Output | Total output damage hero dalam permainan | Subjektif |
| | Kill Threat/Burst | Potensi kill cepat terhadap target | Subjektif |
| | Sustained DPS | Damage konsisten dalam durasi teamfight panjang | Subjektif |
| | Objective Pressure | Kemampuan menekan objektif (turret, turtle, lord) | Subjektif |

---

## 11. Spesifikasi Metode AHP

### 11.1 Skala Perbandingan Berpasangan (Skala Saaty 1–9)

| Nilai | Interpretasi |
|---|---|
| 1 | Sama penting (*equal importance*) |
| 3 | Sedikit / cukup lebih penting (*moderate importance*) |
| 5 | Lebih penting (*strong importance*) |
| 7 | Sangat lebih penting (*very strong importance*) |
| 9 | Mutlak / ekstrem lebih penting (*extreme importance*) |
| 2, 4, 6, 8 | Nilai tengah di antara dua nilai berdekatan (*intermediate values*) |
| 1/n | Kebalikan: kriteria j lebih penting dari kriteria i dengan nilai n |

### 11.2 Alur Perhitungan AHP

1. Susun matriks perbandingan berpasangan **A (6×6)** berdasarkan penilaian expert per role/lane
2. Hitung jumlah setiap kolom: **Sⱼ = Σᵢ aᵢⱼ**
3. Normalisasi matriks: **nᵢⱼ = aᵢⱼ / Sⱼ**
4. Hitung bobot prioritas: **wᵢ = (1/n) Σⱼ nᵢⱼ**
5. Hitung λmax: rata-rata dari **λᵢ = (AW)ᵢ / wᵢ**
6. Hitung **CI = (λmax − n) / (n − 1)**
7. Hitung **CR = CI / RI** (RI untuk n=6 adalah 1.24)
8. Jika **CR ≤ 0.10** → bobot valid dan disimpan; jika **CR > 0.10** → minta revisi penilaian

### 11.3 Tabel Random Index (RI)

| n (Ordo Matriks) | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 |
|---|---|---|---|---|---|---|---|---|---|---|
| **RI** | 0.00 | 0.00 | 0.58 | 0.90 | 1.12 | 1.24 | 1.32 | 1.41 | 1.45 | 1.49 |

### 11.4 Role/Lane dan Konteks Pembobotan

AHP dilakukan untuk setiap role/lane secara terpisah karena kebutuhan komposisi tim berbeda per posisi. Penilaian diperoleh dari coach dan player UKM UNAIR Esport sebagai expert.

| Role/Lane | Konteks Pembobotan |
|---|---|
| **Jungling** | Prioritas pada hero dengan mobility, offense, dan kemampuan ganking tinggi |
| **Midlane** | Prioritas pada offense, crowd control, dan damage area |
| **Exp Lane** | Prioritas pada durability, offense, dan kemampuan lane dominance |
| **Roamer** | Prioritas pada crowd control, utility, dan support tim |
| **Gold Lane** | Prioritas pada offense (DPS), durability, dan kemampuan scale late game |

---

## 12. Spesifikasi Metode SAW

### 12.1 Alur Perhitungan SAW

1. Susun matriks keputusan **X (131 hero × 6 kriteria)** dari rata-rata 4 subkriteria per kriteria
2. Normalisasi matriks:
   - **Benefit** → `rᵢⱼ = xᵢⱼ / max(xⱼ)`
   - **Cost** → `rᵢⱼ = min(xⱼ) / xᵢⱼ`
3. Hitung nilai preferensi: **Vᵢ = Σⱼ (wⱼ × rᵢⱼ)** menggunakan bobot AHP per role/lane
4. Urutkan hero dari Vᵢ tertinggi ke terendah → daftar ranking rekomendasi

### 12.2 Tipe Atribut Kriteria Utama

| Kriteria | Tipe Atribut | Penjelasan Normalisasi |
|---|---|---|
| **Difficulty** | Cost | Semakin kecil nilainya, semakin baik (hero mudah dimainkan) |
| **Crowd Control** | Benefit | Semakin besar nilainya, semakin baik |
| **Mobility** | Benefit | Semakin besar nilainya, semakin baik |
| **Utility** | Benefit | Semakin besar nilainya, semakin baik |
| **Durability** | Benefit | Semakin besar nilainya, semakin baik |
| **Offense** | Benefit | Semakin besar nilainya, semakin baik |

### 12.3 Skala Rating Subkriteria (1–5)

| Skor | Interpretasi |
|---|---|
| 1 | Sangat rendah / sangat tidak sesuai |
| 2 | Rendah / tidak sesuai |
| 3 | Sedang / cukup sesuai |
| 4 | Tinggi / sesuai |
| 5 | Sangat tinggi / sangat sesuai |

### 12.4 Skenario Output Rekomendasi

| Skenario | Fokus Kriteria | Keterangan |
|---|---|---|
| **Default** | Bobot AHP sesuai role/lane | Rekomendasi berdasarkan bobot standar hasil AHP per role/lane |
| **Prioritas Aman** | Durability + Utility lebih tinggi | Cocok saat tim butuh stabilitas, frontline, atau proteksi core |
| **Prioritas Agresif** | Offense + Mobility lebih tinggi | Cocok saat tim butuh snowball, pressure, atau tempo cepat |

---

## 13. Spesifikasi Antarmuka Pengguna

### 13.1 Halaman Utama / Rekomendasi (Pengguna)

| Elemen UI | Spesifikasi |
|---|---|
| **Header** | Nama sistem, logo (jika ada), navigasi utama |
| **Section: Hero Ban** | Dropdown/searchable select untuk memilih multiple hero yang di-ban |
| **Section: Hero Pick Musuh** | Dropdown/searchable select untuk memilih multiple hero yang di-pick musuh |
| **Section: Role/Lane** | Radio button atau dropdown untuk memilih 1 role/lane |
| **Section: Skenario** | Pilihan 3 skenario: Default, Prioritas Aman, Prioritas Agresif |
| **Tombol 'Rekomendasikan'** | Submit form dan trigger perhitungan SAW |
| **Tombol 'Reset'** | Mengosongkan semua input |
| **Tabel Hasil** | Kolom: Rank, Nama Hero, Class, Vi (%), skor per 6 kriteria |
| **Indikator Loading** | Spinner/loading state saat perhitungan berlangsung |
| **Pesan Kosong** | Teks informatif jika tidak ada hero yang tersedia untuk role/lane dipilih |

### 13.2 Panel Admin

| Halaman Admin | Fungsi Utama |
|---|---|
| **Login** | Form username/password dengan validasi |
| **Dashboard** | Ringkasan: jumlah hero, status bobot AHP per role/lane, status konsistensi |
| **Manajemen Hero** | Tabel hero dengan fitur tambah, edit, hapus; form validasi input |
| **Manajemen Kriteria** | Tabel kriteria & subkriteria; edit tipe atribut |
| **Input AHP** | Form grid perbandingan berpasangan 6×6 per role/lane; tombol hitung & simpan |
| **Hasil AHP** | Tabel bobot kriteria, λmax, CI, CR, status konsistensi per role/lane |
| **Rating Hero** | Form input/edit rating 1–5 untuk setiap hero × 24 subkriteria |
| **Matriks Keputusan** | Tampilan tabel 131 hero × 6 kriteria skor yang sudah dihitung |

---

## 14. Rencana Pengujian

### 14.1 Jenis Pengujian

| Jenis Pengujian | Deskripsi | Kriteria Keberhasilan |
|---|---|---|
| **Validasi Perhitungan AHP** | Bandingkan hasil bobot dan CR sistem dengan perhitungan manual (Excel/Python) pada sampel penilaian | Selisih bobot ≤ 0.001 dari perhitungan manual |
| **Validasi Perhitungan SAW** | Bandingkan nilai Vi sistem dengan perhitungan manual pada 5 sampel hero | Selisih Vi ≤ 0.001 dari perhitungan manual |
| **Uji Fungsional** | Verifikasi setiap use case berjalan sesuai alur yang didefinisikan | Seluruh use case berjalan tanpa error kritis |
| **Uji Filter Draft** | Pastikan hero yang di-ban/pick tidak muncul dalam rekomendasi | 0% hero terlarang muncul di output rekomendasi |
| **Uji Konsistensi AHP** | Verifikasi sistem menolak/memperingatkan jika CR > 0.10 | Sistem memunculkan peringatan saat CR > 0.10 |
| **Evaluasi Expert** | Coach/player menilai kewajaran bobot dan ranking rekomendasi | Minimal 70% hero rekomendasi Top-5 dianggap wajar oleh expert |

### 14.2 Skenario Uji Kritis

| ID Uji | Skenario | Expected Result |
|---|---|---|
| T-01 | Semua hero di role/lane di-ban + pick musuh | Sistem menampilkan pesan "Tidak ada hero tersedia" |
| T-02 | Input AHP dengan CR > 0.10 | Sistem menampilkan peringatan merah dan tidak menyimpan bobot |
| T-03 | Input AHP dengan CR ≤ 0.10 | Sistem menyimpan bobot dan menampilkan status "Konsisten" |
| T-04 | Rekomendasi dengan role Jungling, ban 5 hero | Output tidak mengandung 5 hero yang di-ban |
| T-05 | Hero multi-role/lane (misal: Alice — Exp Lane, Jungling, Mid Lane) | Hero muncul di semua role/lane yang valid |
| T-06 | Perhitungan SAW untuk 131 hero | Hasil muncul dalam ≤ 3 detik |

---

## 15. Timeline Pengembangan

| Fase | Periode | Deliverable |
|---|---|---|
| **Fase 1: Perencanaan & Pengumpulan Data** | Desember 2025 | Proposal skripsi, data kriteria & subkriteria, penilaian AHP dari expert |
| **Fase 2: Perancangan Sistem** | Januari 2026 | PRD, use case diagram, activity diagram, rancangan database, wireframe UI (Figma) |
| **Fase 3: Implementasi Backend** | Februari – Maret 2026 | Modul AHP (Python), modul SAW (Python), REST API Flask, database MySQL |
| **Fase 4: Implementasi Frontend & Admin** | Maret – April 2026 | Halaman rekomendasi, panel admin, form AHP & rating hero |
| **Fase 5: Pengujian & Validasi** | April 2026 | Laporan validasi AHP-SAW, uji fungsional, evaluasi bersama expert |
| **Fase 6: Finalisasi & Dokumentasi** | Mei 2026 | Laporan skripsi final, dokumentasi teknis, persiapan sidang |

---

## 16. Analisis Risiko

| Risiko | Dampak | Probabilitas | Mitigasi |
|---|---|---|---|
| CR > 0.10 pada penilaian AHP expert | Bobot tidak valid, rekomendasi tidak akurat | Sedang | Iterasi revisi penilaian bersama expert; panduan pengisian skala Saaty |
| Data rating hero tidak lengkap (131 hero × 24 subkriteria) | Sistem tidak dapat menghitung skor semua hero | Tinggi | Penjadwalan sesi pengisian rating bertahap; validasi kelengkapan sebelum sistem aktif |
| Performa lambat saat 131 hero dihitung | Pengalaman pengguna buruk | Rendah | Optimasi query SQL; caching hasil normalisasi yang jarang berubah |
| Update meta game MLBB (hero baru, patch balance) | Data rating menjadi tidak relevan | Sedang | Panel admin memudahkan update rating; dokumentasi prosedur update |
| Keterbatasan akses expert untuk validasi akhir | Evaluasi tidak dapat dilakukan | Rendah | Jadwalkan sesi evaluasi sejak awal; gunakan expert alternatif dari UKM Esport |

---

## 17. Kriteria Penerimaan Produk

Sistem dianggap memenuhi persyaratan dan siap untuk penilaian akademis apabila seluruh kriteria berikut terpenuhi:

| Kriteria | Standar Penerimaan |
|---|---|
| **Kelengkapan Fungsional** | Minimal 90% fitur *Must Have* pada Bab 6 berjalan tanpa bug kritis |
| **Konsistensi AHP** | Seluruh 5 role/lane memiliki bobot AHP dengan CR ≤ 0.10 |
| **Akurasi Perhitungan** | Selisih nilai Vi sistem vs. manual ≤ 0.001 untuk seluruh sampel uji |
| **Akurasi Filter Draft** | 0% hero yang di-ban atau di-pick musuh muncul dalam rekomendasi |
| **Kelengkapan Data** | Rating tersedia untuk seluruh 131 hero × 24 subkriteria |
| **Performa** | Waktu respons rekomendasi ≤ 3 detik pada hardware pengembangan |
| **Evaluasi Expert** | Minimal 70% hero Top-5 rekomendasi dianggap relevan oleh expert |
| **Dokumentasi** | PRD, use case, activity diagram, dan laporan pengujian tersedia |

---

## 18. Referensi

- Abidin, A. Z., Fairuzabadi, M., & Wibawa. (2024). *Decision support system for selecting Mobile Legends heroes in Epic tier using AHP-TOPSIS method.* JTH: Journal of Technology and Health. https://fahruddin.org/jth/article/view/95

- Azhari, A., et al. (2022). *Keputusan pemberian bantuan sosial program keluarga harapan menggunakan metode AHP dan SAW.* Matrik: Jurnal Manajemen, Teknik Informatika dan Rekayasa Komputer, 21(3), 639–652. https://doi.org/10.30812/matrik.v21i3.1806

- Chen, Z., et al. (2018). *The art of drafting: A team-oriented hero recommendation system for multiplayer online battle arena games.* Proceedings of ACM RecSys '18. https://arxiv.org/abs/1806.10130

- Goodridge, W. S. (2016). Sensitivity Analysis Using Simple Additive Weighting Method. *IJISA*, 8(5), 27–33. https://www.mecs-press.org/ijisa/ijisa-v8-n5/IJISA-V8-N5-4.pdf

- JISTECH. (2024). *Sistem Pendukung Keputusan Penerima Bantuan Usaha Mikro Menggunakan Kombinasi Metode AHP dan SAW.* https://jurnal.uinsu.ac.id/index.php/jistech/article/download/24159/10442

- Menold, N., & Bogner, K. (2016). *Design of Rating Scales in Questionnaires.* GESIS Survey Guidelines.

- Pan, et al. (2022). Review on AHP consistency and weight calculation methods.

- Sheng, et al. (2020). *Which Heroes to Pick? Learning to Draft in MOBA Games with Neural Networks and Tree Search.*

- Taherdoost, H. (2017). *Decision making using the analytic hierarchy process (AHP).* IJEMS. https://www.iaras.org/iaras/journals/ijems

- Taherdoost, H. (2023). *Analysis of simple additive weighting method (SAW).* JMSER, 6(1). https://doi.org/10.30564/jmser.v6i1.5400

- Vafaei, N., Ribeiro, R. A., & Camarinha-Matos, L. M. (2022). Assessing Normalization Techniques for Simple Additive Weighting Method. *Procedia Computer Science*, 199, 1229–1236.

- **Proposal Skripsi:** Firli Satriya Putri — *Sistem Pendukung Keputusan Pemilihan Hero pada Fase Draft Pick Game Mobile Legends Menggunakan Metode AHP-SAW* (2026).

- **Data AHP Expert Judgement:** Coach & Player UKM UNAIR Esport, Universitas Airlangga Surabaya.

---

*— Akhir Dokumen PRD —*

*Dokumen ini bersifat living document dan dapat diperbarui sesuai perkembangan penelitian.*
