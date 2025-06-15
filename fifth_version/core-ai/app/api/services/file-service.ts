import { API_BASE_URL, API_ENDPOINTS } from '../config';

export interface ConvertedFile {
  text: string;
  [key: string]: unknown; // For any additional fields returned by the API
}

export const fileService = {
  /**
   * Convert a file to text format
   */
  async convertFile(file: File): Promise<ConvertedFile> {
    const formData = new FormData();
    formData.append('file', file);

    const response = await fetch(`${API_BASE_URL}${API_ENDPOINTS.convert}`, {
      method: 'POST',
      body: formData,
    });

    if (!response.ok) {
      throw new Error(`Failed to convert file ${file.name}`);
    }

    return await response.json();
  }
};

// Legacy exports for backward compatibility
export const convertFile = fileService.convertFile; 