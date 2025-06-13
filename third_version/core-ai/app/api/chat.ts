import { API_BASE_URL, API_ENDPOINTS } from './config';

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

export interface SendMessageParams {
  text: string;
  temperature: number;
  history: Array<{ sender: "user" | "llm"; text: string }>;
  enabledTools: string[];
  systemPrompt: string;
  attachments?: FileAttachment[];
}

export async function sendMessage(params: SendMessageParams): Promise<ChatMessageResponse> {
  const requestBody: any = {
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
} 