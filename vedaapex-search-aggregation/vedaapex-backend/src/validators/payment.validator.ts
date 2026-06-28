import { z } from "zod";

export const createPaymentOrderSchema = z.object({
  amountPaise: z.coerce.number().int().min(1),
  currency: z.string().default("INR"),
  purpose: z.string().min(2).max(120).optional(),
  notes: z.record(z.any()).optional(),
});

export const verifyPaymentSchema = z.object({
  razorpay_order_id: z.string().min(5),
  razorpay_payment_id: z.string().min(5),
  razorpay_signature: z.string().min(10),
  metadata: z.record(z.any()).optional(),
});

export const paymentIdParamSchema = z.object({
  paymentId: z.string().cuid(),
});
