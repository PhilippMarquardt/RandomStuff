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
  model_name: string;
  history: Array<{ sender: "user" | "llm"; text: string }>;
  enabledTools: string[];
  systemPrompt: string;
  attachments?: { filename: string; content: string; content_type: string }[];
}

export interface SendMessageResponse {
  text: string;
  error?: string | null;
}

export class ChatService {
  /**
   * Send a message to the chat API
   * @param params - The parameters for sending a message
   * @returns The response from the chat API
   */
  async sendMessage(params: SendMessageParams): Promise<SendMessageResponse> {
    try {
      const response = await fetch(`${API_BASE_URL}/api/v1/chat/invoke`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          text: params.text,
          temperature: params.temperature,
          model_name: params.model_name,
          history: params.history,
          enabled_tools: params.enabledTools,
          system_prompt: params.systemPrompt,
          attachments: params.attachments
        }),
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ detail: 'Network error' }));
        throw new Error(errorData.detail || 'Failed to send message');
      }

      return await response.json();
    } catch (error) {
      console.error("Error sending message:", error);
      throw error;
    }
  }

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

  async fetchModels(): Promise<string[]> {
    try {
      const response = await fetch(`${API_BASE_URL}/api/v1/chat/models`);
      if (!response.ok) {
        throw new Error('Failed to fetch models');
      }
      return await response.json();
    } catch (error) {
      console.error("Error fetching models:", error);
      return [];
    }
  }
}

export const chatService = new ChatService();

// Legacy exports for backward compatibility
export const sendMessage = chatService.sendMessage;
export const searchDocuments = chatService.searchDocuments; 