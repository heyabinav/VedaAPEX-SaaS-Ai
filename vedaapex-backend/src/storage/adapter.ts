export type UploadObjectInput = {
  key: string;
  body: Buffer;
  contentType: string;
};

export type UploadObjectResult = {
  key: string;
  url: string;
};

export interface StorageAdapter {
  uploadObject(input: UploadObjectInput): Promise<UploadObjectResult>;
  deleteObject(key: string): Promise<void>;
  getSignedDownloadUrl(key: string, expiresInSeconds?: number): Promise<string>;
  getSignedUploadUrl(key: string, contentType: string, expiresInSeconds?: number): Promise<string>;
}
