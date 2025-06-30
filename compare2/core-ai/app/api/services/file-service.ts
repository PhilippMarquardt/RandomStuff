import { API_BASE_URL, API_ENDPOINTS } from '../config';

export interface ConvertedFile {
  text: string;
  [key: string]: unknown; // For any additional fields returned by the API
}

export interface WordBBox {
  text: string;
  bbox: [number, number, number, number]; // [x0, y0, x1, y1]
  block_no: number;
  line_no: number;
  word_no: number;
}

export interface ImageBBox {
  bbox: [number, number, number, number]; // [x0, y0, x1, y1]
  area: number;
  type: string;
}

export interface PDFPage {
  page_number: number;
  dimensions: {
    width: number;
    height: number;
  };
  words: WordBBox[];
  images: ImageBBox[];
}

export interface PDFWordsData {
  pages: PDFPage[];
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
  },

  /**
   * Extract words with bounding boxes from PDF
   */
  async extractPDFWords(file: File): Promise<PDFWordsData> {
    const formData = new FormData();
    formData.append('file', file);

    const response = await fetch(`${API_BASE_URL}/api/v1/pdf/extract-words`, {
      method: 'POST',
      body: formData,
    });

    if (!response.ok) {
      throw new Error(`Failed to extract words from PDF ${file.name}`);
    }

    return await response.json();
  },

  /**
   * Extract a region from a PDF page as a base64 image
   */
  async extractImageFromRegion(
    file: File, 
    pageNumber: number, 
    bbox: [number, number, number, number]
  ): Promise<string> {
    const formData = new FormData();
    formData.append('file', file);
    
    const regionData = {
      page_number: pageNumber,
      bbox: bbox,
    };
    formData.append('region_data_str', JSON.stringify(regionData));

    const response = await fetch(`${API_BASE_URL}/api/v1/pdf/extract-image-region`, {
      method: 'POST',
      body: formData,
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({ detail: 'Unknown error' }));
      throw new Error(`Failed to extract image from PDF: ${errorData.detail}`);
    }

    const result = await response.json();
    return result.image;
  }
};

// Legacy exports for backward compatibility
export const convertFile = fileService.convertFile;
export const extractPDFWords = fileService.extractPDFWords; 