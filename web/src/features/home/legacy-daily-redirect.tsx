"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";

export function LegacyDailyRedirect() {
  const router = useRouter();
  useEffect(() => {
    if (window.location.hash === "#daily-question") router.replace("/daily-question");
  }, [router]);
  return null;
}
