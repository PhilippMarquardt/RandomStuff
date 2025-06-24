import { API_BASE_URL, API_ENDPOINTS } from '../config';

export interface UploadResult {
  success: boolean;
  message: string;
  collection_name: string;
  document_count: number;
  file_name: string;
}

export const uploadService = {
  /**
   * Fetch all available collections
   */
  async fetchCollections(): Promise<string[]> {
    try {
      const response = await fetch(`${API_BASE_URL}${API_ENDPOINTS.collections}`);
      if (response.ok) {
        const data = await response.json();
        return data;
      }
      return [];
    } catch (error) {
      console.error('Error fetching collections:', error);
      return [];
    }
  },

  /**
   * Upload a file to a specific collection
   */
  async uploadFile(file: File, collectionName: string): Promise<UploadResult> {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('collection_name', collectionName.trim());

    const response = await fetch(`${API_BASE_URL}${API_ENDPOINTS.upload}`, {
      method: 'POST',
      body: formData,
    });

    const result = await response.json();

    if (!response.ok) {
      throw new Error(result.message || 'Upload failed');
    }

    return result;
  }
};

// Legacy exports for backward compatibility
export const fetchCollections = uploadService.fetchCollections; 