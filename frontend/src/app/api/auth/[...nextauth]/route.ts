import NextAuth, { NextAuthOptions, DefaultSession } from "next-auth";
import CredentialsProvider from "next-auth/providers/credentials";

declare module "next-auth" {
  interface Session {
    accessToken?: string;
    user: {
      id?: string;
      role?: string;
    } & DefaultSession["user"];
  }

  interface User {
    id?: string;
    email?: string;
    role?: string;
    access_token?: string;
  }
}

declare module "next-auth/jwt" {
  interface JWT {
    accessToken?: string;
    role?: string;
    id?: string;
  }
}

export const authOptions: NextAuthOptions = {
  providers: [
    CredentialsProvider({
      name: "Credentials",
      credentials: {
        email: { label: "Email", type: "text", placeholder: "ornek@email.com" },
        password: { label: "Şifre", type: "password" }
      },
      async authorize(credentials) {
        if (!credentials?.email || !credentials?.password) {
          return null;
        }

        try {
          const apiUrl = process.env.INTERNAL_API_URL || process.env.NEXT_PUBLIC_API_URL || "http://api:8000";
          const res = await fetch(`${apiUrl}/api/v1/auth/login`, {
            method: "POST",
            body: JSON.stringify({
              email: credentials.email,
              password: credentials.password
            }),
            headers: { "Content-Type": "application/json" }
          });

          const data = await res.json();
          if (res.ok && data?.access_token) {
            return {
              id: data.user.id,
              email: data.user.email,
              name: data.user.email.split("@")[0],
              role: data.user.role,
              access_token: data.access_token
            };
          }
        } catch (error) {
          console.error("Auth authorize error:", error);
        }

        return null;
      }
    })
  ],
  callbacks: {
    async jwt({ token, user }) {
      if (user) {
        token.accessToken = user.access_token;
        token.role = user.role;
        token.id = user.id;
      }
      return token;
    },
    async session({ session, token }) {
      if (session.user) {
        session.user.id = token.id as string;
        session.user.role = token.role as string;
      }
      session.accessToken = token.accessToken as string;
      return session;
    }
  },
  session: {
    strategy: "jwt",
    maxAge: 24 * 60 * 60
  },
  pages: {
    signIn: "/login"
  },
  secret: process.env.NEXTAUTH_SECRET || "tarimsal-hasar-analizi-nextauth-secret-key-2026"
};

const handler = NextAuth(authOptions);

export { handler as GET, handler as POST };
