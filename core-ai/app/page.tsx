"use client"

import React, { useState, useEffect, useRef } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import rehypeHighlight from 'rehype-highlight';
import 'highlight.js/styles/github.css';
import { useRouter } from 'next/navigation';

// Basic Gear Icon SVG component
const GearIcon = () => (
  <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" className="w-5 h-5 text-gray-500 hover:text-indigo-600 transition-colors duration-200">
    <path fillRule="evenodd" d="M11.49 3.17a.75.75 0 01.899.67l.063 1.004a7.502 7.502 0 004.082 3.182l.973-.243a.75.75 0 01.905.654l.5 1.732a.75.75 0 01-.448.867l-.99.44a7.505 7.505 0 000 5.062l.99.44a.75.75 0 01.448.867l-.5 1.732a.75.75 0 01-.905.654l-.973-.243a7.502 7.502 0 00-4.082 3.182l-.063 1.004a.75.75 0 01-.9.67H8.51a.75.75 0 01-.9-.67l-.063-1.004a7.502 7.502 0 00-4.082-3.182l-.973.243a.75.75 0 01-.905-.654l-.5-1.732a.75.75 0 01.448-.867l.99-.44a7.505 7.505 0 000-5.062l-.99-.44a.75.75 0 01-.448-.867l.5-1.732a.75.75 0 01.905-.654l.973.243A7.502 7.502 0 007.56 4.844l.063-1.004a.75.75 0 01.9-.67h2.98zM10 6.75a3.25 3.25 0 100 6.5 3.25 3.25 0 000-6.5z" clipRule="evenodd" />
  </svg>
);

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

