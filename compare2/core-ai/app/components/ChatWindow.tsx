"use client"

/**
 * ChatWindow Component with Table and Graph Rendering Support
 * 
 * This component supports rendering JSON tables and various graphs in chat messages from LLM responses.
 * The LLM can send visualization data using <START_FIGURE> and <END_FIGURE> markers with JSON format,
 * and it will be automatically rendered as proper HTML tables or interactive Plotly graphs.
 * 
 * Supported visualization types:
 * - "table": HTML tables
 * - "line": Line charts
 * - "bar": Bar charts  
 * - "scatter": Scatter plots
 * - "histogram": Histograms
 * - "heatmap": Heatmaps
 * - "pie": Pie charts
 * - "box": Box plots
 * - "violin": Violin plots
 * - "area": Area charts
 * - "bubble": Bubble charts
 * - "3d_scatter": 3D scatter plots
 * - "surface": 3D surface plots
 * 
 * Format for tables:
 * <START_FIGURE>
 * {
 *   "type": "table",
 *   "data": {
 *     "Column 1": ["row1_col1", "row2_col1", "row3_col1"],
 *     "Column 2": ["row1_col2", "row2_col2", "row3_col2"],
 *     "Column 3": ["row1_col3", "row2_col3", "row3_col3"]
 *   }
 * }
 * <END_FIGURE>
 * 
 * Format for graphs:
 * <START_FIGURE>
 * {
 *   "type": "line",
 *   "data": {
 *     "x": [1, 2, 3, 4, 5],
 *     "y": [10, 15, 13, 17, 20]
 *   },
 *   "layout": {
 *     "title": "Sample Line Chart",
 *     "xaxis": {"title": "X Axis"},
 *     "yaxis": {"title": "Y Axis"}
 *   }
 * }
 * <END_FIGURE>
 * 
 * Multiple series example:
 * <START_FIGURE>
 * {
 *   "type": "line",
 *   "data": [
 *     {
 *       "x": [1, 2, 3, 4],
 *       "y": [10, 11, 12, 13],
 *       "name": "Series 1"
 *     },
 *     {
 *       "x": [1, 2, 3, 4],
 *       "y": [16, 15, 14, 13],
 *       "name": "Series 2"
 *     }
 *   ],
 *   "layout": {
 *     "title": "Multi-series Line Chart"
 *   }
 * }
 * <END_FIGURE>
 * 
 * The component supports multiple visualizations in a single message. Each visualization should be
 * wrapped in <START_FIGURE>...</END_FIGURE> markers.
 * 
 * Example usage in LLM response:
 * "Here's the comparison data:
 * 
 * <START_FIGURE>
 * {
 *   "type": "table",
 *   "data": {
 *     "Document": ["Doc A", "Doc B", "Doc C"],
 *     "Pages": [10, 15, 8],
 *     "Status": ["Complete", "In Progress", "Complete"]
 *   }
 * }
 * <END_FIGURE>
 * 
 * And here's another table:
 * 
 * <START_FIGURE>
 * {
 *   "type": "table",
 *   "data": {
 *     "Category": ["A", "B"],
 *     "Value": [100, 200]
 *   }
 * }
 * <END_FIGURE>
 * 
 * This will render properly formatted tables with hover effects, proper styling,
 * and responsive design. Multiple tables in one message are fully supported."
 */

import React, { useRef, useEffect } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import rehypeHighlight from 'rehype-highlight';
import 'highlight.js/styles/github-dark.css';
import { 
  PaperClipIcon, 
  SendIcon, 
  LoadingIcon, 
  FileIcon, 
  CloseIcon, 
  CollectionIcon 
} from './icons';
import { 
  type ChatMessage, 
  type FileAttachment, 
  type VisualizationData,
} from '../types';
import { ModuleRegistry, AllCommunityModule } from 'ag-grid-community';
import { CodeBlock } from './chat/CodeBlock';
import { RenderVisualization } from './chat/RenderVisualization';
import { type ComponentProps } from 'react';
import { type MarkdownNode } from '../types';

ModuleRegistry.registerModules([AllCommunityModule]);

type PreProps = ComponentProps<'pre'> & {
  node?: MarkdownNode;
};

