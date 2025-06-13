"use client"

import React, { useState, useEffect, useRef } from 'react';
import { useRouter } from 'next/navigation';
import ChatWindow from './components/ChatWindow';
import SettingsSidebar from './components/SettingsSidebar';
import { 
  fetchCollections as fetchCollectionsAPI, 
  searchDocuments as searchDocumentsAPI,
  fetchTools as fetchToolsAPI,
  sendMessage,
  convertFile
} from './api';

// Icons needed for the sidebar

const PlusIcon = () => (
  <svg className="w-5 h-5 mr-2.5" fill="none" strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" viewBox="0 0 24 24" stroke="currentColor">
    <path d="M12 6v6m0 0v6m0-6h6m-6 0H6"></path>
  </svg>
);

const UploadCloudIcon = () => (
  <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="w-5 h-5 mr-2.5">
    <path d="M14.5 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7.5L14.5 2z"/>
    <polyline points="14,2 14,8 20,8"/>
    <line x1="12" y1="18" x2="12" y2="12"/>
    <line x1="9" y1="15" x2="12" y2="12"/>
    <line x1="15" y1="15" x2="12" y2="12"/>
  </svg>
);

const ServicesIcon = () => (
  <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="w-5 h-5 mr-2.5">
    <rect x="3" y="3" width="7" height="7" />
    <rect x="14" y="3" width="7" height="7" />
    <rect x="14" y="14" width="7" height="7" />
    <rect x="3" y="14" width="7" height="7" />
  </svg>
);



const ChatBubbleIcon = () => (
  <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" className="w-4 h-4 mr-2 text-indigo-400">
    <path fillRule="evenodd" d="M10 2c-2.236 0-4.43.18-6.57.524C1.993 2.755 1 4.014 1 5.426v5.148c0 1.413.993 2.67 2.43 2.902 1.168.188 2.352.327 3.55.414.28.02.521.18.642.413l1.713 3.293a.75.75 0 001.33 0l1.713-3.293a.783.783 0 01.642-.413 41.102 41.102 0 003.55-.414c1.437-.231 2.43-1.49 2.43-2.902V5.426c0-1.413-.993-2.67-2.43-2.902A41.289 41.289 0 0010 2zM6.75 6a.75.75 0 000 1.5h6.5a.75.75 0 000-1.5h-6.5zm0 2.5a.75.75 0 000 1.5h3.5a.75.75 0 000-1.5h-3.5z" clipRule="evenodd"/>
  </svg>
);

const SearchIcon = () => (
  <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" className="w-5 h-5 text-gray-400 absolute left-3 top-1/2 transform -translate-y-1/2">
    <path fillRule="evenodd" d="M9 3.5a5.5 5.5 0 100 11 5.5 5.5 0 000-11zM2 9a7 7 0 1112.452 4.391l3.328 3.329a.75.75 0 11-1.06 1.06l-3.329-3.328A7 7 0 012 9z" clipRule="evenodd" />
  </svg>
);





import type { ChatMessage, Tool } from './api';

// Type definitions
type ChatSession = {
  id: string;
  name: string;
  messages: ChatMessage[];
};

interface ChatMessageResponse { 
  text: string;
  error?: string | null;
}

// Type for file attachment
type FileAttachment = {
  id: string;
  file: File;
  preview?: string;
};



