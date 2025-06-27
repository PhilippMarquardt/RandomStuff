import type { ChatMessage as ApiChatMessage } from '../api';

export type ChatMessage = ApiChatMessage;

export type VisualizationData = TableData | GraphData;

export type TableData = {
  type: 'table';
  data: { [key: string]: (string | number)[] };
}

export type GraphData = {
  type: 'line' | 'bar' | 'pie' | 'scatter' | 'heatmap' | 'box' | 'bubble';
  data: Record<string, unknown> | Record<string, unknown>[];
  layout?: Record<string, unknown>;
  config?: Record<string, unknown>;
} 