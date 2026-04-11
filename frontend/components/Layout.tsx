"use client";

import { useEffect } from "react";
import { usePathname, useRouter } from "next/navigation";
import DashboardLayout from "./DashboardLayout";
import { getToken } from "../app/lib/auth";
import { useAuth } from "../app/lib/store";
import { getMyProfile } from "../lib/api/profile";
import { getTrialStatus } from "../lib/api/profile";
import { useTrialStore } from "../store/trialStore";

export default function Layout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const { setAuthenticated } = useAuth();
  const { setTrial } = useTrialStore();

  const isPublicRoute =
    pathname === "/" ||
    pathname === "/login" ||
    pathname === "/register" ||
    pathname === "/verify-email" ||
    pathname === "/pricing";

  useEffect(() => {
    const check = async () => {
      const token = getToken();
      setAuthenticated(Boolean(token));
      if (!token && !isPublicRoute) {
        router.replace("/login");
        return;
      }
      if (token && !isPublicRoute && pathname !== "/onboarding") {
        try {
          const me = await getMyProfile();
          if (!me.onboarding_completed) {
            router.replace("/onboarding");
            return;
          }
          const trial = await getTrialStatus();
          if (trial.on_trial) {
            setTrial({
              onTrial: true,
              isExpired: Boolean(trial.is_expired),
              daysLeft: trial.days_left ?? 0,
              warningLevel: trial.warning_level ?? "normal",
            });
          } else {
            setTrial({ onTrial: false, isExpired: false, daysLeft: 0, warningLevel: "normal" });
          }
        } catch {}
      }
    };
    check();
  }, [pathname, router, setAuthenticated, isPublicRoute, setTrial]);

  if (isPublicRoute) return <>{children}</>;

  return <DashboardLayout>{children}</DashboardLayout>;
}
