"use client"

import type { Receipt } from "@/lib/supabase"

const HEADERS = [
  "issue_date", "vendor_name", "vendor_tax_id", "document_type", "document_number",
  "category", "subtotal", "vat_amount", "wht_amount", "total_amount", "currency",
  "drive_file_url", "created_at", "confirmed_at",
]

function toCsv(rows: Receipt[]): string {
  const escape = (v: unknown) => {
    const s = v == null ? "" : String(v)
    return s.includes(",") || s.includes('"') || s.includes("\n")
      ? `"${s.replace(/"/g, '""')}"`
      : s
  }
  const lines = [
    HEADERS.join(","),
    ...rows.map((r) => HEADERS.map((h) => escape(r[h as keyof Receipt])).join(",")),
  ]
  return lines.join("\r\n")
}

export function CsvExportButton({
  receipts,
  month,
  category,
}: {
  receipts: Receipt[]
  month?: string
  category?: string
}) {
  const handleExport = () => {
    const csv = toCsv(receipts)
    const blob = new Blob(["﻿" + csv], { type: "text/csv;charset=utf-8;" }) // BOM for Thai chars in Excel
    const url = URL.createObjectURL(blob)
    const a = document.createElement("a")
    const suffix = [month, category].filter(Boolean).join("_") || "all"
    a.href = url
    a.download = `receipts_${suffix}.csv`
    a.click()
    URL.revokeObjectURL(url)
  }

  return (
    <button
      onClick={handleExport}
      disabled={receipts.length === 0}
      className="flex items-center gap-2 rounded-lg border border-gray-300 bg-white px-4 py-2 text-sm text-gray-700 hover:bg-gray-50 shadow-sm transition disabled:opacity-40 disabled:cursor-not-allowed"
    >
      ⬇ Export CSV ({receipts.length})
    </button>
  )
}
