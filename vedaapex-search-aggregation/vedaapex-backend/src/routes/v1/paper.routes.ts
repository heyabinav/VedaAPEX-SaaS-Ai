import { Router } from "express";
import multer from "multer";

import { paperController } from "../../controllers/paper.controller";
import { authorize } from "../../middleware/authorize";
import { authenticate } from "../../middleware/authenticate";
import { validate } from "../../middleware/validate";
import { env } from "../../config/env";
import { ROLES } from "../../constants/roles";
import { bulkImportPapersSchema, createPaperSchema, idParamSchema, paperQuerySchema, updatePaperSchema } from "../../validators/paper.validator";

const upload = multer({
  storage: multer.memoryStorage(),
  limits: {
    fileSize: env.MAX_UPLOAD_MB * 1024 * 1024,
  },
});

export const paperRouter = Router();

/**
 * @openapi
 * /papers:
 *   get:
 *     summary: Fetch previous year papers with filters and pagination.
 */
paperRouter.get("/", validate(paperQuerySchema, "query"), paperController.list);
paperRouter.get("/coverage", paperController.coverage);
paperRouter.get("/trending", paperController.trending);
paperRouter.get("/:paperId", validate(idParamSchema, "params"), paperController.getById);
paperRouter.post("/:paperId/download", validate(idParamSchema, "params"), paperController.downloadPaper);
paperRouter.post("/:paperId/bookmark", authenticate, validate(idParamSchema, "params"), paperController.bookmarkPaper);
paperRouter.delete("/:paperId/bookmark", authenticate, validate(idParamSchema, "params"), paperController.removeBookmark);

paperRouter.post(
  "/upload-url",
  authenticate,
  authorize(ROLES.ADMIN),
  validate(createPaperSchema),
  paperController.uploadUrl,
);
paperRouter.post(
  "/upload",
  authenticate,
  authorize(ROLES.ADMIN),
  upload.single("file"),
  validate(createPaperSchema),
  paperController.uploadPaper,
);
paperRouter.post(
  "/bulk-import",
  authenticate,
  authorize(ROLES.ADMIN),
  validate(bulkImportPapersSchema),
  paperController.bulkImport,
);
paperRouter.patch(
  "/:paperId",
  authenticate,
  authorize(ROLES.ADMIN),
  validate(idParamSchema, "params"),
  validate(updatePaperSchema),
  paperController.updatePaper,
);
paperRouter.delete("/:paperId", authenticate, authorize(ROLES.ADMIN), validate(idParamSchema, "params"), paperController.deletePaper);
