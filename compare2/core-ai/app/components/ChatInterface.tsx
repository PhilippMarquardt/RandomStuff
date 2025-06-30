"use client"

import React, { useState, useEffect, useRef, useCallback } from 'react';
import ChatWindow from './ChatWindow';
import SettingsSidebar from './SettingsSidebar';
import { ChatSidebar } from './sidebar/ChatSidebar';
import { 
  chatService,
  uploadService,
  fileService,
  toolService,
  type ChatMessage,
  type Tool
} from '../api';
import type { ChatSession, FileAttachment } from '../types';

export default function ChatInterface() {
  const [chats, setChats] = useState<ChatSession[]>([]);
  const [activeChatId, setActiveChatId] = useState<string | null>(null);
  const [inputValue, setInputValue] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [isSettingsCollapsed, setIsSettingsCollapsed] = useState(true);
  const [temperature, setTemperature] = useState(0.1);
  const [searchQuery, setSearchQuery] = useState('');
  const [tools, setTools] = useState<Tool[]>([]);
  const [systemPrompt, setSystemPrompt] = useState(`You are a helpful assistant. VISUALIZATION CAPABILITIES: Use <START_FIGURE> and <END_FIGURE> markers to create interactive visualizations: <START_FIGURE>{"type": "table", "data": {"Document": ["Doc A", "Doc B"], "Metric": [100, 120], "Change": ["+5%", "+12%"]}}<END_FIGURE> <START_FIGURE>{"type": "line", "data": [{"x": ["Q1", "Q2", "Q3"], "y": [10, 15, 12], "name": "Portfolio A"}, {"x": ["Q1", "Q2", "Q3"], "y": [8, 14, 16], "name": "Portfolio B"}], "layout": {"title": "Performance Comparison", "xaxis": {"title": "Quarter"}, "yaxis": {"title": "Returns (%)"}}}<END_FIGURE> <START_FIGURE>{"type": "bar", "data": {"x": ["Asset A", "Asset B", "Asset C"], "y": [25, 30, 15], "name": "Allocation %"}, "layout": {"title": "Asset Allocation Comparison"}}<END_FIGURE> <START_FIGURE>{"type": "pie", "data": {"labels": ["Stocks", "Bonds", "Real Estate", "Cash"], "values": [60, 25, 10, 5]}, "layout": {"title": "Portfolio Composition"}}<END_FIGURE> <START_FIGURE>{"type": "scatter", "data": {"x": [5, 8, 12, 15], "y": [3, 7, 9, 12], "mode": "markers", "name": "Risk vs Return"}, "layout": {"title": "Risk-Return Analysis", "xaxis": {"title": "Risk (%)"}, "yaxis": {"title": "Return (%)"}}}<END_FIGURE> <START_FIGURE>{"type": "heatmap", "data": {"z": [[1, 0.8, 0.3], [0.8, 1, 0.5], [0.3, 0.5, 1]], "x": ["Stock A", "Stock B", "Stock C"], "y": ["Stock A", "Stock B", "Stock C"]}, "layout": {"title": "Asset Correlation Matrix"}}<END_FIGURE> <START_FIGURE>{"type": "box", "data": {"y": [2, 4, 6, 8, 10, 12, 15], "name": "Return Distribution"}, "layout": {"title": "Return Distribution Analysis"}}<END_FIGURE> <START_FIGURE>{"type": "bubble", "data": {"x": [10, 15, 20], "y": [5, 8, 12], "size": [20, 30, 40], "name": "Performance Metrics"}, "layout": {"title": "Multi-Factor Analysis"}}<END_FIGURE>`);
  const [attachments, setAttachments] = useState<FileAttachment[]>([]);
  const [availableModels, setAvailableModels] = useState<string[]>([]);
  const [selectedModel, setSelectedModel] = useState<string>('');
  const [isDragging, setIsDragging] = useState(false);
  const [recentUploads, setRecentUploads] = useState<FileAttachment[]>([]);
  const [collections, setCollections] = useState<string[]>(['default']);
  const [selectedCollection, setSelectedCollection] = useState<string>('default');
  const fileInputRef = useRef<HTMLInputElement>(null!);
  const dropZoneRef = useRef<HTMLDivElement>(null!);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Function to fetch available models from the backend
  const fetchModels = useCallback(async () => {
    const models = await chatService.fetchModels();
    setAvailableModels(models);
    if (models.length > 0) {
      // Set default model from localStorage or the first one from the list
      const savedModel = localStorage.getItem('selectedModel');
      if (savedModel && models.includes(savedModel)) {
        setSelectedModel(savedModel);
      } else {
        setSelectedModel(models[0]);
      }
    }
  }, []);

  // Function to fetch available tools from the backend
  const fetchTools = useCallback(async () => {
    const tools = await toolService.fetchTools();
    setTools(tools);
  }, []);

  // Function to fetch collections from the backend
  const fetchCollections = useCallback(async () => {
    const data = await uploadService.fetchCollections();
        setCollections(data);
        // If current selected collection doesn't exist in the list, reset to default
        if (!data.includes(selectedCollection)) {
          setSelectedCollection(data.includes('default') ? 'default' : data[0] || 'default');
    }
  }, [selectedCollection]);

  const handleNewChat = useCallback((isInitialChat = false) => {
    const newChatId = Date.now().toString();
    setChats(prevChats => {
      const newChatName = isInitialChat ? "New Chat" : `Chat ${prevChats.length + 1}`;
      const newChat: ChatSession = {
        id: newChatId,
        name: newChatName,
        messages: [],
      };
      return [newChat, ...prevChats];
    });
    setActiveChatId(newChatId);
    setInputValue('');
    setAttachments([]);
    setSelectedCollection('default');
    fetchModels();
    fetchTools();
  }, [fetchModels, fetchTools]);

  // Add animation styles via useEffect to avoid SSR issues
  useEffect(() => {
    const style = document.createElement('style');
    style.textContent = `
    @keyframes fadeIn {
      from { opacity: 0; }
      to { opacity: 1; }
    }

    @keyframes fadeSlideIn {
      from { 
        opacity: 0;
        transform: translateY(10px);
      }
      to { 
        opacity: 1;
        transform: translateY(0);
      }
    }

    .animate-fadeIn {
      animation: fadeIn 0.3s ease-out forwards;
    }

    .animate-fadeSlideIn {
      animation: fadeSlideIn 0.4s ease-out forwards;
    }
    `;
    document.head.appendChild(style);

    // Clean up on component unmount
    return () => {
      if (style.parentNode) {
        style.parentNode.removeChild(style);
      }
    };
  }, []);

  // Load models, collections, and tools on mount
  useEffect(() => {
    fetchModels();
    fetchCollections();
    fetchTools();
  }, [fetchModels, fetchCollections, fetchTools]);

  useEffect(() => {
    const savedChats = localStorage.getItem('chatSessions');
    if (savedChats) {
      const parsedChats = JSON.parse(savedChats);
      setChats(parsedChats);
      if (parsedChats.length > 0) {
        setActiveChatId(localStorage.getItem('activeChatId') || parsedChats[0].id);
      } else {
        // If localStorage has an empty array, create a new chat
        handleNewChat(true);
      }
    } else {
      // If nothing in localStorage, create an initial chat
      handleNewChat(true); // Pass true to indicate it's the very first chat
    }
    const savedTemp = localStorage.getItem('modelTemperature');
    if (savedTemp) {
      setTemperature(parseFloat(savedTemp));
    }
  }, [handleNewChat]);

  // Load tools on mount
  useEffect(() => {
    fetchTools();
  }, []);

  useEffect(() => {
    if (chats.length > 0) {
      localStorage.setItem('chatSessions', JSON.stringify(chats));
    }
    if (activeChatId) {
      localStorage.setItem('activeChatId', activeChatId);
    }
    localStorage.setItem('modelTemperature', temperature.toString());
    if (selectedModel) {
      localStorage.setItem('selectedModel', selectedModel);
    }
  }, [chats, activeChatId, temperature, selectedModel]);

  const handleSwitchChat = (chatId: string) => {
    setActiveChatId(chatId);
    setInputValue('');
  };

  const activeChat = chats.find(chat => chat.id === activeChatId);
  const currentMessages = activeChat?.messages || [];
  
  // Scroll to bottom when messages change
  useEffect(() => {
    if (messagesEndRef.current) {
      messagesEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [currentMessages.length]);

  // Handle file selection
  const handleFileSelect = (event: React.ChangeEvent<HTMLInputElement>) => {
    const files = event.target.files;
    if (files && files.length > 0) {
      addFiles(files);
    }
  };

  // Add files to attachments
  const addFiles = (files: FileList) => {
    const newAttachments: FileAttachment[] = [];
    
    Array.from(files).forEach(file => {
      const id = Date.now().toString() + Math.random().toString(36).substr(2, 9);
      const attachment: FileAttachment = { id, file };
      
      // Create preview for images
      if (file.type.startsWith('image/')) {
        const reader = new FileReader();
        reader.onload = (e) => {
          if (e.target?.result) {
            setAttachments(prev => 
              prev.map(a => a.id === id ? { ...a, preview: e.target!.result as string } : a)
            );
          }
        };
        reader.readAsDataURL(file);
      }
      
      newAttachments.push(attachment);
    });
    
    setAttachments(prev => [...prev, ...newAttachments]);
  };

  // Remove a file from attachments
  const handleRemoveFile = (id: string) => {
    setAttachments(prev => prev.filter(attachment => attachment.id !== id));
  };

  // Set up drag and drop handlers
  useEffect(() => {
    const dropZone = dropZoneRef.current;
    
    if (!dropZone) return;
    
    const handleDragOver = (e: DragEvent) => {
      e.preventDefault();
      setIsDragging(true);
    };
    
    const handleDragLeave = (e: DragEvent) => {
      e.preventDefault();
      setIsDragging(false);
    };
    
    const handleDrop = (e: DragEvent) => {
      e.preventDefault();
      setIsDragging(false);
      
      if (e.dataTransfer?.files) {
        addFiles(e.dataTransfer.files);
      }
    };
    
    dropZone.addEventListener('dragover', handleDragOver);
    dropZone.addEventListener('dragleave', handleDragLeave);
    dropZone.addEventListener('drop', handleDrop);
    
    return () => {
      dropZone.removeEventListener('dragover', handleDragOver);
      dropZone.removeEventListener('dragleave', handleDragLeave);
      dropZone.removeEventListener('drop', handleDrop);
    };
  }, [dropZoneRef]);

  // Function to search documents in the selected collection
  const searchDocuments = async (query: string, collectionName: string): Promise<string> => {
    return await chatService.searchDocuments(query, collectionName);
  };

  // Enhanced send message function to handle attachments
  const handleSendMessage = async () => {
    if ((inputValue.trim() !== '' || attachments.length > 0) && activeChatId && activeChat) {
      // Create message text that includes attachment filenames for display
      let messageText = inputValue.trim();
      
      // Add attachments to recent uploads
      if (attachments.length > 0) {
        setRecentUploads(prev => [...attachments, ...prev].slice(0, 5));
        
        // Add attachment names to the displayed message
        const attachmentText = attachments.map(a => `[Attached: ${a.file.name}]`).join(' ');
        if (messageText) {
          messageText += '\n' + attachmentText;
        } else {
          messageText = attachmentText;
        }
      }
      
      // Create attachment metadata for the message
      const messageAttachments = attachments.map(a => ({
        filename: a.file.name,
        content_type: a.file.type,
        size: a.file.size
      }));
      
      const userMessage: ChatMessage = { 
        text: messageText, 
        sender: 'user',
        attachments: messageAttachments.length > 0 ? messageAttachments : undefined
      };
      const currentInput = inputValue.trim(); // Store original input without attachment text
      setInputValue(''); // Clear input immediately for better UX
      
      // Process file attachments for backend
      const fileAttachments = [];
      for (const attachment of attachments) {
        try {
          const result = await fileService.convertFile(attachment.file);
          fileAttachments.push({
            filename: attachment.file.name,
            content: result.text,
            content_type: 'text/plain' // After conversion, the content is always text
          });
        } catch (error) {
          console.error(`Error processing file ${attachment.file.name}:`, error);
        }
      }
      
      // Don't clear attachments automatically - let user decide when to remove them

      // Optimistically update UI with user message
      setChats(prevChats =>
        prevChats.map(chat =>
          chat.id === activeChatId
            ? { ...chat, messages: [...chat.messages, userMessage] }
            : chat
        )
      );
      
      setIsLoading(true);
      // Search for relevant documents in the selected collection if not default
      let contextualMessage = currentInput;
      if (selectedCollection !== 'default' && collections.includes(selectedCollection)) {
        const documentContext = await searchDocuments(currentInput, selectedCollection);
        if (documentContext) {
          contextualMessage = `Context from collection "${selectedCollection}":\n\n${documentContext}\n\nUser Question: ${currentInput}`;
        }
      }
      
      // Prepare history: take all messages from the current active chat *before* adding the new user message.
      // The backend will add the current userMessage to its langchain_messages list.
      const historyForBackend = activeChat.messages.map(msg => ({ sender: msg.sender as "user" | "llm", text: msg.text }));

      // Prepare enabled tools list
      const enabledTools = tools.filter(tool => tool.enabled).map(tool => tool.name);

      try {
        const data = await chatService.sendMessage({
          text: contextualMessage,
          temperature, 
          model_name: selectedModel,
          history: historyForBackend,
          enabledTools: enabledTools,
          systemPrompt: systemPrompt,
          attachments: fileAttachments.length > 0 ? fileAttachments : undefined
        });
        
        const llmResponse: ChatMessage = { text: data.text, sender: 'llm' };
        
        // Update UI with LLM response
        setChats(prevChats =>
          prevChats.map(chat =>
            chat.id === activeChatId
              ? { ...chat, messages: [...chat.messages, llmResponse] }
              : chat
          )
        );

      } catch (error) {
        console.error("Error sending message to backend:", error);
        const errorMessageText = error instanceof Error ? error.message : 'Could not connect to LLM service.';
        // Check if an error message for this exact failure is already the last message
        const lastMessage = activeChat.messages[activeChat.messages.length -1];
        if(!(lastMessage && lastMessage.sender === 'llm' && lastMessage.text.includes(errorMessageText))){
            const errorMessage: ChatMessage = {
              text: `Error: ${errorMessageText}`,
              sender: 'llm',
            };
            setChats(prevChats =>
              prevChats.map(chat =>
                chat.id === activeChatId
                  ? { ...chat, messages: [...chat.messages, errorMessage] }
                  : chat
              )
            );
        }
      } finally {
        setIsLoading(false);
      }
    }
  };

  const handleToggleTool = (toolName: string) => {
    setTools(prevTools =>
      prevTools.map(tool =>
        tool.name === toolName ? { ...tool, enabled: !tool.enabled } : tool
      )
    );
  };

  return (
    <>
      {/* Sidebar */}
      <ChatSidebar
        searchQuery={searchQuery}
        onSearchQueryChange={setSearchQuery}
        onNewChat={() => handleNewChat()}
        chats={chats}
        activeChatId={activeChatId}
        onSwitchChat={handleSwitchChat}
      />

      {/* Main Chat Area */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {/* Navigation Bar */}
        <nav className="w-full bg-white backdrop-blur-sm border-b border-gray-200 shadow-sm">
          <div className="container mx-auto px-6 py-4 flex justify-between items-center">
            <div className="flex items-center">
              <h1 className="text-xl font-bold text-gray-800 tracking-tight uppercase">CORE-AI</h1>
            </div>
            <div className="flex items-center space-x-3">
              {activeChat && (
                <div className="flex items-center space-x-2">
                  {selectedCollection !== 'default' && (
                    <div className="flex items-center px-2 py-1 bg-indigo-50 border border-indigo-200 rounded-md">
                      <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" className="w-3 h-3 mr-1 text-indigo-500">
                        <path fillRule="evenodd" d="M3.75 3A1.75 1.75 0 002 4.75v2.5C2 8.216 2.784 9 3.75 9h2.5A1.75 1.75 0 008 7.25v-2.5C8 3.784 7.216 3 6.25 3h-2.5zM3.5 4.75a.25.25 0 01.25-.25h2.5a.25.25 0 01.25.25v2.5a.25.25 0 01-.25.25h-2.5a.25.25 0 01-.25-.25v-2.5zM11.75 3A1.75 1.75 0 0010 4.75v2.5c0 .966.784 1.75 1.75 1.75h2.5A1.75 1.75 0 0016 7.25v-2.5C16 3.784 15.216 3 14.25 3h-2.5zm-.25 1.75a.25.25 0 01.25-.25h2.5a.25.25 0 01.25.25v2.5a.25.25 0 01-.25.25h-2.5a.25.25 0 01-.25-.25v-2.5zM3.75 11A1.75 1.75 0 002 12.75v2.5c0 .966.784 1.75 1.75 1.75h2.5A1.75 1.75 0 008 15.25v-2.5C8 11.784 7.216 11 6.25 11h-2.5zm-.25 1.75a.25.25 0 01.25-.25h2.5a.25.25 0 01.25.25v2.5a.25.25 0 01-.25.25h-2.5a.25.25 0 01-.25-.25v-2.5z" clipRule="evenodd" />
                      </svg>
                      <span className="text-xs text-indigo-700 font-medium">{selectedCollection}</span>
                    </div>
                  )}
                  <span className="text-sm text-gray-500 font-medium">{activeChat.name}</span>
                </div>
              )}
            </div>
          </div>
        </nav>

        {activeChatId ? (
          <ChatWindow
            messages={currentMessages}
            inputValue={inputValue}
            setInputValue={setInputValue}
            attachments={attachments}
            setAttachments={setAttachments}
            selectedCollection={selectedCollection}
            onSendMessage={handleSendMessage}
            onFileSelect={handleFileSelect}
            onRemoveFile={handleRemoveFile}
            isDragging={isDragging}
            dropZoneRef={dropZoneRef}
            fileInputRef={fileInputRef}
            isLoading={isLoading}
          />
        ) : (
          <main className="flex-1 flex items-center justify-center">
            <p className="text-gray-500 text-lg">Select a chat or start a new one.</p>
          </main>
        )}
      </div>
      {activeChatId && (
        <SettingsSidebar
          isCollapsed={isSettingsCollapsed}
          setIsCollapsed={setIsSettingsCollapsed}
          temperature={temperature}
          setTemperature={setTemperature}
          systemPrompt={systemPrompt}
          setSystemPrompt={setSystemPrompt}
          tools={tools}
          models={availableModels}
          selectedModel={selectedModel}
          setSelectedModel={setSelectedModel}
          collections={collections}
          selectedCollection={selectedCollection}
          setSelectedCollection={setSelectedCollection}
          attachments={attachments}
          recentUploads={recentUploads}
          isDragging={isDragging}
          dropZoneRef={dropZoneRef}
          fileInputRef={fileInputRef}
          onFileSelect={handleFileSelect}
          onRemoveFile={handleRemoveFile}
          onToggleTool={handleToggleTool}
          onFetchTools={fetchTools}
          onFetchCollections={fetchCollections}
        />
      )}
    </>
  );
} 