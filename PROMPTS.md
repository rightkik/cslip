# PROMPTS.md — Prompt ทั้งหมดที่ใช้

แบ่งเป็น 2 ส่วน:
- **ส่วน A** = prompt สำหรับสั่ง **Claude Code** ใน VS Code (ทำตามลำดับ task)
- **ส่วน B** = prompt สำหรับ **Gemini OCR** (ฝังในโค้ด)

---

# ส่วน A — Prompts สำหรับ Claude Code

> วิธีใช้: เปิด Claude Code ในโฟลเดอร์ root ของโปรเจกต์ (มันจะอ่าน `CLAUDE.md` เอง)
> แล้ว copy prompt ทีละ task มาวาง สั่งทีละขั้นตอน อย่าสั่งรวดเดียวทั้งหมด

### Task 0 — Bootstrap project
```
Read README.md, CLAUDE.md, and docs/ARCHITECTURE.md first.
Then scaffold the project: create requirements.txt, .env.example (matching SETUP.md),
app/config.py (load all env vars with pydantic-settings), and empty module files matching
the folder structure in README.md section 5. Add a minimal FastAPI app in app/main.py with
a GET /health endpoint. Don't implement business logic yet.
Update DEV_LOG.txt per docs/DEV_LOG_GUIDE.md.
```

### Task 1 — OCR interface + Gemini implementation
```
Implement app/ocr/base.py: define the ReceiptData pydantic model (see docs/ARCHITECTURE.md
section 2) and an abstract OCRProvider class with an async method
`extract(self, file_bytes: bytes, mime_type: str) -> ReceiptData`.
Then implement app/ocr/gemini.py using the google-genai SDK and model gemini-2.0-flash.
Use the OCR system prompt from docs/PROMPTS.md section B. Force JSON output and parse it
safely into ReceiptData. Add a unit test in tests/ that mocks the Gemini client.
Update DEV_LOG.txt.
```

### Task 2 — LINE webhook + client
```
Implement app/line_client.py (download message content by messageId, send reply messages,
build a confirmation Flex/Quick-Reply message). Then implement the LINE webhook in app/main.py:
verify x-line-signature, dedupe by messageId, ack with 200 fast, and process image/file
messages in a BackgroundTask. For now the background task should just download the content and
call the OCR provider, then reply with the extracted fields as text. Avoid push messages — use
reply only. Update DEV_LOG.txt.
```

### Task 3 — Database layer (Supabase)
```
Implement app/db/repository.py using supabase-py. Functions: insert_pending(receipt_data,
line_user_id, line_message_id) -> receipt_id; get_by_message_id; update_status; mark_synced;
list_by_user_and_month. Models in app/db/models.py if needed. Wire Task 2's background task to
save a 'pending' receipt after OCR. Add a test with a mocked client. Update DEV_LOG.txt.
```

### Task 4 — Google Drive upload
```
Implement app/storage/drive.py with a service account. Function ensure_folder_path(company,
year, month) -> folder_id (create folders if missing, cache lookups), and upload_file(file_bytes,
filename, mime_type, folder_id) -> (file_id, web_url). Wire it into the background task: after
saving pending receipt, upload the original file and store drive_file_id/url on the receipt.
Use the folder structure in ARCHITECTURE.md section 6. Update DEV_LOG.txt.
```

### Task 5 — Confirmation flow + Google Sheets sync
```
Add a confirmation step: when replying after OCR, include a Quick Reply with "ยืนยัน" and
"แก้ไข"/"ยกเลิก". Handle the postback/text: on confirm -> set status 'confirmed', append a row
to Google Sheets (implement app/storage/sheets.py per ARCHITECTURE.md section 7), set
sheet_row_synced=true. On cancel -> status 'rejected'. Update DEV_LOG.txt.
```

