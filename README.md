# Paypers-DIY — ระบบจัดการใบเสร็จอัตโนมัติ (ใช้เอง)

ระบบบันทึกค่าใช้จ่ายส่วนตัว/ธุรกิจขนาดเล็ก แบบ self-hosted ที่เลียนแบบ core ของ Paypers.ai
โดยใช้ free tier ให้มากที่สุด เป้าหมายคือ **ต้นทุน ~0 บาท/เดือน** สำหรับการใช้งานคนเดียว

> **Workflow หลัก:** ส่งรูปใบเสร็จ → LINE Bot → AI อ่านข้อมูล → ยืนยัน → บันทึกลง DB + Google Drive + Google Sheets

---

## 1. เป้าหมายของโปรเจกต์ (Scope)

### ทำ (Phase 1 — MVP)
- รับรูป/ไฟล์ PDF ใบเสร็จผ่าน LINE Bot (private chat)
- ใช้ Gemini Vision อ่านและสกัดข้อมูล: ชื่อร้าน, เลขที่เอกสาร, วันที่, ยอดรวม, VAT, WHT, หมวดหมู่
- ตอบกลับใน LINE ให้ user ยืนยัน/แก้ไข (ผ่าน reply message — ฟรี)
- บันทึกลง Supabase (Postgres)
- อัปโหลดไฟล์ต้นฉบับขึ้น Google Drive (จัดโฟลเดอร์ตามเดือน)
- เพิ่มแถวข้อมูลลง Google Sheets

### ทำ (Phase 2)
- หน้า Dashboard web (สรุปค่าใช้จ่ายรายเดือน/รายปี)
- ออกเอกสาร PDF: ใบแทนใบเสร็จ, ใบสำคัญจ่าย
- รองรับหลายบริษัท (multi-company)

### ทำ (Phase 3 — optional)
- LINE Group support (หลายคนช่วยกันส่ง)
- ตรวจสอบเลขผู้เสียภาษีกับฐาน DBD
- **Email auto-scan (ดูหัวข้อ "เรื่องอีเมล" ด้านล่าง)**

### ไม่ทำ (ตอนนี้)
- ระบบ payment/subscription
- Mobile app native

---

## 2. เรื่องอีเมล auto-scan — คำแนะนำ

คุณบอกว่ายังไม่เห็นความสำคัญ — **ผมเห็นด้วยให้เลื่อนไปก่อน** ด้วยเหตุผล:

1. **ROI ต่ำตอนเริ่ม** — Gmail API setup (OAuth + watch/poll) ซับซ้อนกว่าที่คิด และต้องผ่าน Google verification ถ้าจะใช้ scope `gmail.readonly` แบบ production (มิฉะนั้นติด "unverified app" warning)
2. **ค่าใช้จ่ายซ่อน** — ถ้า poll บ่อย จะกิน AI token เยอะ (สแกนทุกเมลที่มี attachment)
3. **แก้ปัญหาได้ด้วยวิธีง่ายกว่า** — แทนที่จะ auto-scan ให้ใช้ **forwarding rule**: ตั้ง filter ใน Gmail ให้ forward เมลที่มีใบเสร็จ (เช่นจาก Vercel, Claude, ค่า subscription) ไปยัง email เฉพาะ แล้วค่อยทำ webhook รับทีหลัง — หรือง่ายสุดคือ user แชร์ภาพ/forward เข้า LINE เอง

**สรุป:** ข้ามไปก่อน ใส่ไว้ใน Phase 3 ถ้าวันหนึ่งใบเสร็จดิจิทัลเยอะจนเริ่มน่ารำคาญ ค่อยทำ

---

## 3. Tech Stack

| Layer | เทคโนโลยี | Free tier | หมายเหตุ |
|---|---|---|---|
| Bot ingress | LINE Messaging API | ✅ รับ + reply ฟรีไม่จำกัด | push จำกัด ~200-300/เดือน (เราเลี่ยง push) |
| Backend | FastAPI (Python 3.11+) | — | async, เหมาะกับ webhook |
| AI OCR | Gemini 2.0 Flash | ✅ 15 RPM, 1M token/วัน | vision + structured output |
| Database | Supabase (Postgres) | ✅ 500MB, 5GB bandwidth | + Storage เผื่อใช้ |
| Hosting | Render + UptimeRobot | ✅ free tier | Render รัน FastAPI; UptimeRobot ping /health ทุก 5 นาที ป้องกัน cold start + Supabase idle |
| File storage | Google Drive API | ✅ 15GB | เก็บต้นฉบับ |
| Spreadsheet | Google Sheets API | ✅ ไม่จำกัด (rate limit) | สำหรับบัญชี |
| PDF gen | WeasyPrint | ✅ open source | HTML → PDF |
| Dashboard (P2) | Next.js + Vercel | ✅ free | — |

