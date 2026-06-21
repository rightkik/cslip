"use server"

import { auth } from "@/auth"
import { createServerClient } from "@/lib/supabase"
import { revalidatePath } from "next/cache"

const ADMIN_EMAILS = (process.env.ADMIN_EMAILS ?? "").split(",").map((e) => e.trim().toLowerCase())

export async function deleteReceipts(ids: string[]): Promise<{ error?: string }> {
  const session = await auth()
  if (!session?.user?.email || !ADMIN_EMAILS.includes(session.user.email.toLowerCase())) {
    return { error: "Unauthorized" }
  }

  if (ids.length === 0) return { error: "No items selected" }

  const supabase = createServerClient()
  const { error } = await supabase
    .from("receipts")
    .delete()
    .in("id", ids)

  if (error) {
    console.error("Delete error:", error.message)
    return { error: error.message }
  }

  revalidatePath("/receipts")
  return {}
}
