export const API_BASE_URL = 'http://localhost:8000';

export const API_ENDPOINTS = {
  // Upload/Collections endpoints
  collections: '/api/v1/upload/collections',
  search: '/api/v1/upload/search',
  upload: '/api/v1/upload/upload',
  
  // Chat endpoints
  chatInvoke: '/api/v1/chat/invoke',
  toolsList: '/api/v1/chat/tools/list',
  
  // File conversion endpoint
  convert: '/api/v1/convert',
}; 