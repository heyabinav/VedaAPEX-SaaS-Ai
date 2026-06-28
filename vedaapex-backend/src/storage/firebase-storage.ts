import { getFirebaseApp } from "../config/firebase";
import { env } from "../config/env";
import type { StorageAdapter, UploadObjectInput, UploadObjectResult } from "./adapter";

export class FirebaseStorageAdapter implements StorageAdapter {
  private readonly bucket: any;

  constructor() {
    const app = getFirebaseApp();

    if (!app) {
      throw new Error("Firebase Admin SDK is not configured.");
    }

    this.bucket = app.storage().bucket();
  }

  async uploadObject(input: UploadObjectInput): Promise<UploadObjectResult> {
    const file = this.bucket.file(input.key);

    await file.save(input.body, {
      contentType: input.contentType,
      resumable: false,
      public: false,
    });

    return {
      key: input.key,
      url: await this.getSignedDownloadUrl(input.key),
    };
  }

  async deleteObject(key: string): Promise<void> {
    await this.bucket.file(key).delete({ ignoreNotFound: true });
  }

  async getSignedDownloadUrl(key: string, expiresInSeconds = env.SIGNED_URL_TTL_SECONDS): Promise<string> {
    const [url] = await this.bucket.file(key).getSignedUrl({
      action: "read",
      expires: Date.now() + expiresInSeconds * 1000,
      version: "v4",
    });

    return url;
  }

  async getSignedUploadUrl(key: string, contentType: string, expiresInSeconds = env.SIGNED_URL_TTL_SECONDS): Promise<string> {
    const [url] = await this.bucket.file(key).getSignedUrl({
      action: "write",
      expires: Date.now() + expiresInSeconds * 1000,
      version: "v4",
      contentType,
    });

    return url;
  }
}
