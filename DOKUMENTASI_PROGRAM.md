# DOKUMENTASI LENGKAP — SPK Draft Pick MLBB (AHP-SAW)

## 1. RINGKASAN PROYEK

Ini adalah aplikasi **Sistem Pendukung Keputusan (SPK)** untuk membantu pemain Mobile Legends: Bang Bang (MLBB) memilih hero terbaik saat fase **Draft Pick**. Metode yang digunakan adalah **AHP (Analytical Hierarchy Process)** untuk pembobotan kriteria dan **SAW (Simple Additive Weighting)** untuk perangkingan hero.

Aplikasi ini dibuat sebagai **proyek skripsi** menggunakan **Flask (Python)** dengan template Jinja2 dan vanilla JavaScript di sisi client.

**Repositori GitHub:** https://github.com/FirliSatriya/SPK-MLBB  
**Target deploy:** Vercel (serverless Python)  
**Lokal:** `python app.py` → http://localhost:5000

---

## 2. STRUKTUR DIREKTORI

```
skripsi-firli/
├── app.py                          # Flask app untuk development lokal
├── api/
│   └── index.py                    # Flask app untuk Vercel serverless (duplikat app.py dengan path adjustment)
├── vercel.json                     # Konfigurasi Vercel deployment
├── requirements.txt                # Dependencies: flask>=3.0.0
├── .gitignore
│
├── templates/                      # Jinja2 HTML templates
│   ├── base.html                   # Layout utama (navbar, theme toggle, footer)
│   ├── draft.html                  # Halaman simulasi draft pick (/)
│   ├── ahp.html                    # Halaman bobot AHP (/ahp)
│   ├── heroes.html                 # Halaman database hero (/heroes)
│   ├── login.html                  # Halaman login admin (/login)
│   └── admin.html                  # Halaman admin panel (/admin)
│
├── static/css/style.css            # CSS utama (dark/light mode, gaming theme)
├── public/static/css/style.css     # Duplikat CSS untuk Vercel CDN
│
├── AHP-SAW - DATA HERO.csv         # Data 132 hero (ID, nama, class, role)
├── AHP-SAW - DIFFICULTY.csv        # Skor sub-kriteria Difficulty per hero
├── AHP-SAW - CROWD CONTROL.csv     # Skor sub-kriteria Crowd Control per hero
├── AHP-SAW - MOBILITY.csv          # Skor sub-kriteria Mobility per hero
├── AHP-SAW - UTILITY.csv           # Skor sub-kriteria Utility per hero
├── AHP-SAW - DURABILITY.csv        # Skor sub-kriteria Durability per hero
├── AHP-SAW - OFFENSE.csv           # Skor sub-kriteria Offense per hero
├── AHP-SAW - DISINI.csv            # Matriks perbandingan berpasangan AHP (3 expert × 5 role)
├── AHP-SAW - BOBOT AHP.csv         # Data bobot AHP (referensi)
├── AHP-SAW - SKOR SAW .csv         # Data skor SAW (referensi)
│
├── calculate_saw.py                # Script Python standalone untuk perhitungan AHP-SAW (CLI)
├── hasil_saw.txt                   # Output hasil perhitungan SAW
├── hasil_saw_output.txt            # Output detail perhitungan
├── PRD_SPK_DraftPick_MLBB_AHP-SAW.md    # Product Requirements Document
└── PRD_SPK_DraftPick_MLBB_AHP-SAW.docx  # PRD versi Word
```

---

## 3. DATA CSV — FORMAT & KOLOM

### 3.1 `AHP-SAW - DATA HERO.csv`
Berisi daftar 132 hero. Kolom: `ID_HERO`, `NAMA_HERO`, `CLASS`, `ROLE`.  
- `ROLE` bisa multi-value dipisahkan koma, contoh: `"JUNGLING, EXP LANE"`.
- Semua role di-uppercase saat di-load: `JUNGLING`, `MID LANE`, `EXP LANE`, `ROAMING`, `GOLD LANE`.

### 3.2 File Kriteria (6 file CSV)
Setiap file berisi skor sub-kriteria per hero. Kolom: `ID_HERO` + 4 sub-kriteria. Contoh:

| File | Sub-Kriteria | Tipe |
|------|-------------|------|
| `DIFFICULTY.csv` | COMPLEXITY, TIMING PRECISSION, POSITIONING REQUIREMENT, DECISION COMPLEXITY | **Cost** (makin rendah makin bagus) |
| `CROWD CONTROL.csv` | TYPE STRENGHT, RELIABILITY, AREA COVERAGE, CHAIN / FREQUENCY | **Benefit** |
| `MOBILITY.csv` | DASH/BLINK, ROTATION SPEED, ESCAPE CAPABILITY, FLEXIBILITY | **Benefit** |
| `UTILITY.csv` | TEAM SUPPORT, ZONING / CONTROL, DISRUPTION, PROTECTION | **Benefit** |
| `DURABILITY.csv` | BASE TANKINESS, SUSTAIN/REGEN, DAMAGE MITIGATION, SURVIVAL TOOLS | **Benefit** |
| `OFFENSE.csv` | DAMAGE, KILL THREAT/BURST, POSITIONING REQUIREMENT, DECISION COMPLEXITY | **Benefit** |

