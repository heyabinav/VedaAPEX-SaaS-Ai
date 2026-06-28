import { Router } from "express";

import { studyController } from "../../controllers/study.controller";
import { authenticate } from "../../middleware/authenticate";
import { validate } from "../../middleware/validate";
import { generateMockTestSchema, generateStudyPlanSchema, updateProgressSchema } from "../../validators/study.validator";

export const studyRouter = Router();

studyRouter.use(authenticate);
studyRouter.get("/dashboard", studyController.dashboard);
studyRouter.get("/plans", studyController.listPlans);
studyRouter.post("/plans/generate", validate(generateStudyPlanSchema), studyController.generatePlan);
studyRouter.put("/progress", validate(updateProgressSchema), studyController.updateProgress);
studyRouter.post("/mock-tests/generate", validate(generateMockTestSchema), studyController.generateMockTest);
