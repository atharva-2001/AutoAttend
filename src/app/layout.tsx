import type { Metadata } from "next";
import { Work_Sans, Roboto_Mono } from "next/font/google";
import "./globals.css";

const workSans = Work_Sans({
  subsets: ['latin'],
  display: 'swap',
  variable: '--font-work-sans',
})

const robotoMono = Roboto_Mono({
  subsets: ['latin'],
  display: 'swap',
  variable: '--font-roboto-mono',
})

export const metadata: Metadata = {
  title: "Auto Attendance",
  description: "",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en">
      <body className={`${workSans.variable} ${workSans.className} ${robotoMono.variable} min-h-screen bg-[#ffffff] bg-[linear-gradient(#e5e7eb_1px,transparent_1px),linear-gradient(to_right,#e5e7eb_1px,transparent_1px)] bg-[size:16px_16px]`}>
        {children}
      </body>
    </html>
  )
}
