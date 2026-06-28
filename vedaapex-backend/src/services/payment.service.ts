import crypto from "node:crypto";

import { PaymentOrderStatus, PaymentStatus } from "@prisma/client";

import { env } from "../config/env";
import { getRazorpayClient } from "../config/razorpay";
import { prisma } from "../config/prisma";
import { ApiError } from "../utils/api-error";
import { toOptionalJsonValue } from "../utils/prisma-json";
import { activityService } from "./activity.service";
import { usageService } from "./usage.service";
import { UsageMetricType } from "@prisma/client";

type CreateOrderInput = {
  userId: string;
  amountPaise: number;
  currency?: string;
  purpose?: string;
  notes?: Record<string, unknown>;
};

type VerifyInput = {
  userId: string;
  razorpay_order_id: string;
  razorpay_payment_id: string;
  razorpay_signature: string;
  metadata?: Record<string, unknown>;
};

const buildReceipt = () => `vedaapex_${Date.now()}_${crypto.randomBytes(4).toString("hex")}`;

const normalizeAmount = (amountPaise: number) => {
  if (amountPaise < env.RAZORPAY_MIN_AMOUNT_PAISA) {
    throw new ApiError(400, `Minimum payment amount is ${env.RAZORPAY_MIN_AMOUNT_PAISA} paise.`);
  }

  return amountPaise;
};

export const paymentService = {
  async createOrder(input: CreateOrderInput) {
    if (!env.RAZORPAY_KEY_ID || !env.RAZORPAY_KEY_SECRET) {
      throw new ApiError(500, "Razorpay is not configured.");
    }

    const amountPaise = normalizeAmount(input.amountPaise);
    const currency = input.currency ?? env.RAZORPAY_CURRENCY;
    const receipt = buildReceipt();
    const client = getRazorpayClient();

    const order = await client.orders.create({
      amount: amountPaise,
      currency,
      receipt,
      notes: {
        ...(input.notes ?? {}),
        userId: input.userId,
        purpose: input.purpose ?? "VEDAAPEX_PAYMENT",
      },
    });

    const paymentOrder = await prisma.paymentOrder.create({
      data: {
        userId: input.userId,
        orderId: order.id,
        receipt,
        amountPaise,
        currency,
        purpose: input.purpose,
        notes: toOptionalJsonValue(input.notes),
        providerPayload: toOptionalJsonValue(order),
      },
    });

    await activityService.log({
      userId: input.userId,
      action: "payment.order.created",
      entityType: "PaymentOrder",
      entityId: paymentOrder.id,
      metadata: {
        amountPaise,
        currency,
        purpose: input.purpose,
      },
    });

    return {
      id: paymentOrder.id,
      orderId: paymentOrder.orderId,
      amountPaise: paymentOrder.amountPaise,
      currency: paymentOrder.currency,
      receipt: paymentOrder.receipt,
      keyId: env.RAZORPAY_KEY_ID,
      razorpayOrder: order,
    };
  },

  verifySignature(input: VerifyInput) {
    if (!env.RAZORPAY_KEY_SECRET) {
      throw new ApiError(500, "Razorpay is not configured.");
    }

    const expectedSignature = crypto
      .createHmac("sha256", env.RAZORPAY_KEY_SECRET)
      .update(`${input.razorpay_order_id}|${input.razorpay_payment_id}`)
      .digest("hex");

    if (expectedSignature !== input.razorpay_signature) {
      throw new ApiError(400, "Invalid Razorpay signature.");
    }
  },

  async confirmPayment(input: VerifyInput) {
    const order = await prisma.paymentOrder.findUnique({
      where: {
        orderId: input.razorpay_order_id,
      },
      include: {
        transaction: true,
      },
    });

    if (!order) {
      throw new ApiError(404, "Payment order not found.");
    }

    if (order.userId !== input.userId) {
      throw new ApiError(403, "This payment order does not belong to the current user.");
    }

    this.verifySignature(input);

    const transaction = await prisma.paymentTransaction.upsert({
      where: {
        paymentOrderId: order.id,
      },
      update: {
        paymentId: input.razorpay_payment_id,
        signature: input.razorpay_signature,
        status: PaymentStatus.VERIFIED,
        verifiedAt: new Date(),
        metadata: toOptionalJsonValue(input.metadata),
      },
      create: {
        userId: input.userId,
        paymentOrderId: order.id,
        provider: "RAZORPAY",
        paymentId: input.razorpay_payment_id,
        orderId: input.razorpay_order_id,
        signature: input.razorpay_signature,
        status: PaymentStatus.VERIFIED,
        amountPaise: order.amountPaise,
        currency: order.currency,
        metadata: toOptionalJsonValue(input.metadata),
        verifiedAt: new Date(),
      },
    });

    await prisma.paymentOrder.update({
      where: { id: order.id },
      data: {
        status: PaymentOrderStatus.PAID,
      },
    });

    await usageService.track({
      userId: input.userId,
      metricType: UsageMetricType.PAYMENT,
      provider: "RAZORPAY",
      metadata: {
        paymentOrderId: order.id,
        paymentTransactionId: transaction.id,
        amountPaise: order.amountPaise,
        currency: order.currency,
      },
    });

    await activityService.log({
      userId: input.userId,
      action: "payment.verified",
      entityType: "PaymentTransaction",
      entityId: transaction.id,
      metadata: {
        amountPaise: order.amountPaise,
        currency: order.currency,
      },
    });

    return transaction;
  },

  async listMyPayments(userId: string) {
    return prisma.paymentTransaction.findMany({
      where: { userId },
      orderBy: { createdAt: "desc" },
      include: {
        paymentOrder: true,
      },
    });
  },
};
