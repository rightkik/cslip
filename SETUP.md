# SETUP.md — เตรียม service ทั้งหมดก่อนเริ่ม dev

ทำตามลำดับนี้ เก็บค่าที่ได้ใส่ `.env` (ดู `.env.example`)

---

## 1. LINE Messaging API (ฟรี)

1. ไป https://developers.line.biz/console/ → สร้าง **Provider**
2. สร้าง **Messaging API channel** (ไม่ใช่ LINE Login)
3. ในแท็บ **Messaging API**:
   - คัดลอก **Channel access token** (long-lived) → `LINE_CHANNEL_ACCESS_TOKEN`
   - คัดลอก **Channel secret** (อยู่แท็บ Basic settings) → `LINE_CHANNEL_SECRET`
4. **Webhook URL** — ใส่ทีหลังเมื่อ deploy แล้ว (เช่น `https://xxx.up.railway.app/webhook`)
   - เปิด **Use webhook** = ON
5. ปิด **Auto-reply messages** และ **Greeting messages** ใน LINE Official Account Manager
   (ไม่งั้นมันจะตอบอัตโนมัติชนกับ bot)

> หมายเหตุค่าใช้จ่าย: การ **รับ** ข้อความและการ **reply** ฟรีไม่จำกัด
> สิ่งที่นับโควต้าคือ push/broadcast (แพ็ก Communication ฟรี ~200-300/เดือน) — เราจะเลี่ยง push

---

## 2. Gemini API (ฟรี)

1. ไป https://aistudio.google.com/apikey
2. กด **Create API key** → คัดลอก → `GEMINI_API_KEY`
3. Free tier: Gemini 2.0 Flash ~15 requests/min, 1M tokens/day — เพียงพอ
4. โมเดลที่ใช้: `gemini-2.0-flash` (vision + JSON output)

---

## 3. Supabase (ฟรี)

1. ไป https://supabase.com → สร้าง project ใหม่ (เลือก region สิงคโปร์ใกล้ไทยสุด)
2. **Project Settings → API**:
   - `Project URL` → `SUPABASE_URL`
   - `anon public` key → `SUPABASE_ANON_KEY`
   - `service_role` key → `SUPABASE_SERVICE_KEY` (สำหรับ backend, เก็บเป็นความลับ)
3. ไป **SQL Editor** → รัน schema จาก `docs/ARCHITECTURE.md` หัวข้อ 3
4. (Free tier: 500MB DB, 5GB bandwidth, 1GB storage)

---

## 4. Google Cloud — Drive + Sheets (ฟรี, ใช้ Service Account)

1. ไป https://console.cloud.google.com → สร้าง project
2. **APIs & Services → Library** → enable:
   - Google Drive API
   - Google Sheets API
3. **APIs & Services → Credentials → Create Credentials → Service Account**
   - ตั้งชื่อ เช่น `paypers-diy-sa`
   - สร้างเสร็จ → กดเข้า service account → แท็บ **Keys → Add Key → JSON** → ดาวน์โหลด
   - เก็บไฟล์ json ไว้ในเครื่อง (อย่า commit!) → path ใส่ `GOOGLE_SA_JSON_PATH`
   - หรือแปลงเป็น base64 ใส่ env `GOOGLE_SA_JSON_B64` (สะดวกกับ Railway)
4. **แชร์โฟลเดอร์ Drive ให้ service account:**
   - สร้างโฟลเดอร์ `Paypers-DIY` ใน Google Drive ส่วนตัว
   - แชร์โฟลเดอร์นั้นให้ email ของ service account (`xxx@xxx.iam.gserviceaccount.com`) สิทธิ์ Editor
   - คัดลอก folder ID จาก URL → `DRIVE_ROOT_FOLDER_ID`
5. **แชร์ Google Sheet ให้ service account:**
   - สร้าง Google Sheet ใหม่ → แชร์ให้ email service account สิทธิ์ Editor
   - คัดลอก sheet ID จาก URL → `SHEETS_SPREADSHEET_ID`

> Service Account สำคัญกว่า OAuth สำหรับ use case นี้ เพราะไม่ต้องผ่าน consent flow และไม่ติด
> "unverified app" — เหมาะกับ backend ที่เข้าถึง Drive/Sheets ของเจ้าของเอง

---

## 5. Render (ฟรี — hosting) + UptimeRobot (ฟรี — keep-alive)

> **หมายเหตุ:** Railway ยกเลิก free tier ปี 2023 แล้ว อย่าใช้ Cloud Run (background task ถูก kill หลัง HTTP response กลับ)

### 5A. Render
1. ไป https://render.com → login ด้วย GitHub
2. push repo ขึ้น GitHub ก่อน
3. **New → Web Service → Connect Repository**
4. ตั้งค่า:
   - **Runtime:** Python 3
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
   - **Instance Type:** Free
5. ตั้ง **Environment Variables** = ค่าทั้งหมดใน `.env`
6. เอา public domain ที่ได้ไปใส่เป็น LINE Webhook URL (`https://xxx.onrender.com/webhook`)

> Free tier มี cold start ~30-50s หลัง idle — แก้ด้วย UptimeRobot ด้านล่าง

### 5B. UptimeRobot (แก้ cold start + ป้องกัน Supabase idle)
1. ไป https://uptimerobot.com → สมัครบัญชีฟรี
2. **Add New Monitor:**
   - **Monitor Type:** HTTP(s)
   - **URL:** `https://xxx.onrender.com/health`
   - **Monitoring Interval:** 5 minutes
3. ผลที่ได้: process ไม่ sleep → webhook ตอบ 200 ทันเสมอ + Supabase ไม่ pause หลัง 7 วัน idle

---

## 6. ตรวจสอบก่อนเริ่ม dev — checklist

- [ ] `LINE_CHANNEL_ACCESS_TOKEN`, `LINE_CHANNEL_SECRET`
- [ ] `GEMINI_API_KEY`
- [ ] `SUPABASE_URL`, `SUPABASE_SERVICE_KEY`
- [ ] รัน SQL schema ใน Supabase แล้ว
- [ ] `GOOGLE_SA_JSON_PATH` (หรือ B64), service account สร้างแล้ว
- [ ] แชร์ Drive folder + Sheet ให้ service account แล้ว
- [ ] `DRIVE_ROOT_FOLDER_ID`, `SHEETS_SPREADSHEET_ID`
- [ ] เครื่องมี Python 3.11+, ngrok (สำหรับทดสอบ local webhook ก่อน deploy)
- [ ] Render service สร้างแล้ว + ได้ public URL แล้ว
- [ ] UptimeRobot monitor สร้างแล้ว ชี้ไปที่ `/health` ทุก 5 นาที

> **ทดสอบ local:** ใช้ `ngrok http 8000` เพื่อได้ HTTPS URL ชั่วคราว เอาไปใส่ LINE webhook ระหว่าง dev
