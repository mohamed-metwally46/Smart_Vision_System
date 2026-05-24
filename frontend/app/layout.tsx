"use client";

import "./globals.css";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useState } from "react";
import Sidebar from "@/components/layout/Sidebar";
import TopBar from "@/components/layout/TopBar";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30_000,
      retry: 2,
    },
  },
});

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const [client] = useState(() => queryClient);

  return (
    <html lang="en">
      <head>
        <title>Smart Vision System</title>
        <meta name="description" content="AI-powered surveillance dashboard" />
        <link rel="icon" href="/favicon.ico" />
      </head>
      <body className="flex h-screen overflow-hidden bg-surface-900">
        <QueryClientProvider client={client}>
          <Sidebar />
          <div className="flex flex-col flex-1 overflow-hidden">
            <TopBar />
            <main className="flex-1 overflow-auto p-4 lg:p-6">
              {children}
            </main>
          </div>
        </QueryClientProvider>
      </body>
    </html>
  );
}
