import { nanoid } from "nanoid";

import { env } from "../config/env";
import type { StorageAdapter } from "../storage/adapter";
import { FirebaseStorageAdapter } from "../storage/firebase-storage";
import { R2StorageAdapter } from "../storage/r2-storage";

let adapter: StorageAdapter | null = null;

const getAdapter = () => {
  if (adapter) {
    return adapter;
  }

  adapter = env.STORAGE_PROVIDER === "firebase" ? new FirebaseStorageAdapter() : new R2StorageAdapter();
  return adapter;
};

export const storageService = {
  buildPaperStorageKey: (paper: { board: string; classLevel: number; subject: string; year: number }) =>
    `papers/${paper.board.toLowerCase()}/class-${paper.classLevel}/${paper.subject.toLowerCase().replace(/\s+/g, "-")}/${paper.year}-${nanoid(8)}.pdf`,

  buildAnswerStorageKey: (userId: string, extension: string) => `answers/${userId}/${Date.now()}-${nanoid(8)}.${extension}`,

  buildMediaStorageKey: (assetType: "IMAGE" | "VIDEO", extension: string) =>
    `media/originals/${assetType.toLowerCase()}/${Date.now()}-${nanoid(8)}.${extension}`,

  buildProcessedMediaStorageKey: (assetType: "IMAGE" | "VIDEO", operation: string, extension: string) =>
    `media/processed/${assetType.toLowerCase()}/${operation.toLowerCase().replace(/_/g, "-")}/${Date.now()}-${nanoid(8)}.${extension}`,

  async uploadBuffer(key: string, buffer: Buffer, contentType: string) {
    return getAdapter().uploadObject({
      key,
      body: buffer,
      contentType,
    });
  },

  async deleteObject(key: string) {
    await getAdapter().deleteObject(key);
  },

  async getSignedDownloadUrl(key: string) {
    return getAdapter().getSignedDownloadUrl(key);
  },

  async getSignedUploadUrl(key: string, contentType: string) {
    return getAdapter().getSignedUploadUrl(key, contentType);
  },
};