### ทำไม Gemini ไม่ใช่ Claude (สำหรับ OCR)
- Gemini free tier ใหญ่กว่ามาก (1M token/วันฟรี) เหมาะกับงาน volume
- Vision + JSON structured output ดีพอสำหรับใบเสร็จ
- *(ถ้าต้องการความแม่นยำสูงสุดในอนาคต ค่อยสลับเป็น Claude Haiku/Sonnet ได้ — โครงสร้างโค้ดออกแบบให้สลับ provider ง่าย)*

---

## 4. สถาปัตยกรรม

```
┌──────────┐   webhook    ┌─────────────────┐
│ LINE App │ ───────────► │  FastAPI Backend │
│  (user)  │ ◄─────────── │   (Railway)      │
└──────────┘  reply(free) └────────┬─────────┘
                                    │
                  ┌─────────────────┼──────────────────┐
                  ▼                 ▼                  ▼
          ┌──────────────┐  ┌──────────────┐  ┌──────────────┐
          │ Gemini Flash │  │   Supabase   │  │ Google APIs  │
          │  (OCR/parse) │  │  (Postgres)  │  │ Drive+Sheets │
          └──────────────┘  └──────────────┘  └──────────────┘
```

### Flow รายละเอียด
1. User ส่งรูป/PDF เข้า LINE → LINE ส่ง webhook (มี `messageId` + `replyToken`)
2. Backend ดึง binary จาก LINE content API ด้วย `messageId`
3. ส่งให้ Gemini พร้อม prompt → ได้ JSON ข้อมูลใบเสร็จ
4. บันทึกสถานะ `pending` ลง Supabase, อัปโหลดไฟล์ขึ้น Drive
5. ตอบกลับ user (reply) แสดงข้อมูลที่อ่านได้ + ปุ่ม "ยืนยัน / แก้ไข" (Quick Reply / Flex Message)
6. เมื่อ user ยืนยัน → เปลี่ยนสถานะ `confirmed`, append แถวลง Google Sheets

---

## 5. โครงสร้างโฟลเดอร์

```
paypers-diy/
├── README.md                  ← ไฟล์นี้
├── docs/
│   ├── ARCHITECTURE.md         ← รายละเอียดสถาปัตยกรรม + data model
│   ├── SETUP.md                ← วิธี setup LINE / Gemini / Supabase / Google ทีละขั้น
│   ├── PROMPTS.md              ← prompt ทั้งหมดที่ใช้กับ AI (OCR + Claude Code)
│   ├── ROADMAP.md              ← แผนพัฒนาแบ่ง phase + checklist
│   └── DEV_LOG_GUIDE.md        ← กติกาการเขียน dev log
├── DEV_LOG.txt                 ← log การพัฒนา (ภาษาอังกฤษ) — Claude Code เขียนทุกครั้ง
├── CLAUDE.md                   ← instruction สำหรับ Claude Code
├── .env.example
├── requirements.txt
├── app/
│   ├── main.py                 ← FastAPI entry + LINE webhook
│   ├── config.py               ← env config
│   ├── line_client.py          ← รับ content / ส่ง reply
│   ├── ocr/
│   │   ├── base.py             ← interface (สลับ provider ได้)
│   │   └── gemini.py           ← Gemini implementation
│   ├── storage/
│   │   ├── drive.py            ← Google Drive upload
│   │   └── sheets.py           ← Google Sheets append
│   ├── db/
│   │   ├── models.py           ← Supabase/Postgres schema
│   │   └── repository.py       ← CRUD
│   └── documents/
│       └── voucher.py          ← (P2) PDF generation
└── tests/
```

---

## 6. ต้นทุนจริง (สรุป)

| รายการ | ต้นทุน/เดือน |
|---|---|
| LINE Bot (รับ + reply) | 0 บาท |
| Gemini Flash OCR (≤~200 ใบ/วัน) | 0 บาท |
| Render hosting | 0 บาท (free tier) |
| Supabase | 0 บาท |
| Google Drive/Sheets | 0 บาท |
| **รวม** | **0 บาท** |
| Domain (optional) | ~40 บาท/เดือน (500/ปี) |

ถ้าเกิน free tier AI: Gemini Flash ~$0.075/1M input token → 1,000 ใบ/เดือน ≈ 20-30 บาท

---

## 7. ขั้นตอนถัดไป

1. อ่าน `SETUP.md` ทำการสมัคร service ทั้งหมดให้พร้อมก่อน (เก็บ key ใส่ `.env`)
2. เปิด VS Code + Claude Code ในโฟลเดอร์นี้
3. สั่ง Claude Code ตาม prompt ใน `docs/PROMPTS.md` ทีละ task ตาม `docs/ROADMAP.md`
4. ให้ Claude Code เขียน `DEV_LOG.txt` ทุกครั้งหลังทำงานสำคัญ (กติกาใน `docs/DEV_LOG_GUIDE.md`)
