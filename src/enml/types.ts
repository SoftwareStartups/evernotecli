export interface ResourceInfo {
  hashHex: string;
  mimeType: string;
  filename: string;
}

export interface Attachment {
  hashHex: string;
  hashBytes: Uint8Array;
  mimeType: string;
  data: Uint8Array;
  filename: string;
  sourcePath: string;
}

export interface EnmlResult {
  enml: string;
  attachments: Attachment[];
}