// Function to detect and parse JSON visualization format with START_FIGURE/END_FIGURE markers
const parseVisualizationData = (text: string): { 
  visualizations: { vizData: VisualizationData; startIndex: number; endIndex: number }[];
  textParts: { text: string; isVisualization: boolean; vizData?: VisualizationData }[];
} => {
  try {
    const visualizations: { vizData: VisualizationData; startIndex: number; endIndex: number }[] = [];
    const figureRegex = /<START_FIGURE>([\s\S]*?)<END_FIGURE>/g;
    let match;

    // Find all <START_FIGURE>...<END_FIGURE> blocks
    while ((match = figureRegex.exec(text)) !== null) {
      const jsonContent = match[1].trim();
      try {
        const parsed = JSON.parse(jsonContent);
        
        // Validate table data
        if (parsed.type === 'table' && parsed.data && typeof parsed.data === 'object') {
          const isValidTableData = Object.values(parsed.data).every(value => Array.isArray(value));
          if (isValidTableData) {
            visualizations.push({
              vizData: parsed,
              startIndex: match.index,
              endIndex: match.index + match[0].length
            });
          }
        }
        // Validate graph data
        else if (parsed.type && ['line', 'bar', 'scatter', 'histogram', 'heatmap', 'pie', 'box', 'violin', 'area', 'bubble', '3d_scatter', 'surface'].includes(parsed.type)) {
          if (parsed.data) {
            visualizations.push({
              vizData: parsed,
              startIndex: match.index,
              endIndex: match.index + match[0].length
            });
          }
        }
      } catch {
        // Continue to next match if this one fails to parse
        continue;
      }
    }

    // If no visualizations found, return the original text
    if (visualizations.length === 0) {
      return {
        visualizations: [],
        textParts: [{ text, isVisualization: false }]
      };
    }

    // Split text into parts (text and visualizations)
    const textParts: { text: string; isVisualization: boolean; vizData?: VisualizationData }[] = [];
    let lastIndex = 0;

    visualizations.forEach((viz) => {
      // Add text before this visualization
      if (viz.startIndex > lastIndex) {
        const textBefore = text.slice(lastIndex, viz.startIndex).trim();
        if (textBefore) {
          textParts.push({ text: textBefore, isVisualization: false });
        }
      }
      
      // Add the visualization
      textParts.push({ 
        text: '', 
        isVisualization: true, 
        vizData: viz.vizData 
      });

      lastIndex = viz.endIndex;
    });

    // Add remaining text after last visualization
    if (lastIndex < text.length) {
      const remainingText = text.slice(lastIndex).trim();
      if (remainingText) {
        textParts.push({ text: remainingText, isVisualization: false });
      }
    }

    return { visualizations, textParts };
  } catch {
    return {
      visualizations: [],
      textParts: [{ text, isVisualization: false }]
    };
  }
};

interface ChatWindowProps {
  messages: ChatMessage[];
  inputValue: string;
  setInputValue: (value: string) => void;
  attachments: FileAttachment[];
  setAttachments: React.Dispatch<React.SetStateAction<FileAttachment[]>>;
  selectedCollection: string;
  onSendMessage: () => void;
  onFileSelect: (event: React.ChangeEvent<HTMLInputElement>) => void;
  onRemoveFile: (id: string) => void;
  isDragging: boolean;
  dropZoneRef: React.RefObject<HTMLDivElement>;
  fileInputRef: React.RefObject<HTMLInputElement>;
  isLoading: boolean;
}