**Cara menghitung skor kriteria utama:** rata-rata dari 4 sub-kriteria. Contoh: `Difficulty = (COMPLEXITY + TIMING + POSITIONING + DECISION) / 4`

### 3.3 `AHP-SAW - DISINI.csv`
Matriks perbandingan berpasangan AHP dari expert. Layout di CSV:
- **Kolom 0-7 (col_off=0):** 3 blok matriks 6×6 untuk JUNGLING (baris 2-7, 11-16, 20-25), MID LANE (29-34, 38-43, 47-52), GOLD LANE (56-61, 65-70, 74-79)
- **Kolom 9-16 (col_off=9):** 3 blok matriks 6×6 untuk EXP LANE (baris 2-7, 11-16, 20-25), ROAMING (29-34, 38-43, 47-52)
- Nilai bisa berupa angka atau fraksi (misal `1/3`, `1/5`).
- Matriks diagonal = 1, dan jika `m[i][j]` kosong tapi `m[j][i]` ada, maka `m[i][j] = 1/m[j][i]` (reciprocal).

---

## 4. LOGIKA AHP-SAW (di `app.py` dan `api/index.py`)

Kedua file ini memiliki kode yang **identik secara logika**. Perbedaan hanya pada path resolution.

### 4.1 Konstanta Penting
```python
CRITERIA_ORDER = ["Difficulty", "Crowd Control", "Mobility", "Utility", "Durability", "Offense"]
ATTR_TYPES = {"Difficulty": "cost", sisanya: "benefit"}
ROLES = ["JUNGLING", "MID LANE", "EXP LANE", "ROAMING", "GOLD LANE"]
```

### 4.2 Alur Data Loading (saat server start)
1. `load_heroes()` → baca `DATA HERO.csv` → list of dict `{id, name, class, roles[]}`
2. `load_scores()` → baca 6 file kriteria → dict `{hero_id: {criteria_name: avg_score}}`
3. `load_ahp_matrices()` → baca `DISINI.csv` → extract 15 blok matriks 6×6 → kelompokkan per role (masing-masing 3 matriks dari 3 expert)
4. Untuk setiap role: aggregate 3 matriks expert dengan **geometric mean** → hitung AHP → simpan di `AHP_RESULTS`
5. Attach skor ke setiap hero object

### 4.3 Fungsi `geo_mean(mats)`
Menggabungkan matriks dari beberapa expert menggunakan geometric mean:
```
aggregated[i][j] = (mat1[i][j] * mat2[i][j] * mat3[i][j]) ^ (1/3)
```

### 4.4 Fungsi `calc_ahp(mat)` — Menghitung Bobot AHP
1. Hitung column sum
2. Normalisasi matriks (bagi setiap elemen dengan column sum)
3. Bobot (w) = rata-rata setiap baris dari matriks ternormalisasi
4. Hitung λmax (lambda max) untuk uji konsistensi
5. CI = (λmax - n) / (n - 1), dimana n = 6 (jumlah kriteria)
6. CR = CI / RI, dimana RI = 1.24 (untuk n=6, tabel Saaty)
7. Konsisten jika CR ≤ 0.10

**Output:** `{weights: [6 bobot], lambda_max, ci, cr, consistent: bool}`

### 4.5 Fungsi `calc_saw(candidates, scores, weights, exclude_ids, scenario)`
1. Filter hero: buang yang ada di `exclude_ids`
2. Adjust bobot berdasarkan skenario:
   - **Default:** bobot AHP asli
   - **Safe:** Durability ×1.5, Utility ×1.5, Offense ×0.7, Mobility ×0.8
   - **Aggressive:** Offense ×1.5, Mobility ×1.5, Durability ×0.7, Utility ×0.8
3. Re-normalisasi bobot (agar total = 1)
4. Buat decision matrix dari skor 6 kriteria setiap hero
5. Normalisasi SAW:
   - **Benefit:** r[i][j] = value / max_value
   - **Cost:** r[i][j] = min_value / value
6. Hitung Vi = Σ (bobot[j] × r[i][j]) untuk setiap hero
7. Sort descending by Vi
8. Return list dengan `{id, name, class, roles, vi, rank, vi_pct, scores, ...}`

---

## 5. ROUTES (Flask)

