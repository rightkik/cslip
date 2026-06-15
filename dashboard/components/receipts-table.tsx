"use client"

import type { Receipt } from "@/lib/supabase"

const DOC_TYPE_LABEL: Record<string, string> = {
  tax_invoice: "ใบกำกับภาษี",
  receipt: "ใบเสร็จ",
  slip: "สลิป",
  cash_bill: "ใบเสร็จเงินสด",
  order_screenshot: "Order screenshot",
  other: "อื่นๆ",
}

function fmt(n: number | null) {
  if (n == null) return "-"
  return new Intl.NumberFormat("th-TH", { minimumFractionDigits: 2, maximumFractionDigits: 2 }).format(n)
}

export function ReceiptsTable({ receipts }: { receipts: Receipt[] }) {
  if (receipts.length === 0) {
    return (
      <div className="bg-white rounded-xl border border-gray-200 p-12 text-center text-gray-400 text-sm">
        ไม่พบรายการที่ตรงกับเงื่อนไข
      </div>
    )
  }

  return (
    <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-gray-100 bg-gray-50 text-xs text-gray-500 uppercase tracking-wide">
              <th className="px-4 py-3 text-left font-medium">วันที่</th>
              <th className="px-4 py-3 text-left font-medium">ผู้ขาย</th>
              <th className="px-4 py-3 text-left font-medium">หมวดหมู่</th>
              <th className="px-4 py-3 text-left font-medium">ประเภท</th>
              <th className="px-4 py-3 text-right font-medium">ก่อนภาษี</th>
              <th className="px-4 py-3 text-right font-medium">VAT</th>
              <th className="px-4 py-3 text-right font-medium">ยอดสุทธิ</th>
              <th className="px-4 py-3 text-center font-medium">ไฟล์</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-50">
            {receipts.map((r) => (
              <tr key={r.id} className="hover:bg-gray-50 transition-colors">
                <td className="px-4 py-3 text-gray-600 whitespace-nowrap">
                  {r.issue_date ?? "-"}
                </td>
                <td className="px-4 py-3 text-gray-900 font-medium max-w-[200px] truncate">
                  {r.vendor_name ?? "-"}
                </td>
                <td className="px-4 py-3">
                  {r.category ? (
                    <span className="inline-flex items-center rounded-full bg-blue-50 px-2 py-0.5 text-xs text-blue-700 border border-blue-100">
                      {r.category}
                    </span>
                  ) : (
                    <span className="text-gray-400">-</span>
                  )}
                </td>
                <td className="px-4 py-3 text-gray-500 text-xs">
                  {r.document_type ? (DOC_TYPE_LABEL[r.document_type] ?? r.document_type) : "-"}
                </td>
                <td className="px-4 py-3 text-right text-gray-700 tabular-nums">{fmt(r.subtotal)}</td>
                <td className="px-4 py-3 text-right text-gray-500 tabular-nums">{fmt(r.vat_amount)}</td>
                <td className="px-4 py-3 text-right font-semibold text-gray-900 tabular-nums">
                  {fmt(r.total_amount)}
                </td>
                <td className="px-4 py-3 text-center">
                  {r.drive_file_url ? (
                    <a
                      href={r.drive_file_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-blue-500 hover:text-blue-700 transition"
                      title="เปิดไฟล์ต้นฉบับ"
                    >
                      ↗
                    </a>
                  ) : (
                    <span className="text-gray-300">-</span>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