export default function ChatPage() {
  const [chats, setChats] = useState<ChatSession[]>([]);
  const [activeChatId, setActiveChatId] = useState<string | null>(null);
  const [inputValue, setInputValue] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [isSettingsCollapsed, setIsSettingsCollapsed] = useState(true);
  const [isToolsCollapsed, setIsToolsCollapsed] = useState(true);
  const [isCollectionsCollapsed, setIsCollectionsCollapsed] = useState(true);
  const [temperature, setTemperature] = useState(0.7);
  const [searchQuery, setSearchQuery] = useState('');
  const [tools, setTools] = useState<Tool[]>([]);
  const [systemPrompt, setSystemPrompt] = useState("You are a helpful assistant.");
  const [attachments, setAttachments] = useState<FileAttachment[]>([]);
  const [isDragging, setIsDragging] = useState(false);
  const [recentUploads, setRecentUploads] = useState<FileAttachment[]>([]);
  const [collections, setCollections] = useState<string[]>(['default']);
  const [selectedCollection, setSelectedCollection] = useState<string>('default');
  const [showCollectionDropdown, setShowCollectionDropdown] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null!);
  const dropZoneRef = useRef<HTMLDivElement>(null!);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const collectionDropdownRef = useRef<HTMLDivElement>(null);
  const router = useRouter();

  // Function to fetch collections from the backend
  const fetchCollections = async () => {
    const data = await fetchCollectionsAPI();
        setCollections(data);
        // If current selected collection doesn't exist in the list, reset to default
        if (!data.includes(selectedCollection)) {
          setSelectedCollection(data.includes('default') ? 'default' : data[0] || 'default');
    }
  };

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

  // Close settings popover if clicked outside
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      // Close collection dropdown if clicked outside
      if (collectionDropdownRef.current && 
          !collectionDropdownRef.current.contains(event.target as Node)) {
        setShowCollectionDropdown(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
    };
  }, [collectionDropdownRef]);

  // Load collections on mount
  useEffect(() => {
    fetchCollections();
  }, []);

  useEffect(() => {
    const savedChats = localStorage.getItem('chatSessions');
    if (savedChats) {
      const parsedChats = JSON.parse(savedChats);
      setChats(parsedChats);
      if (parsedChats.length > 0) {
        setActiveChatId(localStorage.getItem('activeChatId') || parsedChats[0].id);
      }
    } else {
      // If nothing in localStorage, create an initial chat
      handleNewChat(true); // Pass true to indicate it's the very first chat
    }
    const savedTemp = localStorage.getItem('modelTemperature');
    if (savedTemp) {
      setTemperature(parseFloat(savedTemp));
    }
  }, []); // Load on initial mount

  useEffect(() => {
    if (chats.length > 0) {
      localStorage.setItem('chatSessions', JSON.stringify(chats));
    }
    if (activeChatId) {
      localStorage.setItem('activeChatId', activeChatId);
    }
    localStorage.setItem('modelTemperature', temperature.toString());
  }, [chats, activeChatId, temperature]);

  const handleNewChat = (isInitialChat = false) => {
    const newChatId = Date.now().toString();
    const newChat: ChatSession = {
      id: newChatId,
      name: isInitialChat ? "New Chat" : `Chat ${chats.length + 1}`,
      messages: [],
    };
    setChats(prevChats => [newChat, ...prevChats]); // Add new chat to the top
    setActiveChatId(newChatId);
    setInputValue('');
    
    // Reset UI state for the new chat
    setAttachments([]);
    setSelectedCollection('default');
    fetchTools(); // This will reset tools to their default state
  };

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
    return await searchDocumentsAPI(query, collectionName);
  };

  // Function to fetch available tools from the backend
  const fetchTools = async () => {
    const tools = await fetchToolsAPI();
    setTools(tools);
  };

  // Load tools on mount
  useEffect(() => {
    fetchTools();
  }, []);

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
          const result = await convertFile(attachment.file);
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
        const data = await sendMessage({
          text: contextualMessage,
          temperature, 
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
    <div className="flex h-screen bg-[#FAFBFC] text-gray-800 font-['Inter',_sans-serif] antialiased">
      {/* Sidebar */}
      <div className="w-72 bg-white p-3 flex flex-col space-y-3 border-r border-gray-200 shadow-sm">
        {/* Search bar */}
        <div className="relative">
          <SearchIcon />
          <input
            type="text"
            placeholder="Search chats..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-10 pr-3 py-2 bg-gray-50 border border-gray-200 rounded-lg text-sm text-gray-700 focus:outline-none focus:ring-2 focus:ring-indigo-400 focus:border-transparent transition-all duration-200"
          />
        </div>
        
        <button 
          onClick={() => handleNewChat()}
          className="w-full flex items-center px-3 py-2.5 rounded-lg text-sm font-medium text-gray-600 bg-gray-50 hover:bg-indigo-50 hover:text-indigo-700 focus:outline-none focus:ring-2 focus:ring-indigo-500 transition-all duration-200 hover:shadow-sm"
        >
          <PlusIcon />
          New Chat
        </button>
        
        <button 
          onClick={() => router.push('/upload')}
          className="w-full flex items-center px-3 py-2.5 rounded-lg text-sm font-medium text-gray-600 bg-gray-50 hover:bg-green-50 hover:text-green-700 focus:outline-none focus:ring-2 focus:ring-green-500 transition-all duration-200 hover:shadow-sm"
        >
          <UploadCloudIcon />
          Upload Files
        </button>
        
        <button 
          onClick={() => router.push('/services')}
          className="w-full flex items-center px-3 py-2.5 rounded-lg text-sm font-medium text-gray-600 bg-gray-50 hover:bg-purple-50 hover:text-purple-700 focus:outline-none focus:ring-2 focus:ring-purple-500 transition-all duration-200 hover:shadow-sm"
        >
          <ServicesIcon />
          AI Services
        </button>
        
        <div className="flex-1 overflow-y-auto mt-1 space-y-1 pr-1">
          {chats
            .filter(chat => !searchQuery || chat.name.toLowerCase().includes(searchQuery.toLowerCase()))
            .map(chat => (
              <div 
                key={chat.id} 
                onClick={() => handleSwitchChat(chat.id)}
                className={`flex items-center p-3 rounded-lg cursor-pointer text-sm truncate transition-all duration-200 ${
                  activeChatId === chat.id 
                    ? 'bg-indigo-50 text-indigo-700 font-semibold border-l-4 border-indigo-500' 
                    : 'text-gray-700 hover:bg-gray-50 hover:text-indigo-600 hover:shadow-sm'
                }`}
                title={chat.name}
              >
                <ChatBubbleIcon />
                <span className="truncate">{chat.name}</span>
              </div>
          ))}
        </div>
      </div>

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
            setIsDragging={setIsDragging}
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
      <SettingsSidebar
        isCollapsed={isSettingsCollapsed}
        setIsCollapsed={setIsSettingsCollapsed}
        temperature={temperature}
        setTemperature={setTemperature}
        systemPrompt={systemPrompt}
        setSystemPrompt={setSystemPrompt}
        tools={tools}
        setTools={setTools}
        collections={collections}
        selectedCollection={selectedCollection}
        setSelectedCollection={setSelectedCollection}
        attachments={attachments}
        setAttachments={setAttachments}
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
    </div>
  );
}
