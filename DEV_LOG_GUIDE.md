# DEV_LOG_GUIDE.md — กติกาการเขียน Dev Log

`DEV_LOG.txt` เป็นไฟล์ log ภาษาอังกฤษ บันทึก "อะไรเกิดขึ้นและทำไม" ระหว่างพัฒนา
เพื่อให้กลับมาอ่านเข้าใจบริบทได้ทีหลัง (โดยคนหรือโดย AI)

## Claude Code ต้องเขียน log เมื่อ:
- เพิ่ม feature / module ใหม่
- แก้ bug สำคัญ
- เปลี่ยน config / dependency / architecture
- ตัดสินใจเชิงออกแบบ (design decision) ที่ไม่ชัดเจนในโค้ด

## รูปแบบ (append ต่อท้ายไฟล์เสมอ ห้ามลบของเก่า):

```
========================================
[YYYY-MM-DD HH:MM] TASK: <task id / short title>
----------------------------------------
WHAT: <what was done, 1-3 lines>
WHY:  <reason / decision rationale, if any>
FILES: <files created or changed>
NOTES: <gotchas, TODOs, follow-ups, things that broke>
========================================
```

## ตัวอย่าง:

```
========================================
[2026-06-13 14:30] TASK: Task 1 - OCR interface + Gemini
----------------------------------------
WHAT: Added ReceiptData pydantic model and OCRProvider abstract base.
      Implemented GeminiOCR using google-genai, model gemini-2.0-flash,
      response_mime_type=application/json.
WHY:  Kept provider behind an interface so we can swap to Claude later
      without touching webhook handlers (per CLAUDE.md rule 4).
FILES: app/ocr/base.py, app/ocr/gemini.py, tests/test_gemini.py
NOTES: Gemini sometimes wraps JSON in code fences despite mime_type;
       added a strip-fences fallback before json.loads. TODO: handle
       multi-page PDF (currently sends whole file, works <=20 pages).
========================================
```

## หลักการ
- ภาษาอังกฤษเสมอ (เพื่อให้ search/parse ง่าย และเป็นมาตรฐาน)
- กระชับ ตรงประเด็น เน้นข้อมูลที่ "อ่านแล้วเข้าใจว่าตอนนั้นคิดอะไร"
- ไม่ต้อง log ทุก keystroke — log เฉพาะสิ่งสำคัญ
- ถ้ามี error ที่แก้แล้ว ให้ระบุ root cause สั้น ๆ ใน NOTES
