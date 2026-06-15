import { createServerClient, type Receipt } from "@/lib/supabase"
import { auth, signOut } from "@/auth"
import { ReceiptsTable } from "@/components/receipts-table"
import { SummaryCards } from "@/components/summary-cards"
import { CsvExportButton } from "@/components/csv-export-button"
import { FilterBar } from "@/components/filter-bar"

// Next.js 16: searchParams is async
type SearchParams = Promise<{ month?: string; category?: string }>

export default async function ReceiptsPage({ searchParams }: { searchParams: SearchParams }) {
  const session = await auth()
  const { month, category } = await searchParams

  const supabase = createServerClient()

  // Build query — admin (ADMIN_EMAILS) sees all confirmed receipts.
  // TODO (multi-user): add .eq("google_email", session.user.email) for non-admin users
  // and join a user mapping table (google_email → line_user_id).
  let query = supabase
    .from("receipts")
    .select("*")
    .eq("status", "confirmed")
    .order("issue_date", { ascending: false })
    .order("created_at", { ascending: false })

  if (month) {
    // month = "YYYY-MM"
    const [year, mon] = month.split("-")
    const start = `${year}-${mon}-01`
    const end = new Date(Number(year), Number(mon), 0).toISOString().slice(0, 10) // last day
    query = query.gte("issue_date", start).lte("issue_date", end)
  }

  if (category) {
    query = query.eq("category", category)
  }

  const { data: receipts, error } = await query

  if (error) {
    console.error("Supabase error:", error.message)
  }

  const rows = (receipts ?? []) as Receipt[]

  // Collect unique categories for filter dropdown
  const { data: catRows } = await supabase
    .from("receipts")
    .select("category")
    .eq("status", "confirmed")
    .not("category", "is", null)

  const categories = Array.from(new Set((catRows ?? []).map((r) => r.category as string))).sort()

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white border-b border-gray-200 px-6 py-4 flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-gray-900">Cslip</h1>
          <p className="text-xs text-gray-400">Receipt Dashboard</p>
        </div>
        <div className="flex items-center gap-3">
          <span className="text-sm text-gray-600">{session?.user?.email}</span>
          <form
            action={async () => {
              "use server"
              await signOut({ redirectTo: "/login" })
            }}
          >
            <button
              type="submit"
              className="text-sm text-gray-500 hover:text-gray-800 border border-gray-300 rounded px-3 py-1 transition"
            >
              Sign out
            </button>
          </form>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-6 py-8 space-y-6">
        <SummaryCards receipts={rows} currentMonth={month} />

        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
          <FilterBar categories={categories} currentMonth={month} currentCategory={category} />
          <CsvExportButton receipts={rows} month={month} category={category} />
        </div>

        <ReceiptsTable receipts={rows} />
      </main>
    </div>
  )
}
