import { Router } from "express";

import { paymentController } from "../../controllers/payment.controller";
import { authenticate } from "../../middleware/authenticate";
import { validate } from "../../middleware/validate";
import { createPaymentOrderSchema, verifyPaymentSchema } from "../../validators/payment.validator";

export const paymentRouter = Router();

paymentRouter.use(authenticate);
paymentRouter.post("/orders", validate(createPaymentOrderSchema), paymentController.createOrder);
paymentRouter.post("/verify", validate(verifyPaymentSchema), paymentController.verifyPayment);
paymentRouter.get("/my", paymentController.listMyPayments);
