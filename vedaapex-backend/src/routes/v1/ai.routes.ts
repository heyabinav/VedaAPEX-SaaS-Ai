import { Router } from "express";
import multer from "multer";

import { aiController } from "../../controllers/ai.controller";
import { ROLES } from "../../constants/roles";
import { authenticate } from "../../middleware/authenticate";
import { authorize } from "../../middleware/authorize";
import { validate } from "../../middleware/validate";
import { analyzePaperSchema, evaluateAnswerSchema, generateStudyPackSchema, studyChatSchema } from "../../validators/ai.validator";
import { env } from "../../config/env";

const upload = multer({
  storage: multer.memoryStorage(),
  limits: {
    fileSize: env.MAX_UPLOAD_MB * 1024 * 1024,
  },
});

export const aiRouter = Router();

/**
 * @openapi
 * /ai/papers/{paperId}/analyze:
 *   post:
 *     summary: Run AI analysis for a paper.
 */
aiRouter.post("/papers/:paperId/analyze", authenticate, authorize(ROLES.ADMIN), validate(analyzePaperSchema), aiController.analyzePaper);
aiRouter.post("/papers/:paperId/study-pack", authenticate, validate(generateStudyPackSchema), aiController.generateStudyPack);
aiRouter.post("/answers/evaluate", authenticate, upload.single("file"), validate(evaluateAnswerSchema), aiController.evaluateAnswer);
aiRouter.post("/study/chat", authenticate, validate(studyChatSchema), aiController.studyChat);
