import { PutObjectCommand, DeleteObjectCommand, GetObjectCommand, PutObjectCommandInput, S3Client } from "@aws-sdk/client-s3";
import { getSignedUrl } from "@aws-sdk/s3-request-presigner";

import { env } from "../config/env";
import type { StorageAdapter, UploadObjectInput, UploadObjectResult } from "./adapter";

export class R2StorageAdapter implements StorageAdapter {
  private readonly client: S3Client;

  constructor() {
    if (!env.R2_ACCESS_KEY_ID || !env.R2_SECRET_ACCESS_KEY || !env.R2_BUCKET || !env.R2_ENDPOINT) {
      throw new Error("Cloudflare R2 credentials are not fully configured.");
    }

    this.client = new S3Client({
      region: "auto",
      endpoint: env.R2_ENDPOINT,
      credentials: {
        accessKeyId: env.R2_ACCESS_KEY_ID,
        secretAccessKey: env.R2_SECRET_ACCESS_KEY,
      },
    });
  }

  async uploadObject(input: UploadObjectInput): Promise<UploadObjectResult> {
    const commandInput: PutObjectCommandInput = {
      Bucket: env.R2_BUCKET,
      Key: input.key,
      Body: input.body,
      ContentType: input.contentType,
    };

    await this.client.send(new PutObjectCommand(commandInput));

    return {
      key: input.key,
      url: env.R2_PUBLIC_BASE_URL ? `${env.R2_PUBLIC_BASE_URL}/${input.key}` : await this.getSignedDownloadUrl(input.key),
    };
  }

  async deleteObject(key: string): Promise<void> {
    await this.client.send(
      new DeleteObjectCommand({
        Bucket: env.R2_BUCKET,
        Key: key,
      }),
    );
  }

  async getSignedDownloadUrl(key: string, expiresInSeconds = env.SIGNED_URL_TTL_SECONDS): Promise<string> {
    return getSignedUrl(
      this.client,
      new GetObjectCommand({
        Bucket: env.R2_BUCKET,
        Key: key,
      }),
      { expiresIn: expiresInSeconds },
    );
  }

  async getSignedUploadUrl(key: string, contentType: string, expiresInSeconds = env.SIGNED_URL_TTL_SECONDS): Promise<string> {
    return getSignedUrl(
      this.client,
      new PutObjectCommand({
        Bucket: env.R2_BUCKET,
        Key: key,
        ContentType: contentType,
      }),
      { expiresIn: expiresInSeconds },
    );
  }
}