export default function ChatWindow({
  messages,
  inputValue,
  setInputValue,
  attachments,
  setAttachments,
  selectedCollection,
  onSendMessage,
  onFileSelect,
  onRemoveFile,
  isDragging,
  dropZoneRef,
  fileInputRef,
  isLoading
}: ChatWindowProps) {
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Scroll to bottom when messages change
  useEffect(() => {
    if (messagesEndRef.current) {
      messagesEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [messages.length, isLoading]);

  const renderInputBarContent = (isCentered: boolean) => (
    <div className="relative flex items-end w-full">
      <textarea
        value={inputValue}
        onChange={(e) => setInputValue(e.target.value)}
        onKeyPress={(e) => {
          if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            onSendMessage();
          }
        }}
        placeholder={
          isCentered 
            ? selectedCollection === 'default' 
              ? "Ask the llm..." 
              : `Ask about documents in "${selectedCollection}"...`
            : selectedCollection === 'default'
              ? "Message LLM..."
              : `Ask about "${selectedCollection}"...`
        }
        rows={1}
        style={{ 
          resize: 'none',
          minHeight: 'auto',
          maxHeight: '120px'
        }}
        className={`flex-1 bg-transparent text-sm md:text-base py-2.5 focus:outline-none focus:ring-2 focus:ring-indigo-500 text-gray-800 placeholder-gray-400 rounded-md overflow-y-auto ${isCentered ? 'px-4' : 'px-3'}`}
        onInput={(e) => {
          const target = e.target as HTMLTextAreaElement;
          target.style.height = 'auto';
          target.style.height = Math.min(target.scrollHeight, 120) + 'px';
        }}
      />
      
      {/* Collection indicator */}
      {selectedCollection !== 'default' && (
        <div className="flex items-center mr-2 px-2 py-1 bg-indigo-50 border border-indigo-200 rounded-md">
          <CollectionIcon />
          <span className="text-xs text-indigo-700 font-medium truncate max-w-20">{selectedCollection}</span>
        </div>
      )}
      
      <button
        onClick={onSendMessage}
        className={`group ml-2 md:ml-3 p-2.5 rounded-full focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 transition-all duration-200 
                    ${(inputValue.trim() || attachments.length > 0) 
                        ? 'bg-indigo-600 hover:bg-indigo-500 text-white hover:shadow-md' 
                        : 'bg-gray-200 text-gray-400 cursor-not-allowed'}
                  `}
        aria-label="Send message"
        disabled={!(inputValue.trim() || attachments.length > 0)}
      >
        <SendIcon />
      </button>
    </div>
  );

  const renderMessages = () => (
    messages.map((message, index) => (
      <div
        key={`${message.sender}-${index}-${message.text.substring(0, 30)}`}
        className={`flex w-full mb-5 ${message.sender === 'user' ? 'justify-end' : 'justify-start'} animate-fadeSlideIn`}
      >
        <div className={`w-full max-w-xl md:max-w-2xl lg:max-w-3xl px-1 ${message.sender === 'user' ? 'ml-auto' : 'mr-auto'}`}>
          <div
            className={`px-5 py-3.5 rounded-2xl shadow-md prose prose-sm sm:prose-base max-w-none border
                        prose-p:my-2.5 prose-headings:my-3.5 prose-ul:my-2.5 prose-ol:my-2.5 prose-li:my-1.5 prose-li:leading-relaxed
                        prose-a:text-indigo-600 prose-a:no-underline prose-a:font-medium hover:prose-a:underline
                        prose-blockquote:my-2.5 prose-blockquote:px-3.5 prose-blockquote:border-indigo-200 prose-blockquote:not-italic prose-blockquote:text-gray-600
                        prose-code:before:content-[''] prose-code:after:content-[''] prose-code:font-mono prose-code:tracking-tight
                        prose-pre:relative prose-pre:p-4 prose-pre:rounded-xl prose-pre:my-3.5 prose-pre:font-mono prose-pre:bg-opacity-75
                        prose-p:leading-relaxed prose-headings:leading-tight
                        ${message.sender === 'user'
                          ? 'bg-indigo-600 text-white prose-strong:text-white border-indigo-500 shadow-indigo-100'
                          : 'bg-gray-50 text-gray-800 prose-strong:text-gray-900 border-gray-200 shadow-gray-100 relative before:absolute before:bottom-[-6px] before:left-[-6px] before:w-3 before:h-3 before:rotate-45 before:bg-gray-50 before:border-l before:border-b before:border-gray-200' 
                        }`}
          >
            {message.sender === 'llm' ? (
              (() => {
                const visualizationParseResult = parseVisualizationData(message.text);
                
                if (visualizationParseResult.visualizations.length > 0) {
                  return (
                    <div>
                      {visualizationParseResult.textParts.map((part, partIndex) => (
                         part.isVisualization && part.vizData ? (
                           <RenderVisualization key={partIndex} visData={part.vizData as VisualizationData} />
                         ) : (
                           <ReactMarkdown 
                             key={partIndex}
                             remarkPlugins={[remarkGfm]} 
                             rehypePlugins={[rehypeHighlight]}
                             components={{
                               pre: (props: PreProps) => <CodeBlock {...props} />,
                             }}
                           >
                             {part.text}
                           </ReactMarkdown>
                         )
                       ))}
                    </div>
                  );
                } else {
                  return (
                    <ReactMarkdown 
                      remarkPlugins={[remarkGfm]} 
                      rehypePlugins={[rehypeHighlight]}
                      components={{
                        pre: (props: PreProps) => <CodeBlock {...props} />,
                      }}
                    >
                      {message.text}
                    </ReactMarkdown>
                  );
                }
              })()
            ) : (
              <div>
                {message.text}
                {/* Show attached files for user messages */}
                {message.attachments && message.attachments.length > 0 && (
                  <div className="mt-2 flex flex-wrap gap-2">
                    {message.attachments.map((attachment: {filename: string}, attachIndex: number) => (
                      <div key={attachIndex} className="bg-gray-200 rounded-md px-2 py-1 text-sm text-gray-700 flex items-center">
                        <PaperClipIcon className="w-4 h-4 mr-1.5" />
                        {attachment.filename}
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      </div>
    ))
  );

  const renderAttachments = () => attachments.length > 0 && (
    <div className="flex flex-wrap gap-2 mb-2 px-2">
      <div className="w-full flex items-center justify-between mb-1">
        <div className="text-xs text-gray-500">
          {attachments.length} file{attachments.length > 1 ? 's' : ''} attached
        </div>
        <button
          onClick={() => setAttachments([])}
          className="text-xs text-gray-500 hover:text-red-600 font-medium transition-colors"
        >
          Clear All
        </button>
      </div>
      {attachments.map(attachment => (
        <div 
          key={attachment.id} 
          className="flex items-center bg-indigo-50 border border-indigo-100 px-2 py-1 rounded-md shadow-sm group"
        >
          <FileIcon fileType={attachment.file.type} />
          <span className="mx-2 text-xs text-gray-700 truncate max-w-[120px]">
            {attachment.file.name}
          </span>
          <button 
            onClick={() => onRemoveFile(attachment.id)}
            className="text-gray-400 hover:text-gray-600 transition-opacity"
          >
            <CloseIcon />
          </button>
        </div>
      ))}
    </div>
  );

  return (
    <main className="flex-1 flex flex-col overflow-y-hidden p-1 sm:p-2 md:p-3">
      {/* Message Display Area */}
      <div className={`flex-1 overflow-y-auto p-4 md:p-5 space-y-1 ${messages.length === 0 ? 'flex flex-col justify-center items-center' : 'pt-4'} scroll-smooth`}>
        {messages.length > 0 
          ? (
            <>
              {renderMessages()}
              {isLoading && (
                <div className="flex justify-start w-full">
                  <div className="w-full max-w-xl md:max-w-2xl lg:max-w-3xl px-1 mr-auto">
                    <div className="px-5 py-3.5 rounded-2xl shadow-md bg-gray-50 border border-gray-200 flex items-center space-x-3">
                      <LoadingIcon />
                      <span className="text-sm text-gray-600">Generating...</span>
                    </div>
                  </div>
                </div>
              )}
              <div ref={messagesEndRef} />
            </>
          ) 
          : (
            <div className="text-center">
              <h2 className="text-2xl sm:text-3xl font-semibold text-gray-400">CORE-AI</h2>
            </div>
          )
        }
      </div>

      {/* Input Area Wrapper */}
      <div
        ref={dropZoneRef}
        className={`w-full max-w-2xl lg:max-w-3xl mx-auto flex flex-col transition-all duration-300 ease-in-out px-2 md:px-3
                    ${messages.length === 0 
                        ? 'bg-white rounded-2xl border border-gray-300 my-auto shadow-xl mb-6 sm:mb-8 hover:shadow-lg p-2' 
                        : 'bg-white rounded-xl border border-gray-300 shadow-md py-2 hover:shadow-lg' 
                    }
                    ${isDragging ? 'border-indigo-500 bg-indigo-50' : ''}`}
      >
        {renderAttachments()}
        {renderInputBarContent(messages.length === 0)}
        <input
          type="file"
          multiple
          className="hidden"
          onChange={onFileSelect}
          ref={fileInputRef}
        />
      </div>
    </main>
  );
} 