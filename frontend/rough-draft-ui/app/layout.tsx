import "./globals.css";
import type { Metadata } from "next";
import Providers from "./providers";
import { SiteChrome } from "./ui/site-chrome";

export const metadata: Metadata = {
  title: {
    default: "Rough Draft Football",
    template: "%s • Rough Draft Football",
  },
  description:
    "Community-voted NFL draft outcomes, fantasy football tools, and analysis.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <Providers>
          <SiteChrome>{children}</SiteChrome>
        </Providers>
      </body>
    </html>
  );
}
