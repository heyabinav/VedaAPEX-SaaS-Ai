import pdfParse from "pdf-parse";

import { env } from "../config/env";
import { ApiError } from "../utils/api-error";

export const pdfService = {
  async inspectPdf(file: Express.Multer.File) {
    if (file.mimetype !== env.PDF_ALLOWED_MIME) {
      throw new ApiError(400, "Only PDF uploads are supported.");
    }

    const maxBytes = env.MAX_UPLOAD_MB * 1024 * 1024;

    if (file.size > maxBytes) {
      throw new ApiError(400, `PDF exceeds max size of ${env.MAX_UPLOAD_MB} MB.`);
    }

    const parsed = await pdfParse(file.buffer);

    return {
      text: parsed.text?.trim() ?? "",
      pageCount: parsed.numpages ?? 0,
      info: parsed.info,
    };
  },
};