| Route | Method | Fungsi | Auth |
|-------|--------|--------|------|
| `/` | GET | Halaman simulasi draft pick | - |
| `/ahp` | GET | Halaman bobot AHP per role | - |
| `/heroes` | GET | Halaman database 132 hero | - |
| `/login` | GET/POST | Login admin (username: `admin`, password: `admin123`) | - |
| `/logout` | GET | Logout admin, redirect ke /login | - |
| `/admin` | GET | Admin panel (CRUD hero, lihat AHP, statistik) | Session |
| `/admin/update_hero` | POST (JSON) | Update data hero (nama, class, 6 skor) | Session |
| `/api/recommend` | POST (JSON) | API rekomendasi: terima `{exclude[], scenario}`, return top-5 hero per role | - |
| `/health` | GET | Debug route: cek path, data loading status (hanya di `api/index.py`) | - |

### 5.1 API `/api/recommend` — Detail
**Request:** `POST /api/recommend`
```json
{
  "exclude": ["H001", "H005", "H010"],  // hero IDs yang sudah di-ban/pick
  "scenario": "default"                 // "default" | "safe" | "aggressive"
}
```
**Response:** top 5 hero per role
```json
{
  "JUNGLING": [{"id":"H042","name":"FANNY","vi":0.892,...}, ...],
  "MID LANE": [...],
  "EXP LANE": [...],
  "ROAMING": [...],
  "GOLD LANE": [...]
}
```

---

## 6. TEMPLATE HTML (Jinja2)

### 6.1 `base.html` — Layout Utama
- Navbar dengan link ke 4 halaman + tombol theme toggle (☀️/🌙)
- Active page detection via `request.path`
- Theme toggle: set `data-theme` attribute pada `<html>`, simpan di `localStorage('spk_theme')`
- CSS di-link langsung: `/static/css/style.css` (bukan `url_for`)
- Block: `{% block title %}`, `{% block content %}`, `{% block scripts %}`

### 6.2 `draft.html` — Simulasi Draft Pick
**Struktur 3 layar:**
1. **Start Screen** — pilih skenario (Default/Safe/Aggressive) + tombol MULAI DRAFT
2. **Draft Board** — timer 30s, grid hero, panel Tim Kita & Musuh, panel rekomendasi
3. **Finish Screen** — ringkasan hasil pick kedua tim

**Draft Sequence (20 langkah):**
```
Ban: Blue1, Red1, Blue2, Red2, Blue3, Red3
Pick: Blue1, Red1, Red2, Blue2, Blue3, Red3
Ban: Red4, Blue4, Red5, Blue5
Pick: Red4, Blue4, Blue5, Red5
```

**JavaScript di draft.html:**
- `ALL_HEROES` dan `ROLES` di-inject dari Flask via `{{ heroes | tojson }}`
- `DRAFT_SEQ[]` array 20 objek `{phase, team, label}` mendefinisikan urutan
- `confirmHero(id)` — handler klik hero di grid, push ke array ban/pick yang sesuai
- `renderDraft()` — render ulang semua UI (bans, picks, hero grid, role filter)
- `fetchRecs()` — fetch `POST /api/recommend` saat giliran pick tim kita, tampilkan top-5 per role
- `startTimer()` / `updateTimerUI()` — countdown 30 detik, warna berubah hijau→kuning→merah
- Hero yang sudah di-ban/pick di-exclude dari grid dan rekomendasi

### 6.3 `ahp.html` — Bobot AHP
- Tab per role (Jungling, Mid Lane, dst)
- Menampilkan: Lambda Max, CI, CR, Status Konsistensi
- Visualisasi bobot dengan colored progress bars
- Tabel bobot detail per kriteria

### 6.4 `heroes.html` — Database Hero
- Tabel 132 hero dengan 6 kolom skor kriteria
- Search bar (filter by nama)
- Role filter buttons
- Counter hero yang ditampilkan

### 6.5 `login.html` — Login Admin
- Form POST ke `/login`
- Credential hardcoded: `admin` / `admin123`
- Error message jika salah

### 6.6 `admin.html` — Admin Panel
- **3 Tab:** Data Hero, Bobot AHP, Statistik
- **Tab Data Hero:** Tabel hero + tombol Edit → modal popup
- **Modal Edit:** Form edit nama, class, dan 6 skor kriteria → `POST /admin/update_hero` (AJAX)
- **Tab Bobot AHP:** Ringkasan CR dan bobot per role
- **Tab Statistik:** Jumlah hero per role, jumlah kriteria, jumlah expert
- `role_counts` di-pass dari backend (bukan dihitung di template)

---

## 7. CSS (`static/css/style.css`)

**686 baris** dengan Dark Gaming Theme + Light Mode.

