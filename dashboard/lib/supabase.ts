import { createClient } from "@supabase/supabase-js"

// Server-only — service-role key must NEVER be exposed to the browser.
// All queries run in Server Components or Route Handlers.
export function createServerClient() {
  return createClient(
    process.env.SUPABASE_URL!,
    process.env.SUPABASE_SERVICE_ROLE_KEY!
  )
}

export type Receipt = {
  id: string
  line_user_id: string
  status: string
  vendor_name: string | null
  vendor_tax_id: string | null
  document_type: string | null
  document_number: string | null
  issue_date: string | null
  category: string | null
  subtotal: number | null
  vat_amount: number | null
  wht_amount: number | null
  total_amount: number | null
  currency: string
  drive_file_url: string | null
  created_at: string
  confirmed_at: string | null
}
