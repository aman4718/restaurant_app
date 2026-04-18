import { Inter } from "next/font/google";
import "./globals.css";

const inter = Inter({ subsets: ["latin"], weight: ["400", "500", "600", "700", "800"] });

export const metadata = {
  title: "Culinary Curator",
  description: "Discover your next culinary obsession.",
};

export default function RootLayout({ children }) {
  return (
    <html lang="en">
      <body className={`${inter.className} antialiased bg-[var(--background)] text-text-dark min-h-screen`}>
        {children}
      </body>
    </html>
  );
}
