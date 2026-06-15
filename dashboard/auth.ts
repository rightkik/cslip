import NextAuth from "next-auth"
import Google from "next-auth/providers/google"

const ADMIN_EMAILS = (process.env.ADMIN_EMAILS ?? "").split(",").map((e) => e.trim().toLowerCase())

export const { handlers, signIn, signOut, auth } = NextAuth({
  providers: [
    Google({
      clientId: process.env.GOOGLE_CLIENT_ID!,
      clientSecret: process.env.GOOGLE_CLIENT_SECRET!,
    }),
  ],
  callbacks: {
    async signIn({ user }) {
      // Allow only pre-approved emails. When multi-user is ready, remove this gate
      // and rely on per-user data filtering instead.
      if (!user.email) return false
      if (ADMIN_EMAILS.length > 0 && !ADMIN_EMAILS.includes(user.email.toLowerCase())) {
        return false
      }
      return true
    },
    async session({ session, token }) {
      if (token.email) session.user.email = token.email
      return session
    },
  },
  pages: {
    signIn: "/login",
    error: "/login",
  },
})
