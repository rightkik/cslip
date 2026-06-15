"use client"

import { useRouter, useSearchParams } from "next/navigation"
import { useCallback } from "react"

export function FilterBar({
  categories,
  currentMonth,
  currentCategory,
}: {
  categories: string[]
  currentMonth?: string
  currentCategory?: string
}) {
  const router = useRouter()
  const searchParams = useSearchParams()

  const updateParam = useCallback(
    (key: string, value: string) => {
      const params = new URLSearchParams(searchParams.toString())
      if (value) {
        params.set(key, value)
      } else {
        params.delete(key)
      }
      router.push(`/receipts?${params.toString()}`)
    },
    [router, searchParams]
  )

  // Build month options: current month ± 11 months
  const monthOptions: { value: string; label: string }[] = []
  const now = new Date()
  for (let i = 0; i < 24; i++) {
    const d = new Date(now.getFullYear(), now.getMonth() - i, 1)
    const value = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}`
    const label = d.toLocaleDateString("th-TH", { month: "long", year: "numeric" })
    monthOptions.push({ value, label })
  }

  return (
    <div className="flex flex-wrap gap-3">
      <select
        className="rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm text-gray-700 shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
        value={currentMonth ?? ""}
        onChange={(e) => updateParam("month", e.target.value)}
      >
        <option value="">ทุกเดือน</option>
        {monthOptions.map((m) => (
          <option key={m.value} value={m.value}>
            {m.label}
          </option>
        ))}
      </select>

      <select
        className="rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm text-gray-700 shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
        value={currentCategory ?? ""}
        onChange={(e) => updateParam("category", e.target.value)}
      >
        <option value="">ทุกหมวดหมู่</option>
        {categories.map((c) => (
          <option key={c} value={c}>
            {c}
          </option>
        ))}
      </select>

      {(currentMonth || currentCategory) && (
        <button
          className="rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm text-gray-500 hover:bg-gray-50 transition"
          onClick={() => router.push("/receipts")}
        >
          ล้างตัวกรอง
        </button>
      )}
    </div>
  )
}
