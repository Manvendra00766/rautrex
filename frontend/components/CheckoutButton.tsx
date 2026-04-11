"use client";

import { useRouter } from "next/navigation";
import { createOrder, verifyPayment } from "../app/lib/api";

declare global {
  interface Window {
    Razorpay: any;
  }
}

export default function CheckoutButton({ plan, label }: { plan: "pro_monthly" | "pro_annual" | "team_monthly"; label: string }) {
  const router = useRouter();

  const handlePayment = async () => {
    const { order_id, amount, key } = await createOrder(plan);
    const rzp = new window.Razorpay({
      key,
      amount,
      order_id,
      name: "Rautrex",
      description: "Rautrex Subscription",
      handler: async (response: any) => {
        await verifyPayment({
          razorpay_order_id: response.razorpay_order_id,
          razorpay_payment_id: response.razorpay_payment_id,
          razorpay_signature: response.razorpay_signature,
          plan,
        });
        router.push("/dashboard?upgraded=true");
      },
      theme: { color: "#6366f1" },
    });
    rzp.open();
  };

  return (
    <button onClick={handlePayment} className="w-full rounded-md bg-indigo-500 px-4 py-2 text-sm font-semibold text-white hover:bg-indigo-400">
      {label}
    </button>
  );
}
