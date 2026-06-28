import { StatusCodes } from "http-status-codes";

import { paymentService } from "../services/payment.service";
import { asyncHandler } from "../utils/async-handler";
import { successResponse } from "../utils/response";

export const paymentController = {
  createOrder: asyncHandler(async (req, res) => {
    const result = await paymentService.createOrder({
      userId: req.authUser!.id,
      amountPaise: req.body.amountPaise,
      currency: req.body.currency,
      purpose: req.body.purpose,
      notes: req.body.notes,
    });

    res.status(StatusCodes.CREATED).json(successResponse(result));
  }),

  verifyPayment: asyncHandler(async (req, res) => {
    const result = await paymentService.confirmPayment({
      userId: req.authUser!.id,
      razorpay_order_id: req.body.razorpay_order_id,
      razorpay_payment_id: req.body.razorpay_payment_id,
      razorpay_signature: req.body.razorpay_signature,
      metadata: req.body.metadata,
    });

    res.status(StatusCodes.OK).json(successResponse(result));
  }),

  listMyPayments: asyncHandler(async (req, res) => {
    const result = await paymentService.listMyPayments(req.authUser!.id);
    res.status(StatusCodes.OK).json(successResponse(result));
  }),
};
