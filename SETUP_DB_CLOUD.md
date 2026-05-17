# Setup DB (Neon) + Image Storage (Cloudinary)

App tetap jalan tanpa konfigurasi ini (fallback ke CSV in-memory). Aktifkan kedua
service di bawah ini untuk dapat **persistensi CRUD** dan **upload gambar hero**.

---

## 1. Neon Postgres

1. Daftar di https://neon.tech (free tier, ~3GB).
2. Buat project baru. Region pilih yang dekat (Singapore).
3. Di dashboard project → **Connection Details** → copy **Connection string**
   (mode "Pooled connection" — direkomendasikan untuk Vercel).
   Format:
   ```
   postgresql://USER:PASSWORD@ep-xxx-pooler.region.aws.neon.tech/neondb?sslmode=require
   ```

## 2. Cloudinary

1. Daftar di https://cloudinary.com (free tier 25GB storage + 25GB bandwidth/bulan).
2. Setelah login → **Dashboard** → "API Environment variable":
   ```
   CLOUDINARY_URL=cloudinary://API_KEY:API_SECRET@CLOUD_NAME
   ```
   Copy nilai itu.

## 3. Wire-up local (.env)

```bash
cp .env.example .env
# edit .env dan paste DATABASE_URL + CLOUDINARY_URL
```

## 4. Install dependencies & migrate

```bash
pip install -r requirements.txt
python migrate.py     # Sekali jalan: CSV → Neon. Idempotent.
python app.py         # Jalankan server, http://localhost:5000
```

## 5. Wire-up Vercel

Vercel dashboard → project → **Settings → Environment Variables**, tambah:
- `DATABASE_URL` = (sama dengan local)
- `CLOUDINARY_URL` = (sama dengan local)
- `FLASK_SECRET_KEY` = random string

Lalu **redeploy**.

---

## How it works

- **Startup**: `app.py` cek `DATABASE_URL`. Kalau ada → load heroes/scores/AHP dari
  Neon. Kalau Neon kosong → seed otomatis dari CSV. Kalau env var tidak ada atau
  SQLAlchemy belum ter-install → fallback CSV-only (CRUD tetap jalan tapi
  hilang saat restart).
- **CRUD admin** (`/admin/create_hero`, `/admin/update_hero`, `/admin/delete_hero`,
  `/admin/update_ahp`) — semua mutate in-memory cache *dan* tulis ke Neon
  (UPSERT). Hilang Neon → CRUD tetap jalan tapi tidak persistent.
- **Image upload** (`/admin/upload_hero_image`) — multipart form, file di-upload
  ke Cloudinary di folder `mlbb-heroes/<HERO_ID>`, hasil URL disimpan di kolom
  `image_url` pada tabel `heroes`. Tampilan draft & data hero pakai URL ini
  kalau ada, fallback ke Fandom wiki URL kalau kosong.
- **Image delete** (`/admin/delete_hero_image`) — hapus dari Cloudinary + clear
  kolom DB.
- **Hero delete** — juga hapus gambar dari Cloudinary (best-effort).

## Tabel di Neon

```sql
heroes          (id, name, hero_class, roles JSONB, image_url, image_public_id, created_at, updated_at)
hero_scores     (id, hero_id FK, criterion, value, UNIQUE(hero_id, criterion))
ahp_matrices    (id, role, evaluator_idx, matrix JSONB, UNIQUE(role, evaluator_idx))
```
