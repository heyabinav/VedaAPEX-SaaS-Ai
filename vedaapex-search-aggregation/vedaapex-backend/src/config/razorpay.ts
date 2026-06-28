import Razorpay from "razorpay";

import { env } from "./env";

let razorpayClient: Razorpay | null = null;

export const getRazorpayClient = () => {
  if (razorpayClient) {
    return razorpayClient;
  }

  if (!env.RAZORPAY_KEY_ID || !env.RAZORPAY_KEY_SECRET) {
    throw new Error("Razorpay is not configured.");
  }

  razorpayClient = new Razorpay({
    key_id: env.RAZORPAY_KEY_ID,
    key_secret: env.RAZORPAY_KEY_SECRET,
  });

  return razorpayClient;
};
