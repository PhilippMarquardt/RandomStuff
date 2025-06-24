import type { ChatMessage } from '../api';
 
export type ChatSession = {
  id: string;
  name: string;
  messages: ChatMessage[];
}; 