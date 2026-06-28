import { Router } from "express";
import { z } from "zod";

import { adminController } from "../../controllers/admin.controller";
import { ROLES } from "../../constants/roles";
import { authenticate } from "../../middleware/authenticate";
import { authorize } from "../../middleware/authorize";
import { validate } from "../../middleware/validate";

const roleSchema = z.object({
  role: z.enum(["USER", "ADMIN"]),
});

const featureSchema = z.object({
  isFeatured: z.boolean().default(true),
});

const userIdParamSchema = z.object({
  userId: z.string().cuid(),
});

const paperIdParamSchema = z.object({
  paperId: z.string().cuid(),
});

export const adminRouter = Router();

adminRouter.use(authenticate, authorize(ROLES.ADMIN));
adminRouter.get("/users", adminController.listUsers);
adminRouter.patch("/users/:userId/role", validate(userIdParamSchema, "params"), validate(roleSchema), adminController.updateUserRole);
adminRouter.post("/users/:userId/revoke-sessions", validate(userIdParamSchema, "params"), adminController.revokeUserSessions);
adminRouter.post("/papers/:paperId/feature", validate(paperIdParamSchema, "params"), validate(featureSchema), adminController.featurePaper);
adminRouter.get("/analytics/overview", adminController.analyticsOverview);
adminRouter.get("/analytics/papers", adminController.paperAnalytics);
adminRouter.get("/ai-reports", adminController.aiReports);
