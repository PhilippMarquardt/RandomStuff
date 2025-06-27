export interface MarkdownNode {
  type: string;
  value?: string;
  children?: MarkdownNode[];
} 