import { Router } from "express";
import { z } from "zod";

import { notificationController } from "../../controllers/notification.controller";
import { authenticate } from "../../middleware/authenticate";
import { validate } from "../../middleware/validate";

const notificationIdParamSchema = z.object({
  notificationId: z.string().cuid(),
});

export const notificationRouter = Router();

notificationRouter.use(authenticate);
notificationRouter.get("/", notificationController.list);
notificationRouter.post("/:notificationId/read", validate(notificationIdParamSchema, "params"), notificationController.markRead);
