# ARCHITECTURE.md

## 1. ภาพรวม component

| Component | หน้าที่ | ไฟล์ |
|---|---|---|
| LINE webhook handler | รับ event, validate signature, dedupe, queue งาน | `app/main.py` |
| LINE client | ดึง binary content, ส่ง reply / flex | `app/line_client.py` |
| OCR interface | สัญญา (contract) สำหรับ AI provider | `app/ocr/base.py` |
| Gemini OCR | implementation จริง | `app/ocr/gemini.py` |
| Drive storage | อัปโหลดไฟล์, สร้างโฟลเดอร์รายเดือน | `app/storage/drive.py` |
| Sheets storage | append แถวค่าใช้จ่าย | `app/storage/sheets.py` |
| Repository | CRUD กับ Supabase | `app/db/repository.py` |
| Config | โหลด env | `app/config.py` |

## 2. Receipt schema (Pydantic — อยู่ใน `app/ocr/base.py`)

```python
class ReceiptData(BaseModel):
    vendor_name: str | None          # ชื่อร้าน/ผู้ขาย
    vendor_tax_id: str | None        # เลขประจำตัวผู้เสียภาษี (13 หลัก)
    document_type: str | None        # "tax_invoice" | "receipt" | "slip" | "cash_bill" | "other"
    document_number: str | None      # เลขที่เอกสาร
    issue_date: date | None          # วันที่ออกเอกสาร (ISO)
    category: str | None             # หมวดหมู่ค่าใช้จ่าย (software, food, transport, ...)
    subtotal: Decimal | None         # ยอดก่อนภาษี
    vat_amount: Decimal | None       # ภาษีมูลค่าเพิ่ม
    wht_amount: Decimal | None       # ภาษีหัก ณ ที่จ่าย
    total_amount: Decimal | None     # ยอดสุทธิ
    currency: str = "THB"
    raw_text: str | None             # ข้อความดิบที่อ่านได้ (เผื่อ debug)
    confidence: float | None         # ความมั่นใจ 0-1 (ถ้า model ให้)
```

## 3. Database schema (Supabase / Postgres)

```sql
-- companies: รองรับ multi-company (Phase 2)
create table companies (
  id uuid primary key default gen_random_uuid(),
  name text not null,
  tax_id text,
  created_at timestamptz default now()
);

-- receipts: รายการใบเสร็จหลัก
create table receipts (
  id uuid primary key default gen_random_uuid(),
  company_id uuid references companies(id),
  line_user_id text not null,
  line_message_id text unique not null,   -- ใช้ dedupe
  status text not null default 'pending',  -- pending | confirmed | rejected
  vendor_name text,
  vendor_tax_id text,
  document_type text,
  document_number text,
  issue_date date,
  category text,
  subtotal numeric(14,2),
  vat_amount numeric(14,2),
  wht_amount numeric(14,2),
  total_amount numeric(14,2),
  currency text default 'THB',
  raw_text text,
  confidence real,
  drive_file_id text,        -- id ไฟล์ต้นฉบับใน Google Drive
  drive_file_url text,
  sheet_row_synced boolean default false,
  created_at timestamptz default now(),
  confirmed_at timestamptz
);

create index idx_receipts_user on receipts(line_user_id);
create index idx_receipts_status on receipts(status);
create index idx_receipts_date on receipts(issue_date);
```

## 4. State machine ของใบเสร็จ

```
[user ส่งรูป]
      │
      ▼
  pending ──(user กดยืนยัน)──► confirmed ──► sync to Sheets
      │
      └──(user กดยกเลิก / ส่งใหม่)──► rejected
```

## 5. การจัดการ async / background

- Webhook handler ต้องตอบ 200 เร็ว (LINE timeout ~1s แนะนำให้รีบ ack)
- ใช้ FastAPI `BackgroundTasks` (พอสำหรับ single-user) — ถ้าต้องการ scale ค่อยเปลี่ยนเป็น queue (เช่น Supabase + worker)
- **ลำดับงานที่ถูกต้อง** (reply token มีอายุ 30 วินาทีเท่านั้น — ต้อง reply ก่อน upload):

```
[webhook ack 200]
      │
      ▼  (BackgroundTask)
download content
      │
      ▼
OCR (Gemini)
      │
      ▼
insert pending → Supabase
      │
      ▼
reply ผลลัพธ์ให้ user ← ทำก่อน! token หมดใน 30s
      │
      ▼  (ยัง BackgroundTask ต่อ)
upload Drive → เก็บ drive_file_id ใน DB
      │
      ▼
(รอ user confirm → Sheets sync)
```

> **สำคัญ:** Drive upload และ Sheets sync ต้องอยู่ **หลัง** reply เสมอ มิฉะนั้น reply token หมดอายุก่อนและ user ไม่ได้รับผล OCR

## 6. Google Drive โครงสร้างโฟลเดอร์

```
Paypers-DIY/
└── {company_name}/
    └── {YYYY}/
        └── {MM}/
            └── {issue_date}_{vendor}_{doc_number}.{ext}
```
ถ้าไม่มีข้อมูล ใช้ fallback เช่น `unknown_vendor` หรือวันที่ที่ได้รับ

## 7. Google Sheets layout

| วันที่ | ID | ผู้ขาย | เลขผู้เสียภาษี | ประเภท | หมวดหมู่ | ยอดก่อนภาษี | VAT | WHT | ยอดสุทธิ | ลิงก์ไฟล์ |
|---|---|---|---|---|---|---|---|---|---|---|

หนึ่งชีตต่อบริษัท หรือใช้คอลัมน์ company แยก (เลือกใน Phase 2)

## 8. Error handling
- OCR fail → reply "อ่านไม่ออก ลองถ่ายใหม่ให้ชัดขึ้น" + log
- Drive/Sheets fail → ยังเก็บ DB ไว้, mark `sheet_row_synced=false`, retry ทีหลัง
- ทุก error สำคัญ → เขียน DEV_LOG ถ้าเป็น bug ที่แก้, เขียน runtime log เสมอ
