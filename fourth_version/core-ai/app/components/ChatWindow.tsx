"use client"

/**
 * ChatWindow Component with Table Rendering Support
 * 
 * This component supports rendering JSON tables in chat messages from LLM responses.
 * The LLM can send table data in the following JSON format, and it will be automatically
 * rendered as a proper HTML table:
 * 
 * Format:
 * {
 *   "type": "table",
 *   "data": {
 *     "Column 1": ["row1_col1", "row2_col1", "row3_col1"],
 *     "Column 2": ["row1_col2", "row2_col2", "row3_col2"],
 *     "Column 3": ["row1_col3", "row2_col3", "row3_col3"]
 *   }
 * }
 * 
 * The JSON can be:
 * - Wrapped in markdown code blocks (```json ... ```)
 * - Wrapped in plain code blocks (``` ... ```)
 * - Raw JSON in the message text
 * 
 * Example usage in LLM response:
 * "Here's the comparison data:
 * 
 * ```json
 * {
 *   "type": "table",
 *   "data": {
 *     "Document": ["Doc A", "Doc B", "Doc C"],
 *     "Pages": [10, 15, 8],
 *     "Status": ["Complete", "In Progress", "Complete"]
 *   }
 * }
 * ```
 * 
 * This will render a properly formatted table with hover effects, proper styling,
 * and responsive design."
 */

import React, { useRef, useEffect, useState } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import rehypeHighlight from 'rehype-highlight';
import 'highlight.js/styles/github.css';

// Icons
const SendIcon = () => (
  <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" className="w-5 h-5 transition-transform duration-200 group-hover:translate-x-0.5">
    <path d="M3.105 3.105a.75.75 0 01.814-.102l14.25 5.25a.75.75 0 010 1.392l-14.25 5.25a.75.75 0 01-.912-.99L4.839 10 2.99 3.997a.75.75 0 01.114-.892z" />
  </svg>
);

const CopyIcon = () => (
  <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect>
    <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path>
  </svg>
);

const CheckIcon = () => (
  <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <polyline points="20 6 9 17 4 12"></polyline>
  </svg>
);

const LoadingIcon = () => (
  <svg className="animate-spin h-5 w-5 text-indigo-500" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
  </svg>
);

const FileIcon = ({ fileType }: { fileType: string }) => {
  if (fileType.startsWith('image/')) {
    return (
      <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" className="w-5 h-5 text-indigo-500">
        <path fillRule="evenodd" d="M1 5.25A2.25 2.25 0 013.25 3h13.5A2.25 2.25 0 0119 5.25v9.5A2.25 2.25 0 0116.75 17H3.25A2.25 2.25 0 011 14.75v-9.5zm1.5 5.81v3.69c0 .414.336.75.75.75h13.5a.75.75 0 00.75-.75v-2.69l-2.22-2.219a.75.75 0 00-1.06 0l-1.91 1.909.47.47a.75.75 0 11-1.06 1.06L8.97 10.53a.75.75 0 00-1.06 0l-3.91 3.91V11.06l.5-.5a.75.75 0 000-1.06l-3-3zm2.03.78a.75.75 0 00-.53.22l-1.5 1.5v-3.19c0-.414.336-.75.75-.75h13.5a.75.75 0 01.75.75v2.19l-1.5-1.5a.75.75 0 00-.53-.22h-3v.75a.75.75 0 01-.75.75h-4.5a.75.75 0 01-.75-.75v-.75h-3z" clipRule="evenodd" />
      </svg>
    );
  } else if (fileType === 'application/pdf') {
    return (
      <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" className="w-5 h-5 text-red-500">
        <path fillRule="evenodd" d="M4.5 2A1.5 1.5 0 003 3.5v13A1.5 1.5 0 004.5 18h11a1.5 1.5 0 001.5-1.5V7.621a1.5 1.5 0 00-.44-1.06l-4.12-4.122A1.5 1.5 0 0011.378 2H4.5zm2.25 8.5a.75.75 0 000 1.5h6.5a.75.75 0 000-1.5h-6.5zm0 3a.75.75 0 000 1.5h6.5a.75.75 0 000-1.5h-6.5z" clipRule="evenodd" />
      </svg>
    );
  } else {
    return (
      <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" className="w-5 h-5 text-gray-500">
        <path d="M3 3.75A1.75 1.75 0 014.75 2h10.5c.966 0 1.75.784 1.75 1.75v10.5A1.75 1.75 0 0115.25 16h-1.5a.75.75 0 010-1.5h1.5a.25.25 0 00.25-.25V3.75a.25.25 0 00-.25-.25H4.75a.25.25 0 00-.25.25v10.5c0 .138.112.25.25.25h1.5a.75.75 0 010 1.5h-1.5A1.75 1.75 0 013 14.25V3.75z" />
        <path d="M3.75 6.5a.75.75 0 01.75-.75h7a.75.75 0 010 1.5h-7a.75.75 0 01-.75-.75zM3 10.25a.75.75 0 01.75-.75h7a.75.75 0 010 1.5h-7a.75.75 0 01-.75-.75z" />
      </svg>
    );
  }
};

