import { API_BASE_URL, API_ENDPOINTS } from '../config';

export interface ChatMessage {
  text: string;
  sender: string;
  attachments?: Array<{
    filename: string;
    content_type: string;
    size: number;
  }>;
}

export interface ChatMessageResponse {
  text: string;
  error?: string | null;
}

export interface FileAttachment {
  filename: string;
  content: string;
  content_type: string;
}

export interface SearchResult {
  content: string;
  metadata: {
    source_file: string;
  };
}

export interface SearchResultsResponse {
  results: SearchResult[];
}

export interface SendMessageParams {
  text: string;
  temperature: number;
  history: Array<{ sender: "user" | "llm"; text: string }>;
  enabledTools: string[];
  systemPrompt: string;
  attachments?: FileAttachment[];
}

export const chatService = {
  /**
   * Send a message to the chat API
   */
  async sendMessage(params: SendMessageParams): Promise<ChatMessageResponse> {
    const requestBody: {
      text: string;
      temperature: number;
      history: Array<{ sender: "user" | "llm"; text: string }>;
      enabled_tools: string[];
      system_prompt: string;
      attachments?: FileAttachment[];
    } = {
      text: params.text,
      temperature: params.temperature,
      history: params.history,
      enabled_tools: params.enabledTools,
      system_prompt: params.systemPrompt
    };

    // Add file attachments if any
    if (params.attachments && params.attachments.length > 0) {
      requestBody.attachments = params.attachments;
    }

    const response = await fetch(`${API_BASE_URL}${API_ENDPOINTS.chatInvoke}`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(requestBody),
    });

    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(errorData.detail || 'Network response was not ok');
    }

    return await response.json();
  },

  /**
   * Search documents in a specific collection
   */
  async searchDocuments(query: string, collectionName: string): Promise<string> {
    try {
      const response = await fetch(`${API_BASE_URL}${API_ENDPOINTS.search}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          query: query,
          collection_name: collectionName,
          k: 3 // Get top 3 relevant documents
        }),
      });

      if (response.ok) {
        const searchResults: SearchResultsResponse = await response.json();
        if (searchResults.results && searchResults.results.length > 0) {
          // Format the search results into context
          const context = searchResults.results
            .map((result: SearchResult, index: number) => 
              `Document ${index + 1} (from ${result.metadata.source_file}):\n${result.content}`
            )
            .join('\n\n');
          return context;
        }
      }
    } catch (error) {
      console.error('Error searching documents:', error);
    }
    return '';
  }
};

// Legacy exports for backward compatibility
export const sendMessage = chatService.sendMessage;
export const searchDocuments = chatService.searchDocuments; 