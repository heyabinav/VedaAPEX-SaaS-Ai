import { Router } from "express";
import multer from "multer";

import { env } from "../../config/env";
import { mediaController } from "../../controllers/media.controller";
import { authenticate } from "../../middleware/authenticate";
import { validate } from "../../middleware/validate";
import {
  createMediaJobSchema,
  createMediaUploadUrlSchema,
  mediaJobParamSchema,
  registerMediaAssetSchema,
  uploadMediaAssetSchema,
} from "../../validators/media.validator";

const upload = multer({
  storage: multer.memoryStorage(),
  limits: {
    fileSize: env.MEDIA_UPLOAD_MAX_MB * 1024 * 1024,
  },
});

export const mediaRouter = Router();

mediaRouter.use(authenticate);
mediaRouter.get("/assets", mediaController.listAssets);
mediaRouter.post("/upload-url", validate(createMediaUploadUrlSchema), mediaController.createUploadUrl);
mediaRouter.post("/assets/register", validate(registerMediaAssetSchema), mediaController.registerAsset);
mediaRouter.post("/assets/upload", upload.single("file"), validate(uploadMediaAssetSchema), mediaController.uploadAsset);
mediaRouter.get("/jobs", mediaController.listJobs);
mediaRouter.get("/jobs/:jobId", validate(mediaJobParamSchema, "params"), mediaController.getJob);
mediaRouter.post("/jobs", validate(createMediaJobSchema), mediaController.createJob);
