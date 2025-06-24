"use client"

import React from 'react';
import { useRouter } from 'next/navigation';
import {
  PlusIcon,
  UploadCloudIcon,
  ServicesIcon,
  ChatBubbleIcon,
  SearchIcon,
} from '../icons';
import type { ChatSession } from '../../types/chat';

interface ChatSidebarProps {
  searchQuery: string;
  onSearchQueryChange: (query: string) => void;
  onNewChat: () => void;
  chats: ChatSession[];
  activeChatId: string | null;
  onSwitchChat: (id: string) => void;
}

export const ChatSidebar = ({
  searchQuery,
  onSearchQueryChange,
  onNewChat,
  chats,
  activeChatId,
  onSwitchChat,
}: ChatSidebarProps) => {
  const router = useRouter();

  return (
    <div className="w-72 bg-white p-3 flex flex-col space-y-3 border-r border-gray-200 shadow-sm">
      {/* Search bar */}
      <div className="relative">
        <SearchIcon />
        <input
          type="text"
          placeholder="Search chats..."
          value={searchQuery}
          onChange={(e) => onSearchQueryChange(e.target.value)}
          className="w-full pl-10 pr-3 py-2 bg-gray-50 border border-gray-200 rounded-lg text-sm text-gray-700 focus:outline-none focus:ring-2 focus:ring-indigo-400 focus:border-transparent transition-all duration-200"
        />
      </div>
      
      <button 
        onClick={onNewChat}
        className="w-full flex items-center px-3 py-2.5 rounded-lg text-sm font-medium text-gray-600 bg-gray-50 hover:bg-indigo-50 hover:text-indigo-700 focus:outline-none focus:ring-2 focus:ring-indigo-500 transition-all duration-200 hover:shadow-sm"
      >
        <PlusIcon />
        New Chat
      </button>
      
      <button 
        onClick={() => router.push('/upload')}
        className="w-full flex items-center px-3 py-2.5 rounded-lg text-sm font-medium text-gray-600 bg-gray-50 hover:bg-green-50 hover:text-green-700 focus:outli`ne-none focus:ring-2 focus:ring-green-500 transition-all duration-200 hover:shadow-sm"
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
              onClick={() => onSwitchChat(chat.id)}
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
  );
}; 