const SendIcon = () => (
  <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" className="w-5 h-5 transition-transform duration-200 group-hover:translate-x-0.5">
    <path d="M3.105 3.105a.75.75 0 01.814-.102l14.25 5.25a.75.75 0 010 1.392l-14.25 5.25a.75.75 0 01-.912-.99L4.839 10 2.99 3.997a.75.75 0 01.114-.892z" />
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

// Add a notification bell icon
const BellIcon = () => (
  <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" className="w-5 h-5">
    <path fillRule="evenodd" d="M10 2a6 6 0 00-6 6c0 1.887-.454 3.665-1.257 5.234a.75.75 0 00.515 1.076 32.91 32.91 0 003.256.508 3.5 3.5 0 006.972 0 32.903 32.903 0 003.256-.508.75.75 0 00.515-1.076A13.02 13.02 0 0116 8a6 6 0 00-6-6zM8.05 14.943a33.54 33.54 0 003.9 0 2 2 0 01-3.9 0z" clipRule="evenodd" />
  </svg>
);

// Add a file attachment icon
const PaperClipIcon = () => (
  <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" className="w-5 h-5 text-gray-500">
    <path fillRule="evenodd" d="M15.621 4.379a3 3 0 00-4.242 0l-7 7a3 3 0 004.241 4.243h.001l.497-.5a.75.75 0 011.064 1.057l-.498.501-.002.002a4.5 4.5 0 01-6.364-6.364l7-7a4.5 4.5 0 016.368 6.36l-3.455 3.553A2.625 2.625 0 119.52 9.52l3.45-3.451a.75.75 0 111.061 1.06l-3.45 3.451a1.125 1.125 0 001.587 1.595l3.454-3.553a3 3 0 000-4.242z" clipRule="evenodd" />
  </svg>
);

// Add file type icons
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

// Type definitions
type ChatMessage = { 
  text: string; 
  sender: string; 
  attachments?: Array<{
    filename: string;
    content_type: string;
    size: number;
  }>;
};
type ChatSession = {
  id: string;
  name: string;
  messages: ChatMessage[];
};

interface ChatMessageResponse { 
  text: string;
  error?: string | null;
}

// Add types for MCP server
type MCPServer = {
  id: string;
  name: string;
  enabled: boolean;
  status?: 'online' | 'offline' | 'starting' | 'stopping';
  tools?: string[];
};

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
  const [isSettingsOpen, setIsSettingsOpen] = useState(false);
  const [temperature, setTemperature] = useState(0.7);
  const [searchQuery, setSearchQuery] = useState('');
  const [mcpServers, setMcpServers] = useState<MCPServer[]>([]);
  const [attachments, setAttachments] = useState<FileAttachment[]>([]);
  const [showUploads, setShowUploads] = useState(false);
  const [isDragging, setIsDragging] = useState(false);
  const [recentUploads, setRecentUploads] = useState<FileAttachment[]>([]);
  const [collections, setCollections] = useState<string[]>(['default']);
  const [selectedCollection, setSelectedCollection] = useState<string>('default');
  const [showCollectionDropdown, setShowCollectionDropdown] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const dropZoneRef = useRef<HTMLDivElement>(null);
  const settingsButtonRef = useRef<HTMLButtonElement>(null);
  const settingsPopoverRef = useRef<HTMLDivElement>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const collectionDropdownRef = useRef<HTMLDivElement>(null);
  const router = useRouter();

  // Function to fetch collections from the backend
  const fetchCollections = async () => {
    try {
      const response = await fetch('http://localhost:8000/api/v1/upload/collections');
      if (response.ok) {
        const data = await response.json();
        setCollections(data);
        // If current selected collection doesn't exist in the list, reset to default
        if (!data.includes(selectedCollection)) {
          setSelectedCollection(data.includes('default') ? 'default' : data[0] || 'default');
        }
      }
    } catch (error) {
      console.error('Error fetching collections:', error);
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
      if (settingsPopoverRef.current && 
          !settingsPopoverRef.current.contains(event.target as Node) &&
          settingsButtonRef.current && 
          !settingsButtonRef.current.contains(event.target as Node)) {
        setIsSettingsOpen(false);
      }
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
  }, [settingsPopoverRef, settingsButtonRef, collectionDropdownRef]);

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
    try {
      const response = await fetch('http://localhost:8000/api/v1/upload/search', {
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
        const searchResults = await response.json();
        if (searchResults.results && searchResults.results.length > 0) {
          // Format the search results into context
          const context = searchResults.results
            .map((result: any, index: number) => 
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
  };

  // Function to fetch MCP server status from backend
  const fetchMcpStatus = async () => {
    try {
      const response = await fetch('http://localhost:8000/api/v1/chat/mcp/status');
      if (response.ok) {
        const data = await response.json();
        
        // Convert backend format to frontend format
        const servers: MCPServer[] = Object.entries(data.servers).map(([key, enabled], index) => ({
          id: key,
          name: key.charAt(0).toUpperCase() + key.slice(1) + ' Server',
          enabled: enabled as boolean,
          status: 'online' as const,
          tools: data.tools[key] ? data.tools[key].map((tool: any) => tool.name) : []
        }));
        
        setMcpServers(servers);
      }
    } catch (error) {
      console.error('Error fetching MCP status:', error);
      // Fallback to default servers if backend is unavailable
      setMcpServers([
        { id: 'weather', name: 'Weather Server', enabled: true, status: 'online', tools: ['get_weather', 'get_weather_forecast'] },
        { id: 'utilities', name: 'Utilities Server', enabled: true, status: 'online', tools: ['search_web', 'calculate'] },
      ]);
    }
  };

  // Function to update MCP server status on backend
  const updateMcpServers = async (serverUpdates: Record<string, boolean>) => {
    try {
      const response = await fetch('http://localhost:8000/api/v1/chat/mcp/servers/update', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          servers: serverUpdates
        }),
      });
      
      if (response.ok) {
        // Refresh the status from backend
        fetchMcpStatus();
      }
    } catch (error) {
      console.error('Error updating MCP servers:', error);
    }
  };

  // Load MCP status on mount
  useEffect(() => {
    fetchMcpStatus();
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
          const content = await readFileContent(attachment.file);
          fileAttachments.push({
            filename: attachment.file.name,
            content: content,
            content_type: attachment.file.type
          });
        } catch (error) {
          console.error(`Error reading file ${attachment.file.name}:`, error);
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

      // Prepare MCP server configuration
      const mcpConfig = Object.fromEntries(
        mcpServers.map(server => [server.id, server.enabled])
      );

      try {
        const requestBody: any = { 
          text: contextualMessage, // Send the contextual message instead of just currentInput
          temperature, 
          history: historyForBackend,
          mcp_servers: mcpConfig  // Add MCP configuration
        };
        
        // Add file attachments if any
        if (fileAttachments.length > 0) {
          requestBody.attachments = fileAttachments;
        }

        const response = await fetch('http://localhost:8000/api/v1/chat/invoke', {
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

        const data: ChatMessageResponse = await response.json();
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
      }
    }
  };

  // Helper function to read file content
  const readFileContent = (file: File): Promise<string> => {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = (e) => {
        if (e.target?.result) {
          resolve(e.target.result as string);
        } else {
          reject(new Error('Failed to read file'));
        }
      };
      reader.onerror = () => reject(new Error('File reading error'));
      
      // Handle different file types
      if (file.type.startsWith('text/') || 
          file.type === 'application/json' || 
          file.type === 'application/javascript' ||
          file.type === 'application/xml' ||
          file.name.endsWith('.txt') ||
          file.name.endsWith('.md') ||
          file.name.endsWith('.csv') ||
          file.name.endsWith('.py') ||
          file.name.endsWith('.js') ||
          file.name.endsWith('.html') ||
          file.name.endsWith('.css') ||
          file.name.endsWith('.json') ||
          file.name.endsWith('.xml') ||
          file.name.endsWith('.yml') ||
          file.name.endsWith('.yaml')) {
        // Read as text for text-based files
        reader.readAsText(file);
      } else if (file.type.startsWith('image/')) {
        // For images, provide metadata and indicate it's an image
        resolve(`[Image: ${file.name} (${file.type}, ${Math.round(file.size / 1024)}KB) - Image content cannot be directly processed as text. Please describe what you see in the image or ask specific questions about it.]`);
      } else {
        // For other binary files, provide metadata
        resolve(`[File: ${file.name} (${file.type}, ${Math.round(file.size / 1024)}KB) - Binary file content cannot be displayed as text. File type: ${file.type}]`);
      }
    });
  };

  const handleToggleSettings = () => {
    setIsSettingsOpen(!isSettingsOpen);
  };

  const handleTemperatureChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    setTemperature(parseFloat(event.target.value));
  };

  const handleToggleMcpServer = (serverId: string) => {
    const updatedServers = mcpServers.map(server => 
      server.id === serverId 
        ? { ...server, enabled: !server.enabled } 
        : server
    );
    setMcpServers(updatedServers);
    
    // Update backend
    const serverUpdates = Object.fromEntries(
      updatedServers.map(server => [server.id, server.enabled])
    );
    updateMcpServers(serverUpdates);
  };

  const handleToggleAllMcpServers = (enable: boolean) => {
    const updatedServers = mcpServers.map(server => ({
      ...server,
      enabled: enable
    }));
    setMcpServers(updatedServers);
    
    // Update backend
    const serverUpdates = Object.fromEntries(
      updatedServers.map(server => [server.id, server.enabled])
    );
    updateMcpServers(serverUpdates);
  };

  const renderInputBarContent = (isCentered: boolean) => (
    <div className="relative flex items-center w-full">
      <button
        onClick={() => setShowUploads(!showUploads)}
        className="mr-2 p-2 rounded-full hover:bg-gray-100 transition-colors focus:outline-none focus:ring-2 focus:ring-indigo-500"
        aria-label="Attach files"
      >
        <PaperClipIcon />
      </button>
      
      <button
        ref={settingsButtonRef}
        onClick={handleToggleSettings}
        className="mr-2 p-2 rounded-full hover:bg-gray-100 transition-colors focus:outline-none focus:ring-2 focus:ring-indigo-500"
        aria-label="Settings"
      >
        <GearIcon />
      </button>
      
      {showUploads && (
        <div className="absolute bottom-full left-0 mb-2 w-64 bg-white rounded-lg shadow-lg border border-gray-200 p-3 z-10 animate-fadeIn">
          <div className="flex justify-between items-center mb-2">
            <h4 className="text-sm font-medium text-gray-700">Attach Files</h4>
            <button 
              onClick={() => setShowUploads(false)}
              className="text-gray-400 hover:text-gray-600"
            >
              <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
          
          <button
            onClick={() => fileInputRef.current?.click()}
            className="w-full flex items-center justify-center px-3 py-2 bg-indigo-50 hover:bg-indigo-100 text-indigo-700 text-sm font-medium rounded-md transition-colors mb-2"
          >
            <PaperClipIcon />
            <span className="ml-2">Select Files</span>
          </button>
          
          <p className="text-xs text-gray-500 text-center">Drag & drop files in the settings panel</p>
        </div>
      )}
      
      <input
        type="text"
        value={inputValue}
        onChange={(e) => setInputValue(e.target.value)}
        onKeyPress={(e) => {
          if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            handleSendMessage();
          }
        }}
        placeholder={
          isCentered 
            ? selectedCollection === 'default' 
              ? "Ask me anything..." 
              : `Ask about documents in "${selectedCollection}"...`
            : selectedCollection === 'default'
              ? "Message LLM..."
              : `Ask about "${selectedCollection}"...`
        }
        className={`flex-1 bg-transparent text-sm md:text-base py-2.5 h-full focus:outline-none focus:ring-2 focus:ring-indigo-500 text-gray-800 placeholder-gray-400 rounded-md ${isCentered ? 'px-4' : 'px-3'}`}
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
        onClick={handleSendMessage}
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
    currentMessages.map((message, index) => (
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
                          prose-pre:p-4 prose-pre:rounded-xl prose-pre:my-3.5 prose-pre:font-mono prose-pre:bg-opacity-75
                          prose-p:leading-relaxed prose-headings:leading-tight
                          ${message.sender === 'user'
                            ? 'bg-indigo-600 text-white prose-strong:text-white border-indigo-500 shadow-indigo-100'
                            : 'bg-gray-50 text-gray-800 prose-strong:text-gray-900 border-gray-200 shadow-gray-100 relative before:absolute before:bottom-[-6px] before:left-[-6px] before:w-3 before:h-3 before:rotate-45 before:bg-gray-50 before:border-l before:border-b before:border-gray-200' 
                          }`}
            >
              {message.sender === 'llm' ? (
                <ReactMarkdown 
                  remarkPlugins={[remarkGfm]} 
                  rehypePlugins={[rehypeHighlight]}
                  components={{
                    code({node, className, children, ...props}) {
                      return (
                        <code className={`${className} font-['JetBrains_Mono',_monospace] text-sm leading-relaxed`} {...props}>
                          {children}
                        </code>
                      )
                    }
                  }}
                >
                  {message.text}
                </ReactMarkdown>
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

  // Render the settings panel
  const renderSettingsPanel = () => isSettingsOpen && (
    <div 
      ref={settingsPopoverRef}
      className="fixed inset-y-0 right-0 w-80 bg-white shadow-lg z-50 border-l border-gray-200 transform transition-transform duration-200 ease-in-out animate-fadeIn overflow-y-auto"
    >
      <div className="p-4 border-b border-gray-200">
        <div className="flex justify-between items-center">
          <h2 className="text-lg font-semibold text-gray-800">Settings</h2>
          <button 
            onClick={() => setIsSettingsOpen(false)}
            className="p-1 rounded-full hover:bg-gray-100 transition-colors"
          >
            <svg xmlns="http://www.w3.org/2000/svg" className="h-6 w-6 text-gray-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>
      </div>

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
        <p className="text-xs text-gray-500 mt-1">
          Lower values produce more focused, deterministic responses. Higher values produce more creative, varied responses.
        </p>
      </div>

      {/* MCP Servers Section */}
      <div className="p-4 border-b border-gray-200">
        <div className="flex justify-between items-center mb-3">
          <h3 className="text-md font-medium text-gray-700">MCP Servers</h3>
          <div className="flex space-x-2">
            <button 
              onClick={() => handleToggleAllMcpServers(true)}
              className="text-xs px-2 py-1 bg-indigo-50 hover:bg-indigo-100 text-indigo-600 rounded transition-colors"
            >
              Enable All
            </button>
            <button 
              onClick={() => handleToggleAllMcpServers(false)}
              className="text-xs px-2 py-1 bg-gray-50 hover:bg-gray-100 text-gray-600 rounded transition-colors"
            >
              Disable All
            </button>
            <button 
              onClick={fetchMcpStatus}
              className="text-xs px-2 py-1 bg-green-50 hover:bg-green-100 text-green-600 rounded transition-colors"
              title="Refresh server status"
            >
              Refresh
            </button>
          </div>
        </div>
        <div className="space-y-3">
          {mcpServers.map(server => (
            <div key={server.id} className="border border-gray-200 rounded-lg p-3 bg-gray-50">
              <div className="flex items-center justify-between mb-2">
                <div className="flex items-center">
                  <div className={`w-2 h-2 rounded-full mr-2 ${server.status === 'online' ? 'bg-green-500' : 'bg-gray-400'}`}></div>
                  <span className="text-sm font-medium text-gray-700">{server.name}</span>
                </div>
                <label className="relative inline-flex items-center cursor-pointer">
                  <input 
                    type="checkbox" 
                    value="" 
                    className="sr-only peer" 
                    checked={server.enabled} 
                    onChange={() => handleToggleMcpServer(server.id)}
                  />
                  <div className="w-9 h-5 bg-gray-200 peer-focus:outline-none peer-focus:ring-2 peer-focus:ring-indigo-300 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-4 after:w-4 after:transition-all peer-checked:bg-indigo-600"></div>
                </label>
              </div>
              {server.tools && server.tools.length > 0 && (
                <div className="mt-2">
                  <div className="text-xs text-gray-500 mb-1">Available tools:</div>
                  <div className="flex flex-wrap gap-1">
                    {server.tools.map(tool => (
                      <span 
                        key={tool}
                        className={`text-xs px-2 py-1 rounded-full ${
                          server.enabled 
                            ? 'bg-indigo-100 text-indigo-700' 
                            : 'bg-gray-200 text-gray-500'
                        }`}
                      >
                        {tool}
                      </span>
                    ))}
                  </div>
                </div>
              )}
            </div>
          ))}
          {mcpServers.length === 0 && (
            <div className="text-center py-4 text-gray-500">
              <div className="text-sm">Loading MCP servers...</div>
              <div className="text-xs mt-1">Make sure the backend is running</div>
            </div>
          )}
        </div>
        <div className="mt-3 p-2 bg-indigo-50 rounded-lg">
          <div className="text-xs text-indigo-700 font-medium">
            {mcpServers.filter(s => s.enabled).length} of {mcpServers.length} servers enabled
          </div>
          <div className="text-xs text-indigo-600 mt-1">
            MCP servers provide tools like weather, search, and calculations to enhance AI responses.
          </div>
        </div>
      </div>

      {/* Document Collections Section */}
      <div className="p-4 border-b border-gray-200">
        <div className="flex justify-between items-center mb-3">
          <h3 className="text-md font-medium text-gray-700">Document Collections</h3>
          <button 
            onClick={fetchCollections}
            className="text-xs px-2 py-1 bg-green-50 hover:bg-green-100 text-green-600 rounded transition-colors"
            title="Refresh collections"
          >
            Refresh
          </button>
        </div>
        <div className="space-y-2">
          {collections.map((collection) => (
            <button
              key={collection}
              onClick={() => setSelectedCollection(collection)}
              className={`w-full text-left px-3 py-2 text-sm rounded-lg transition-colors flex items-center justify-between border ${
                selectedCollection === collection 
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
              <div className="text-xs mt-1">Upload documents to create collections</div>
            </div>
          )}
        </div>
        <div className="mt-3 p-2 bg-indigo-50 rounded-lg">
          <div className="text-xs text-indigo-700 font-medium">
            Active: {selectedCollection === 'default' ? 'No document context' : selectedCollection}
          </div>
          <div className="text-xs text-indigo-600 mt-1">
            {selectedCollection === 'default' 
              ? 'Select a collection to chat with your documents' 
              : 'Questions will search relevant documents from this collection'
            }
          </div>
        </div>
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
            onChange={handleFileSelect}
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
                    onClick={() => handleRemoveFile(attachment.id)}
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
    </div>
  );

  // Render file attachments above input if present
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
            onClick={() => handleRemoveFile(attachment.id)}
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
              <h1 className="text-xl font-bold text-gray-800 tracking-tight uppercase">AI Chat</h1>
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
          <main className="flex-1 flex flex-col overflow-y-hidden p-1 sm:p-2 md:p-3">
            {/* Message Display Area */}
            <div className={`flex-1 overflow-y-auto p-4 md:p-5 space-y-1 ${currentMessages.length === 0 ? 'flex flex-col justify-center items-center' : 'pt-4'} scroll-smooth`}>
              {currentMessages.length > 0 
                ? (
                  <>
                    {renderMessages()}
                    <div ref={messagesEndRef} />
                  </>
                ) 
                : (
                  <div className="text-center">
                    <h2 className="text-2xl sm:text-3xl font-semibold text-gray-400">How can I help you today?</h2>
                  </div>
                )
              }
            </div>

            {/* Input Area Wrapper */}
            <div
              className={`w-full max-w-2xl lg:max-w-3xl mx-auto flex flex-col transition-all duration-300 ease-in-out px-2 md:px-3
                          ${currentMessages.length === 0 
                              ? 'bg-white rounded-2xl border border-gray-300 my-auto shadow-xl mb-6 sm:mb-8 hover:shadow-lg p-2' 
                              : 'bg-white rounded-xl border border-gray-300 shadow-md py-2 hover:shadow-lg' 
                          }`}
            >
              {renderAttachments()}
              {renderInputBarContent(currentMessages.length === 0)}
            </div>
          </main>
        ) : (
          <main className="flex-1 flex items-center justify-center">
            <p className="text-gray-500 text-lg">Select a chat or start a new one.</p>
          </main>
        )}

        {/* Settings Panel */}
        {renderSettingsPanel()}
        
        {/* Hidden file input for attachments */}
        <input
          type="file"
          multiple
          className="hidden"
          onChange={handleFileSelect}
          ref={fileInputRef}
        />
      </div>
    </div>
  );
}
