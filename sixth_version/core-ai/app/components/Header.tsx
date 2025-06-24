"use client";

import React from 'react';
import { useRouter } from 'next/navigation';

interface HeaderProps {
  title: string;
  subtitle?: string;
  showBackButton?: boolean;
  backButtonText?: string;
  backButtonPath?: string;
  children?: React.ReactNode;
}

const BackIcon = () => (
  <svg className="w-5 h-5 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 19l-7-7m0 0l7-7m-7 7h18" />
  </svg>
);

export default function Header({ 
  title, 
  subtitle, 
  showBackButton = true, 
  backButtonText = "Back to Chat", 
  backButtonPath = "/",
  children 
}: HeaderProps) {
  const router = useRouter();

  return (
    <>
      {/* Navigation Bar */}
      <nav className="w-full bg-white backdrop-blur-sm border-b border-gray-200 shadow-sm">
        <div className="container mx-auto px-6 py-4 flex justify-between items-center">
          <div className="flex items-center">
            <h1 className="text-xl font-bold text-gray-800 tracking-tight uppercase">{title}</h1>
          </div>
          <div className="flex items-center space-x-3">
            {showBackButton && (
              <button
                onClick={() => router.push(backButtonPath)}
                className="inline-flex items-center text-indigo-600 hover:text-indigo-500 transition-colors duration-200"
              >
                <BackIcon />
                {backButtonText}
              </button>
            )}
            {children}
          </div>
        </div>
      </nav>

      {/* Page Header */}
      {subtitle && (
        <div className="bg-gray-50 border-b border-gray-200">
          <div className="container mx-auto px-6 py-6">
            <div className="text-center">
              <p className="text-gray-600 text-lg">{subtitle}</p>
            </div>
          </div>
        </div>
      )}
    </>
  );
} 