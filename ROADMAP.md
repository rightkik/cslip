# ROADMAP.md — แผนพัฒนา

ทำตามลำดับ task ใน `docs/PROMPTS.md` ส่วน A. แต่ละ task = 1 prompt ส่ง Claude Code

## Phase 1 — MVP (เป้า: ส่งรูป → ได้ข้อมูล → บันทึกครบ 3 ที่)

- [x] Task 0 — Bootstrap (scaffold, config, /health)
- [x] Task 1 — OCR interface + Gemini
- [ ] Task 2 — LINE webhook + client (รับรูป, reply ข้อมูล)
- [ ] Task 3 — Supabase repository (บันทึก pending)
- [ ] Task 4 — Google Drive upload (เก็บต้นฉบับ)
- [ ] Task 5 — Confirm flow + Google Sheets sync
- [ ] Task 6 — Edit flow + Natural language quick-entry (แก้ field / พิมพ์ "กาแฟ 65 บาท" โดยไม่ต้องส่งรูป)
- [ ] Task 7 — Deploy prep (Render + UptimeRobot)

**เกณฑ์ผ่าน Phase 1:** ส่งรูปใบเสร็จเข้า LINE → bot ตอบข้อมูลที่อ่านได้ → กดยืนยัน →
ไฟล์ขึ้น Drive + แถวขึ้น Sheet + record ใน DB เป็น confirmed

## Phase 2 — เอกสาร + Dashboard

- [ ] P2-A — PDF: ใบแทนใบเสร็จ + ใบสำคัญจ่าย (WeasyPrint)
- [ ] P2-B — Dashboard web (Next.js + Vercel, อ่านจาก Supabase)
- [ ] P2-C — Multi-company

## Phase 3 — optional / future

- [ ] LINE Group support
- [ ] DBD tax-id verification (ตรวจชื่อบริษัทจากเลขผู้เสียภาษี)
- [ ] Email auto-scan (Gmail API) — ทำเมื่อปริมาณใบเสร็จดิจิทัลคุ้มค่าจริง
- [ ] สลับ/เพิ่ม AI provider (Claude) ผ่าน OCR interface ถ้าต้องการความแม่นยำสูงขึ้น

## หลักการพัฒนา
- ทำทีละ task ให้ผ่านแล้วค่อยไป task ถัดไป (อย่ารวบ)
- ทุก task จบด้วยการอัปเดต `DEV_LOG.txt`
- ทดสอบ local ด้วย ngrok ก่อน deploy
- ใช้ reply ก่อน push เสมอ (push ได้ถ้าจำเป็น เช่น token หมด)
- **reply ต้องเกิดก่อน Drive upload เสมอ** (LINE token หมดใน 30s)
