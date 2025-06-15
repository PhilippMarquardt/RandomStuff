export type UploadStatus = 'idle' | 'uploading' | 'success' | 'error';

export interface UploadResult {
  success: boolean;
  message: string;
  collection_name: string;
  document_count: number;
  file_name: string;
} 