import type { Metadata } from "next"
import { Geist } from "next/font/google"
import "./globals.css"

const geist = Geist({ subsets: ["latin"] })

export const metadata: Metadata = {
  title: "Cslip Dashboard",
  description: "Receipt manager dashboard",
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="th">
      <body className={`${geist.className} bg-gray-50 text-gray-900 antialiased min-h-screen`}>
        {children}
      </body>
    </html>
  )
}
