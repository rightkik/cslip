"use client"

import { useState, useTransition } from "react"
import type { Receipt } from "@/lib/supabase"
import { deleteReceipts } from "@/app/receipts/actions"

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
  const [selected, setSelected] = useState<Set<string>>(new Set())
  const [isPending, startTransition] = useTransition()
  const [showConfirm, setShowConfirm] = useState(false)

  const allSelected = receipts.length > 0 && selected.size === receipts.length

  function toggleAll() {
    if (allSelected) {
      setSelected(new Set())
    } else {
      setSelected(new Set(receipts.map((r) => r.id)))
    }
  }

  function toggle(id: string) {
    setSelected((prev) => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })
  }

  function handleDelete() {
    const ids = Array.from(selected)
    setShowConfirm(false)
    startTransition(async () => {
      const result = await deleteReceipts(ids)
      if (result.error) {
        alert(`Error: ${result.error}`)
      } else {
        setSelected(new Set())
      }
    })
  }

  if (receipts.length === 0) {
    return (
      <div className="bg-white rounded-xl border border-gray-200 p-12 text-center text-gray-400 text-sm">
        ไม่พบรายการที่ตรงกับเงื่อนไข
      </div>
    )
  }

  return (
    <div className="space-y-3">
      {/* Action bar */}
      {selected.size > 0 && (
        <div className="flex items-center gap-3 bg-red-50 border border-red-200 rounded-lg px-4 py-2.5">
          <span className="text-sm text-red-800">
            เลือก {selected.size} รายการ
          </span>
          <button
            onClick={() => setShowConfirm(true)}
            disabled={isPending}
            className="ml-auto text-sm font-medium text-white bg-red-600 hover:bg-red-700 disabled:opacity-50 rounded px-3 py-1.5 transition"
          >
            {isPending ? "กำลังลบ..." : "ลบรายการที่เลือก"}
          </button>
          <button
            onClick={() => setSelected(new Set())}
            disabled={isPending}
            className="text-sm text-red-600 hover:text-red-800 transition"
          >
            ยกเลิก
          </button>
        </div>
      )}

      {/* Confirm dialog */}
      {showConfirm && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
          <div className="bg-white rounded-xl shadow-xl p-6 max-w-sm w-full mx-4 space-y-4">
            <h3 className="text-lg font-semibold text-gray-900">ยืนยันการลบ</h3>
            <p className="text-sm text-gray-600">
              ต้องการลบ {selected.size} รายการที่เลือก?
              <br />
              <span className="text-red-600 font-medium">การลบจะไม่สามารถย้อนกลับได้</span>
            </p>
            <div className="flex gap-3 justify-end">
              <button
                onClick={() => setShowConfirm(false)}
                className="text-sm text-gray-600 hover:text-gray-800 border border-gray-300 rounded px-4 py-2 transition"
              >
                ยกเลิก
              </button>
              <button
                onClick={handleDelete}
                className="text-sm font-medium text-white bg-red-600 hover:bg-red-700 rounded px-4 py-2 transition"
              >
                ยืนยันลบ
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Table */}
      <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-100 bg-gray-50 text-xs text-gray-500 uppercase tracking-wide">
                <th className="px-3 py-3 text-center w-10">
                  <input
                    type="checkbox"
                    checked={allSelected}
                    onChange={toggleAll}
                    className="rounded border-gray-300 text-blue-600 focus:ring-blue-500 cursor-pointer"
                  />
                </th>
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
                <tr
                  key={r.id}
                  className={`hover:bg-gray-50 transition-colors ${selected.has(r.id) ? "bg-blue-50/50" : ""}`}
                >
                  <td className="px-3 py-3 text-center">
                    <input
                      type="checkbox"
                      checked={selected.has(r.id)}
                      onChange={() => toggle(r.id)}
                      className="rounded border-gray-300 text-blue-600 focus:ring-blue-500 cursor-pointer"
                    />
                  </td>
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
    </div>
  )
}
