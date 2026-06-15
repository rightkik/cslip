// Next.js 16: middleware.ts is deprecated → renamed to proxy.ts.
// Named export must be `proxy`. NextAuth v5 callback pattern gives us req.auth.
import { auth } from "@/auth"
import { NextResponse } from "next/server"

export const proxy = auth((req) => {
  const { pathname } = req.nextUrl

  if (!req.auth && pathname !== "/login") {
    return NextResponse.redirect(new URL("/login", req.url))
  }

  if (req.auth && pathname === "/login") {
    return NextResponse.redirect(new URL("/", req.url))
  }
})

export const config = {
  matcher: ["/((?!api/auth|_next/static|_next/image|favicon\\.ico).*)"],
}