### Task 6 — Edit flow + Natural language quick-entry
```
Two features in one:
1. Edit flow: allow user to correct a field via LINE text while a receipt is pending,
   e.g. "ยอด 1250" or "หมวด ค่าอาหาร". Parse key-value corrections, update pending receipt,
   re-show summary for confirmation.
2. Natural language quick-entry: if the user sends a plain text message with NO image/file
   (e.g. "กาแฟ 65 บาท" or "ค่า Figma 590"), use Gemini text-only (not vision) to parse it
   into a ReceiptData and create a pending receipt directly. This is cheaper than vision calls
   and covers common daily expenses. Re-use the same OCRProvider interface.
Keep it simple and Thai-friendly. Update DEV_LOG.txt.
```

### Task 7 — Deploy prep
```
Add a Dockerfile (or railway.toml / Procfile) and a README "Deploy" section. Make config support
GOOGLE_SA_JSON_B64 (decode at startup) so no secret file is needed on Railway. Verify /health.
Update DEV_LOG.txt.
```

### Phase 2 tasks (later)
```
P2-A: PDF generation in app/documents/voucher.py (WeasyPrint) for ใบแทนใบเสร็จ and ใบสำคัญจ่าย
      from an HTML template. Upload generated PDF to Drive.
P2-B: Next.js dashboard (separate folder /dashboard) reading from Supabase: monthly/yearly totals,
      list, filter by category, CSV export. Deploy on Vercel.
P2-C: Multi-company support (companies table, pick active company in LINE).
```

---

# ส่วน B — Gemini OCR System Prompt (ฝังใน app/ocr/gemini.py)

ใช้ prompt นี้เป็น system instruction ส่งคู่กับรูป/PDF:

```
You are a Thai receipt and tax-document extraction engine. You will receive an image or PDF of
a receipt, tax invoice, bank transfer slip, handwritten cash bill, or an order screenshot
(Shopee/Lazada/TikTok). The document may be in Thai, English, or mixed.

Extract the following fields and return ONLY a single valid JSON object — no markdown, no code
fences, no commentary. If a field is unknown, use null.

{
  "vendor_name": string | null,        // merchant/seller name
  "vendor_tax_id": string | null,      // Thai 13-digit tax ID, digits only
  "document_type": "tax_invoice" | "receipt" | "slip" | "cash_bill" | "order_screenshot" | "other" | null,
  "document_number": string | null,    // invoice/receipt number
  "issue_date": string | null,         // ISO 8601 "YYYY-MM-DD". Convert Thai Buddhist year
                                        // (พ.ศ.) to Gregorian (ค.ศ.) by subtracting 543.
  "category": string | null,           // best-guess expense category in Thai, e.g.
                                        // "ค่าซอฟต์แวร์","ค่าอาหาร","ค่าเดินทาง","ค่าโฆษณา",
                                        // "ค่าอุปกรณ์สำนักงาน","ค่าบริการ","อื่นๆ"
  "subtotal": number | null,           // amount before VAT
  "vat_amount": number | null,         // VAT (usually 7% in Thailand). If only total shown and
                                        // VAT is "included", compute vat = total - total/1.07.
  "wht_amount": number | null,         // withholding tax (ภาษีหัก ณ ที่จ่าย) if present
  "total_amount": number | null,       // final amount paid
  "currency": string,                  // ISO code, default "THB"
  "raw_text": string | null,           // all readable text, for debugging
  "confidence": number                 // your confidence 0.0–1.0 in the extraction
}

Rules:
- Amounts are numbers without thousands separators or currency symbols (e.g. 1605.00 not "฿1,605").
- Thai date formats like "14 ม.ค. 2568" -> "2025-01-14".
- For bank slips, vendor_name = the recipient/payee; document_type = "slip".
- For order screenshots, vendor_name = the platform or shop; document_type = "order_screenshot".
- Never invent a tax ID. Only include vendor_tax_id if it clearly appears (13 digits).
- Output must be parseable by json.loads on the first try.
```

> **Note สำหรับ Claude Code:** ตั้งค่า `response_mime_type="application/json"` ใน Gemini config
> ถ้า SDK รองรับ เพื่อบังคับ JSON และลด error การ parse
