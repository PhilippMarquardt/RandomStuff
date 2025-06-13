"use client"

import React, { useRef } from 'react';

// Icons
const PaperClipIcon = () => (
  <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" className="w-5 h-5 text-gray-500">
    <path fillRule="evenodd" d="M15.621 4.379a3 3 0 00-4.242 0l-7 7a3 3 0 004.241 4.243h.001l.497-.5a.75.75 0 011.064 1.057l-.498.501-.002.002a4.5 4.5 0 01-6.364-6.364l7-7a4.5 4.5 0 016.368 6.36l-3.455 3.553A2.625 2.625 0 119.52 9.52l3.45-3.451a.75.75 0 111.061 1.06l-3.45 3.451a1.125 1.125 0 001.587 1.595l3.454-3.553a3 3 0 000-4.242z" clipRule="evenodd" />
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
type Tool = {
  name: string;
  description: string;
  enabled: boolean;
};

type FileAttachment = {
  id: string;
  file: File;
  preview?: string;
};

interface SettingsSidebarProps {
  isCollapsed: boolean;
  setIsCollapsed: (value: boolean) => void;
  temperature: number;
  setTemperature: (value: number) => void;
  systemPrompt: string;
  setSystemPrompt: (value: string) => void;
  tools: Tool[];
  setTools: React.Dispatch<React.SetStateAction<Tool[]>>;
  collections: string[];
  selectedCollection: string;
  setSelectedCollection: (value: string) => void;
  attachments: FileAttachment[];
  setAttachments: React.Dispatch<React.SetStateAction<FileAttachment[]>>;
  recentUploads: FileAttachment[];
  isDragging: boolean;
  dropZoneRef: React.RefObject<HTMLDivElement>;
  fileInputRef: React.RefObject<HTMLInputElement>;
  onFileSelect: (event: React.ChangeEvent<HTMLInputElement>) => void;
  onRemoveFile: (id: string) => void;
  onToggleTool: (toolName: string) => void;
  onFetchTools: () => void;
  onFetchCollections: () => void;
}

export default function SettingsSidebar({
  isCollapsed,
  setIsCollapsed,
  temperature,
  setTemperature,
  systemPrompt,
  setSystemPrompt,
  tools,
  setTools,
  collections,
  selectedCollection,
  setSelectedCollection,
  attachments,
  setAttachments,
  recentUploads,
  isDragging,
  dropZoneRef,
  fileInputRef,
  onFileSelect,
  onRemoveFile,
  onToggleTool,
  onFetchTools,
  onFetchCollections
}: SettingsSidebarProps) {
  const [isToolsCollapsed, setIsToolsCollapsed] = React.useState(false);
  const [isCollectionsCollapsed, setIsCollectionsCollapsed] = React.useState(false);

  const handleTemperatureChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    setTemperature(parseFloat(event.target.value));
  };

  return (
    <div className={`bg-white shadow-lg border-l border-gray-200 transition-all duration-300 ease-in-out overflow-y-auto ${isCollapsed ? 'w-16' : 'w-80'}`}>
      <div className="p-4 border-b border-gray-200">
        <div className="flex justify-between items-center">
          {!isCollapsed && <h2 className="text-lg font-semibold text-gray-800">Settings</h2>}
          <button 
            onClick={() => setIsCollapsed(!isCollapsed)}
            className="p-1 rounded-full hover:bg-gray-100 transition-colors"
          >
            <svg xmlns="http://www.w3.org/2000/svg" className="h-6 w-6 text-gray-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              {isCollapsed ? (
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
              ) : (
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              )}
            </svg>
          </button>
        </div>
      </div>

      {!isCollapsed && (
        <>
          {/* Model Settings */}
          <div className="p-4 border-b border-gray-200">
            <h3 className="text-md font-medium text-gray-700 mb-3">Model Settings</h3>
            <label htmlFor="temperature" className="block text-sm font-medium text-gray-700 mb-1">
              Temperature: <span className="font-semibold text-gray-900">{temperature.toFixed(2)}</span>
            </label>
            <input
              type="range"
              id="temperature"
              name="temperature"
              min="0"
              max="1"
              step="0.01"
              value={temperature}
              onChange={handleTemperatureChange}
              className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer accent-indigo-600 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:ring-offset-2 focus:ring-offset-white"
            />
          </div>

          {/* System Prompt Section */}
          <div className="p-4 border-b border-gray-200">
            <h3 className="text-md font-medium text-gray-700 mb-3">System Prompt</h3>
            <textarea
              value={systemPrompt}
              onChange={(e) => setSystemPrompt(e.target.value)}
              placeholder="e.g., You are a helpful assistant."
              className="w-full p-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
              rows={4}
            />
          </div>

          {/* Tools Section */}
          <div className="p-4 border-b border-gray-200">
            <div className="flex justify-between items-center mb-3">
              <h3 className="text-md font-medium text-gray-700">Available Tools</h3>
              <div className="flex items-center space-x-2">
                <button
                  onClick={onFetchTools}
                  className="text-xs px-2 py-1 bg-blue-50 hover:bg-blue-100 text-blue-600 rounded transition-colors"
                  title="Refresh tool list"
                >
                  Refresh
                </button>
                <button onClick={() => setIsToolsCollapsed(!isToolsCollapsed)}>
                  <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    {isToolsCollapsed ? <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" /> : <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 15l7-7 7 7" />}
                  </svg>
                </button>
              </div>
            </div>
            {!isToolsCollapsed && (
              <div className="space-y-2">
                {tools.map(tool => (
                  <div key={tool.name} className="flex items-center justify-between bg-gray-50 p-2 rounded-lg">
                    <div>
                      <div className="text-sm font-medium text-gray-800">{tool.name}</div>
                      <p className="text-xs text-gray-500">{tool.description}</p>
                    </div>
                    <label className="relative inline-flex items-center cursor-pointer">
                      <input
                        type="checkbox"
                        className="sr-only peer"
                        checked={tool.enabled}
                        onChange={() => onToggleTool(tool.name)}
                      />
                      <div className="w-9 h-5 bg-gray-200 peer-focus:outline-none peer-focus:ring-2 peer-focus:ring-indigo-300 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-4 after:w-4 after:transition-all peer-checked:bg-indigo-600"></div>
                    </label>
                  </div>
                ))}
                {tools.length === 0 && (
                  <div className="text-center py-4 text-gray-500">
                    <div className="text-sm">Loading tools...</div>
                  </div>
                )}
              </div>
            )}
          </div>

          {/* Document Collections Section */}
          <div className="p-4 border-b border-gray-200">
            <div className="flex justify-between items-center mb-3">
              <h3 className="text-md font-medium text-gray-700">Document Collections</h3>
              <div className="flex items-center space-x-2">
                <button
                  onClick={onFetchCollections}
                  className="text-xs px-2 py-1 bg-green-50 hover:bg-green-100 text-green-600 rounded transition-colors"
                  title="Refresh collections"
                >
                  Refresh
                </button>
                <button onClick={() => setIsCollectionsCollapsed(!isCollectionsCollapsed)}>
                  <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    {isCollectionsCollapsed ? <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" /> : <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 15l7-7 7 7" />}
                  </svg>
                </button>
              </div>
            </div>
            {!isCollectionsCollapsed && (
              <div className="space-y-2">
                {collections.map((collection) => (
                  <button
                    key={collection}
                    onClick={() => setSelectedCollection(collection)}
                    className={`w-full text-left px-3 py-2 text-sm rounded-lg transition-colors flex items-center justify-between border ${selectedCollection === collection
                        ? 'bg-indigo-50 text-indigo-700 font-medium border-indigo-200'
                        : 'text-gray-700 hover:bg-gray-50 border-gray-200'
                      }`}
                  >
                    <div className="flex items-center">
                      <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" className="w-4 h-4 mr-2 text-indigo-500">
                        <path fillRule="evenodd" d="M3.75 3A1.75 1.75 0 002 4.75v2.5C2 8.216 2.784 9 3.75 9h2.5A1.75 1.75 0 008 7.25v-2.5C8 3.784 7.216 3 6.25 3h-2.5zM3.5 4.75a.25.25 0 01.25-.25h2.5a.25.25 0 01.25.25v2.5a.25.25 0 01-.25.25h-2.5a.25.25 0 01-.25-.25v-2.5zM11.75 3A1.75 1.75 0 0010 4.75v2.5c0 .966.784 1.75 1.75 1.75h2.5A1.75 1.75 0 0016 7.25v-2.5C16 3.784 15.216 3 14.25 3h-2.5zm-.25 1.75a.25.25 0 01.25-.25h2.5a.25.25 0 01.25.25v2.5a.25.25 0 01-.25.25h-2.5a.25.25 0 01-.25-.25v-2.5zM3.75 11A1.75 1.75 0 002 12.75v2.5c0 .966.784 1.75 1.75 1.75h2.5A1.75 1.75 0 008 15.25v-2.5C8 11.784 7.216 11 6.25 11h-2.5zm-.25 1.75a.25.25 0 01.25-.25h2.5a.25.25 0 01.25.25v2.5a.25.25 0 01-.25.25h-2.5a.25.25 0 01-.25-.25v-2.5z" clipRule="evenodd" />
                      </svg>
                      <span className="truncate">{collection}</span>
                    </div>
                    {selectedCollection === collection && (
                      <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" className="w-4 h-4 text-indigo-600">
                        <path fillRule="evenodd" d="M16.704 4.153a.75.75 0 01.143 1.052l-8 10.5a.75.75 0 01-1.127.075l-4.25-4.5a.75.75 0 011.06-1.06l3.894 3.893 7.48-9.817a.75.75 0 011.05-.143z" clipRule="evenodd" />
                      </svg>
                    )}
                  </button>
                ))}
                {collections.length === 0 && (
                  <div className="text-center py-4 text-gray-500">
                    <div className="text-sm">No collections found</div>
                  </div>
                )}
              </div>
            )}
          </div>

          {/* Uploads Section */}
          <div className="p-4">
            <h3 className="text-md font-medium text-gray-700 mb-3">File Uploads</h3>

            <div
              ref={dropZoneRef}
              className={`border-2 border-dashed rounded-lg p-4 text-center mb-3 transition-colors
                ${isDragging ? 'border-indigo-500 bg-indigo-50' : 'border-gray-300 hover:border-indigo-400'}`}
            >
              <input
                type="file"
                multiple
                className="hidden"
                onChange={onFileSelect}
                ref={fileInputRef}
              />
              <button
                onClick={() => fileInputRef.current?.click()}
                className="inline-flex items-center px-4 py-2 bg-indigo-50 hover:bg-indigo-100 text-indigo-700 font-medium rounded-md transition-colors"
              >
                <PaperClipIcon />
                <span className="ml-2">Select Files</span>
              </button>
            </div>

            {attachments.length > 0 && (
              <div className="mb-3">
                <h4 className="text-sm font-medium text-gray-600 mb-2">Selected Files</h4>
                <div className="space-y-2">
                  {attachments.map(attachment => (
                    <div
                      key={attachment.id}
                      className="flex items-center justify-between bg-gray-50 p-2 rounded"
                    >
                      <div className="flex items-center">
                        <FileIcon fileType={attachment.file.type} />
                        <span className="ml-2 text-sm text-gray-700 truncate max-w-[180px]">
                          {attachment.file.name}
                        </span>
                      </div>
                      <button 
                        onClick={() => onRemoveFile(attachment.id)}
                        className="text-gray-400 hover:text-gray-600"
                      >
                        <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                        </svg>
                      </button>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {recentUploads.length > 0 && (
              <div>
                <h4 className="text-sm font-medium text-gray-600 mb-2">Recent</h4>
                <div className="flex flex-wrap gap-2">
                  {recentUploads.map(upload => (
                    <div
                      key={upload.id}
                      className="flex items-center bg-gray-50 px-2 py-1 rounded text-xs"
                    >
                      <FileIcon fileType={upload.file.type} />
                      <span className="ml-1 truncate max-w-[100px]">{upload.file.name}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        </>
      )}
    </div>
  );
} 