### 7.1 Design System
- **Font:** Inter (body) + Orbitron (heading/gaming)
- **Dark mode (default):** Background `#050a18`, cards glassmorphism `rgba(15,25,55,0.7)`
- **Light mode** (`[data-theme="light"]`): Background `#f0f2f5`, cards `rgba(255,255,255,0.85)`
- **Warna aksen:** Gold `#f0b429`, Blue `#4facfe`, Purple `#7c3aed`, Green `#10b981`, Red `#ef4444`
- **Gradient:** Gold, Blue, Purple untuk buttons/badges
- **Transition:** 0.3s pada background, color, border untuk smooth theme switch

### 7.2 Komponen CSS Utama
- `.navbar` — sticky top, backdrop blur, responsive (hide links di mobile)
- `.card` — glassmorphism panel dengan hover glow
- `.btn`, `.btn-primary`, `.btn-secondary` — button styles
- `.role-btn` — role selector tabs
- `.scenario-btn` — skenario selector (pill shape)
- `.results-table` — styled data table
- `.rank-badge` — gold/silver/bronze ranking
- `.weight-bars`, `.bar-fill` — colored progress bars untuk bobot AHP
- `.theme-toggle` — circular button untuk dark/light switch
- `.hero-picker`, `.hero-tag` — hero selection UI
- Responsive breakpoint: `@media (max-width: 900px)`

---

## 8. DEPLOYMENT — VERCEL

### 8.1 File Konfigurasi
**`vercel.json`:**
```json
{
  "rewrites": [
    { "source": "/(.*)", "destination": "/api/index" }
  ]
}
```
- Vercel otomatis serve file dari `public/` sebagai static
- Semua request lain di-rewrite ke `api/index.py` (Flask serverless function)

**`requirements.txt`:** `flask>=3.0.0`

### 8.2 Perbedaan `app.py` vs `api/index.py`
- `app.py` (lokal): `BASE_DIR = os.path.dirname(os.path.abspath(__file__))` — langsung di project root
- `api/index.py` (Vercel): `find_base_dir()` dengan 3 strategi fallback:
  1. `os.path.dirname(os.path.dirname(__file__))` — naik 1 level dari `api/`
  2. `os.getcwd()` — working directory
  3. `/var/task` — Vercel runtime path

### 8.3 Static Files di Vercel
- CSS disimpan di **2 lokasi**: `static/css/style.css` (untuk lokal) DAN `public/static/css/style.css` (untuk Vercel CDN)
- Template HTML me-link CSS via `/static/css/style.css` (path absolut, bukan `url_for`)
- Vercel serve dari `public/` → browser request `/static/css/style.css` → Vercel serve `public/static/css/style.css`

---

## 9. MASALAH YANG BELUM SELESAI

### 9.1 Deployment Vercel — Masih Error 404
**Status:** Terakhir masih muncul `404: NOT_FOUND` di Vercel. Kemungkinan penyebab:
- Path resolution di serverless function tidak menemukan CSV data files
- Serverless function crash saat load data (tidak ada error handling/logging)
- Perlu dicek via `/health` route untuk diagnosa

**Saran perbaikan:**
1. Buka `https://[domain].vercel.app/health` untuk cek status
2. Jika CSV tidak ditemukan, coba wrap data loading dalam try/except dan return error detail
3. Alternatif: embed data langsung di Python (bukan baca CSV) atau gunakan JSON
4. Cek Vercel deployment logs di dashboard Vercel

### 9.2 Data Persistence
- Perubahan data di Admin panel hanya berlaku selama server hidup (in-memory)
- Di Vercel serverless, setiap request bisa jadi cold start baru → perubahan admin hilang
- **Solusi masa depan:** gunakan database (Firebase, Supabase, atau SQLite)

### 9.3 Konsistensi AHP
- Beberapa role memiliki CR > 0.10 (tidak konsisten menurut standar Saaty)
- Ini sudah didokumentasikan di aplikasi untuk pembahasan skripsi

### 9.4 Duplikasi CSS
- CSS ada di 2 tempat (`static/` dan `public/static/`) — harus di-sync manual
- Idealnya gunakan build script atau symlink

### 9.5 Folder `web/` Kosong
- Sisa dari migrasi Next.js → Flask. Folder kosong tidak bisa dihapus karena dikunci OneDrive
- Hapus manual via File Explorer

---

## 10. CARA MENJALANKAN

### Lokal
```bash
cd skripsi-firli
pip install flask
python app.py
# Buka http://localhost:5000
```

### Deploy ke Vercel
```bash
# Pastikan repo sudah di-push ke GitHub
# Di Vercel dashboard: Import repo → auto deploy
# Atau: npm i -g vercel && vercel
```

---

## 11. CREDENTIAL
- **Admin login:** username `admin`, password `admin123`
- **Flask secret key:** `spk-mlbb-secret-key-2026` (hardcoded, bisa di-override via env var `SECRET_KEY`)
