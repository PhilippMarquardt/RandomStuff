import React from 'react';

export const FileIcon = ({ fileType }: { fileType: string }) => {
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