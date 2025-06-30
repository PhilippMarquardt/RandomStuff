// Service exports
export { chatService } from './chat-service';
export { uploadService } from './upload-service';
export { fileService } from './file-service';
export { toolService } from './tool-service';

// Type exports
export type { 
  ChatMessage, 
  ChatMessageResponse, 
  FileAttachment, 
  SendMessageParams 
} from './chat-service';

export type { UploadResult } from './upload-service';
export type { ConvertedFile } from './file-service';
export type { Tool } from './tool-service';

// Legacy function exports for backward compatibility
export { 
  sendMessage, 
  searchDocuments 
} from './chat-service';

export { fetchCollections } from './upload-service';
export { convertFile } from './file-service';
export { fetchTools } from './tool-service'; 