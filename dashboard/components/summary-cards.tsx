import type { Receipt } from "@/lib/supabase"

function fmt(n: number) {
  return new Intl.NumberFormat("th-TH", { minimumFractionDigits: 2, maximumFractionDigits: 2 }).format(n)
}

function toThaiMonth(iso: string) {
  const [year, mon] = iso.split("-")
  const d = new Date(Number(year), Number(mon) - 1, 1)
  return d.toLocaleDateString("th-TH", { month: "long", year: "numeric" })
}

export function SummaryCards({
  receipts,
  currentMonth,
}: {
  receipts: Receipt[]
  currentMonth?: string
}) {
  const total = receipts.reduce((s, r) => s + (r.total_amount ?? 0), 0)
  const vatTotal = receipts.reduce((s, r) => s + (r.vat_amount ?? 0), 0)
  const count = receipts.length

  const label = currentMonth ? toThaiMonth(currentMonth) : "รายการที่กรอง"

  return (
    <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
      <Card title={`ยอดรวม (${label})`} value={`฿${fmt(total)}`} sub="total_amount" />
      <Card title="VAT รวม" value={`฿${fmt(vatTotal)}`} sub="vat_amount" />
      <Card title="จำนวนรายการ" value={String(count)} sub="รายการ" />
    </div>
  )
}

function Card({ title, value, sub }: { title: string; value: string; sub: string }) {
  return (
    <div className="bg-white rounded-xl border border-gray-200 p-5 shadow-sm">
      <p className="text-xs text-gray-400 mb-1">{title}</p>
      <p className="text-2xl font-bold text-gray-900">{value}</p>
      <p className="text-xs text-gray-400 mt-1">{sub}</p>
    </div>
  )
}