// Types
type ChatMessage = { 
  text: string; 
  sender: string; 
  attachments?: Array<{
    filename: string;
    content_type: string;
    size: number;
  }>;
};

type FileAttachment = {
  id: string;
  file: File;
  preview?: string;
};

// Add TableData type
type TableData = {
  type: 'table';
  data: { [key: string]: any[] };
};

// TableRenderer component
const TableRenderer = ({ tableData }: { tableData: TableData }) => {
  const columns = Object.keys(tableData.data);
  const rowCount = Math.max(...columns.map(col => tableData.data[col]?.length || 0));
  
  if (columns.length === 0) {
    return <div className="text-red-500 text-sm p-2 bg-red-50 border border-red-200 rounded-md">No table data available</div>;
  }

  // Format cell content to handle different data types
  const formatCellContent = (value: any): string => {
    if (value === null || value === undefined) return '';
    if (typeof value === 'object') return JSON.stringify(value);
    return String(value);
  };

  return (
    <div className="overflow-x-auto my-4 rounded-lg border border-gray-200 shadow-sm">
      <table className="min-w-full">
        <thead>
          <tr className="bg-gradient-to-r from-gray-50 to-gray-100">
            {columns.map((column, index) => (
              <th
                key={index}
                className="px-4 py-3 text-left text-xs font-semibold text-gray-700 uppercase tracking-wider border-b border-gray-300 first:rounded-tl-lg last:rounded-tr-lg"
              >
                {column}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="bg-white divide-y divide-gray-200">
          {Array.from({ length: rowCount }, (_, rowIndex) => (
            <tr 
              key={rowIndex} 
              className={`hover:bg-gray-50 transition-colors duration-150 ${rowIndex % 2 === 0 ? 'bg-white' : 'bg-gray-25'}`}
            >
              {columns.map((column, colIndex) => (
                <td
                  key={colIndex}
                  className="px-4 py-3 text-sm text-gray-900 border-r border-gray-200 last:border-r-0 max-w-xs overflow-hidden"
                >
                  <div className="truncate" title={formatCellContent(tableData.data[column]?.[rowIndex])}>
                    {formatCellContent(tableData.data[column]?.[rowIndex]) || (
                      <span className="text-gray-400 italic">—</span>
                    )}
                  </div>
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
      <div className="px-4 py-2 bg-gray-50 border-t border-gray-200 text-xs text-gray-500 rounded-b-lg">
        {rowCount} row{rowCount !== 1 ? 's' : ''} × {columns.length} column{columns.length !== 1 ? 's' : ''}
      </div>
    </div>
  );
};

// Function to detect and parse JSON table format
const parseJsonTable = (text: string): { isTable: boolean; tableData?: TableData; remainingText?: string } => {
  try {
    // Try to find JSON blocks in the text - improved regex to handle various formats
    const jsonMatches = text.match(/```json\s*([\s\S]*?)\s*```|```\s*([\s\S]*?)\s*```|(\{[\s\S]*?\})/g);
    
    if (!jsonMatches) {
      // Try to parse the entire text as JSON if it starts with { and ends with }
      const trimmedText = text.trim();
      if (trimmedText.startsWith('{') && trimmedText.endsWith('}')) {
        try {
          const parsed = JSON.parse(trimmedText);
          if (parsed.type === 'table' && parsed.data && typeof parsed.data === 'object') {
            return { isTable: true, tableData: parsed };
          }
        } catch (e) {
          // Not valid JSON, continue with normal flow
        }
      }
      return { isTable: false };
    }

    // Check each JSON match
    for (const match of jsonMatches) {
      const jsonContent = match.replace(/```json\s*|\s*```|```\s*|\s*```/g, '').trim();
      try {
        const parsed = JSON.parse(jsonContent);
        if (parsed.type === 'table' && parsed.data && typeof parsed.data === 'object') {
          // Validate that data contains arrays
          const isValidTableData = Object.values(parsed.data).every(value => Array.isArray(value));
          if (isValidTableData) {
            const remainingText = text.replace(match, '').trim();
            return { 
              isTable: true, 
              tableData: parsed, 
              remainingText: remainingText || undefined 
            };
          }
        }
      } catch (e) {
        // Continue to next match if this one fails to parse
        continue;
      }
    }
    
    return { isTable: false };
  } catch (error) {
    return { isTable: false };
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
  setIsDragging: (value: boolean) => void;
  dropZoneRef: React.RefObject<HTMLDivElement>;
  fileInputRef: React.RefObject<HTMLInputElement>;
  isLoading: boolean;
}

function extractText(node: any): string {
  if (node.type === 'text') {
    return node.value;
  }
  if (node.children && Array.isArray(node.children)) {
    return node.children.map(extractText).join('');
  }
  return '';
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
  setIsDragging,
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
          <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" className="w-3 h-3 mr-1 text-indigo-500">
            <path fillRule="evenodd" d="M3.75 3A1.75 1.75 0 002 4.75v2.5C2 8.216 2.784 9 3.75 9h2.5A1.75 1.75 0 008 7.25v-2.5C8 3.784 7.216 3 6.25 3h-2.5zM3.5 4.75a.25.25 0 01.25-.25h2.5a.25.25 0 01.25.25v2.5a.25.25 0 01-.25.25h-2.5a.25.25 0 01-.25-.25v-2.5zM11.75 3A1.75 1.75 0 0010 4.75v2.5c0 .966.784 1.75 1.75 1.75h2.5A1.75 1.75 0 0016 7.25v-2.5C16 3.784 15.216 3 14.25 3h-2.5zm-.25 1.75a.25.25 0 01.25-.25h2.5a.25.25 0 01.25.25v2.5a.25.25 0 01-.25.25h-2.5a.25.25 0 01-.25-.25v-2.5zM3.75 11A1.75 1.75 0 002 12.75v2.5c0 .966.784 1.75 1.75 1.75h2.5A1.75 1.75 0 008 15.25v-2.5C8 11.784 7.216 11 6.25 11h-2.5zm-.25 1.75a.25.25 0 01.25-.25h2.5a.25.25 0 01.25.25v2.5a.25.25 0 01-.25.25h-2.5a.25.25 0 01-.25-.25v-2.5z" clipRule="evenodd" />
          </svg>
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
        key={index}
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
                const tableParseResult = parseJsonTable(message.text);
                
                if (tableParseResult.isTable && tableParseResult.tableData) {
                  return (
                    <div>
                      {tableParseResult.remainingText && (
                        <ReactMarkdown 
                          remarkPlugins={[remarkGfm]} 
                          rehypePlugins={[rehypeHighlight]}
                          components={{
                            pre: ({ node, ...props }) => {
                              const [isCopied, setIsCopied] = useState(false);
                              
                              const codeNode = node?.children[0];
                              const codeString = codeNode ? extractText(codeNode) : '';

                              const handleCopy = () => {
                                if (codeString) {
                                  navigator.clipboard.writeText(codeString).then(() => {
                                    setIsCopied(true);
                                    setTimeout(() => setIsCopied(false), 2000);
                                  });
                                }
                              };

                              return (
                                <div className="relative group">
                                  <pre {...props} />
                                  <button
                                    onClick={handleCopy}
                                    className="absolute top-2 right-2 p-1.5 bg-gray-800 text-white rounded-md opacity-0 group-hover:opacity-100 transition-opacity"
                                  >
                                    {isCopied ? <CheckIcon /> : <CopyIcon />}
                                  </button>
                                </div>
                              );
                            },
                          }}
                        >
                          {tableParseResult.remainingText}
                        </ReactMarkdown>
                      )}
                      <TableRenderer tableData={tableParseResult.tableData} />
                    </div>
                  );
                } else {
                  return (
                    <ReactMarkdown 
                      remarkPlugins={[remarkGfm]} 
                      rehypePlugins={[rehypeHighlight]}
                      components={{
                        pre: ({ node, ...props }) => {
                          const [isCopied, setIsCopied] = useState(false);
                          
                          const codeNode = node?.children[0];
                          const codeString = codeNode ? extractText(codeNode) : '';

                          const handleCopy = () => {
                            if (codeString) {
                              navigator.clipboard.writeText(codeString).then(() => {
                                setIsCopied(true);
                                setTimeout(() => setIsCopied(false), 2000);
                              });
                            }
                          };

                          return (
                            <div className="relative group">
                              <pre {...props} />
                              <button
                                onClick={handleCopy}
                                className="absolute top-2 right-2 p-1.5 bg-gray-800 text-white rounded-md opacity-0 group-hover:opacity-100 transition-opacity"
                              >
                                {isCopied ? <CheckIcon /> : <CopyIcon />}
                              </button>
                            </div>
                          );
                        },
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
                  <div className="mt-3 pt-3 border-t border-indigo-400 border-opacity-30">
                    <div className="text-xs text-indigo-100 mb-2 font-medium">Attached Files:</div>
                    <div className="flex flex-wrap gap-2">
                      {message.attachments.map((attachment, attachIndex) => (
                        <div 
                          key={attachIndex}
                          className="flex items-center bg-indigo-500 bg-opacity-50 border border-indigo-400 border-opacity-30 rounded-md px-2 py-1"
                        >
                          <FileIcon fileType={attachment.content_type} />
                          <div className="ml-1 flex flex-col">
                            <span className="text-xs text-white font-medium">
                              {attachment.filename}
                            </span>
                            <span className="text-xs text-indigo-100">
                              {Math.round(attachment.size / 1024)}KB
                            </span>
                          </div>
                        </div>
                      ))}
                    </div>
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
            <svg xmlns="http://www.w3.org/2000/svg" className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
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