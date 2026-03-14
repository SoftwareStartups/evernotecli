export interface ResourceInfo {
  hashHex: string;
  mimeType: string;
  filename: string;
  data?: Uint8Array; // binary body; present when fetched with withResourcesData=true
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
