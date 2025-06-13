"use client"

import React, { useState, useRef, useEffect } from 'react';
import { useRouter } from 'next/navigation';

// Icon components
const UploadIcon = () => (
  <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="w-12 h-12 text-indigo-500">
    <path d="M14.5 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7.5L14.5 2z"/>
    <polyline points="14,2 14,8 20,8"/>
    <line x1="12" y1="18" x2="12" y2="12"/>
    <line x1="9" y1="15" x2="12" y2="12"/>
    <line x1="15" y1="15" x2="12" y2="12"/>
  </svg>
);

const FileIcon = ({ fileType }: { fileType: string }) => {
  if (fileType === 'application/pdf') {
    return (
      <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" className="w-6 h-6 text-red-500">
        <path fillRule="evenodd" d="M4.5 2A1.5 1.5 0 003 3.5v13A1.5 1.5 0 004.5 18h11a1.5 1.5 0 001.5-1.5V7.621a1.5 1.5 0 00-.44-1.06l-4.12-4.122A1.5 1.5 0 0011.378 2H4.5zm2.25 8.5a.75.75 0 000 1.5h6.5a.75.75 0 000-1.5h-6.5zm0 3a.75.75 0 000 1.5h6.5a.75.75 0 000-1.5h-6.5z" clipRule="evenodd" />
      </svg>
    );
  } else if (fileType.includes('word')) {
    return (
      <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" className="w-6 h-6 text-blue-500">
        <path fillRule="evenodd" d="M4.5 2A1.5 1.5 0 003 3.5v13A1.5 1.5 0 004.5 18h11a1.5 1.5 0 001.5-1.5V7.621a1.5 1.5 0 00-.44-1.06l-4.12-4.122A1.5 1.5 0 0011.378 2H4.5zm4.75 6a.75.75 0 00-1.5 0v4.5a.75.75 0 001.5 0V9.5h1a.75.75 0 000-1.5h-1z" clipRule="evenodd" />
      </svg>
    );
  } else {
    return (
      <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" className="w-6 h-6 text-gray-500">
        <path d="M3 3.75A1.75 1.75 0 014.75 2h10.5c.966 0 1.75.784 1.75 1.75v10.5A1.75 1.75 0 0115.25 16h-1.5a.75.75 0 010-1.5h1.5a.25.25 0 00.25-.25V3.75a.25.25 0 00-.25-.25H4.75a.25.25 0 00-.25.25v10.5c0 .138.112.25.25.25h1.5a.75.75 0 010 1.5h-1.5A1.75 1.75 0 013 14.25V3.75z" />
        <path d="M3.75 6.5a.75.75 0 01.75-.75h7a.75.75 0 010 1.5h-7a.75.75 0 01-.75-.75zM3 10.25a.75.75 0 01.75-.75h7a.75.75 0 010 1.5h-7a.75.75 0 01-.75-.75z" />
      </svg>
    );
  }
};

const CheckIcon = () => (
  <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="w-6 h-6 text-green-500">
    <polyline points="20,6 9,17 4,12"/>
  </svg>
);

const XIcon = () => (
  <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="w-6 h-6 text-red-500">
    <line x1="18" y1="6" x2="6" y2="18"/>
    <line x1="6" y1="6" x2="18" y2="18"/>
  </svg>
);

const HomeIcon = () => (
  <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="w-5 h-5">
    <path d="m3 9 9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/>
    <polyline points="9,22 9,12 15,12 15,22"/>
  </svg>
);

const LoadingSpinner = () => (
  <div className="inline-block animate-spin rounded-full h-6 w-6 border-b-2 border-indigo-600"></div>
);

type UploadStatus = 'idle' | 'uploading' | 'success' | 'error';

interface UploadResult {
  success: boolean;
  message: string;
  collection_name: string;
  document_count: number;
  file_name: string;
}

export default function UploadPage() {
  const router = useRouter();
  const [file, setFile] = useState<File | null>(null);
  const [collectionName, setCollectionName] = useState('');
  const [uploadStatus, setUploadStatus] = useState<UploadStatus>('idle');
  const [uploadResult, setUploadResult] = useState<UploadResult | null>(null);
  const [isDragging, setIsDragging] = useState(false);
  const [collections, setCollections] = useState<string[]>([]);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Load existing collections on component mount
  useEffect(() => {
    fetchCollections();
  }, []);

  const fetchCollections = async () => {
    try {
      const response = await fetch('http://localhost:8000/api/v1/upload/collections');
      if (response.ok) {
        const data = await response.json();
        console.log('Collections received:', data);
        // Backend returns array directly, not { collections: [...] }
        setCollections(Array.isArray(data) ? data : []);
      }
    } catch (error) {
      console.error('Error fetching collections:', error);
    }
  };

  const handleFileSelect = (event: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFile = event.target.files?.[0];
    if (selectedFile) {
      setFile(selectedFile);
      setUploadStatus('idle');
      setUploadResult(null);
    }
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    
    const droppedFile = e.dataTransfer.files[0];
    if (droppedFile) {
      setFile(droppedFile);
      setUploadStatus('idle');
      setUploadResult(null);
    }
  };

  const handleUpload = async () => {
    if (!file || !collectionName.trim()) {
      return;
    }

    setUploadStatus('uploading');
    
    const formData = new FormData();
    formData.append('file', file);
    formData.append('collection_name', collectionName.trim());

    try {
      const response = await fetch('http://localhost:8000/api/v1/upload/upload', {
        method: 'POST',
        body: formData,
      });

      const result = await response.json();

      if (response.ok) {
        setUploadStatus('success');
        setUploadResult(result);
        fetchCollections();
      } else {
        setUploadStatus('error');
        setUploadResult(result);
      }
    } catch (error) {
      setUploadStatus('error');
      setUploadResult({
        success: false,
        message: 'Network error: Could not connect to server',
        collection_name: collectionName,
        document_count: 0,
        file_name: file.name
      });
    }
  };

  const resetForm = () => {
    setFile(null);
    setCollectionName('');
    setUploadStatus('idle');
    setUploadResult(null);
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <div className="bg-white shadow-sm border-b">
        <div className="max-w-4xl mx-auto px-6 py-4">
          <div className="flex items-center space-x-4">
            <button
              onClick={() => router.push('/')}
              className="flex items-center space-x-2 text-gray-600 hover:text-indigo-600 transition-colors"
            >
              <HomeIcon />
              <span>Back to Chat</span>
            </button>
            <div className="h-6 w-px bg-gray-300"></div>
            <h1 className="text-2xl font-bold text-gray-900">Upload Documents</h1>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="max-w-2xl mx-auto px-6 py-8">
        <div className="bg-white rounded-xl shadow-lg border border-gray-200 overflow-hidden">
          
          {/* Upload Section */}
          <div className="p-8">
            {/* File Drop Zone */}
            <div
              className={`border-2 border-dashed rounded-lg p-8 text-center transition-all duration-200 ${
                isDragging
                  ? 'border-indigo-500 bg-indigo-50'
                  : file
                  ? 'border-green-300 bg-green-50'
                  : 'border-gray-300 hover:border-indigo-400 hover:bg-gray-50'
              }`}
              onDragOver={handleDragOver}
              onDragLeave={handleDragLeave}
              onDrop={handleDrop}
            >
              {file ? (
                <div className="space-y-4">
                  <div className="flex items-center justify-center space-x-3">
                    <FileIcon fileType={file.type} />
                    <div className="text-left">
                      <p className="font-medium text-gray-900">{file.name}</p>
                      <p className="text-sm text-gray-500">
                        {(file.size / 1024 / 1024).toFixed(2)} MB
                      </p>
                    </div>
                  </div>
                  <button
                    onClick={() => setFile(null)}
                    className="text-sm text-gray-500 hover:text-red-600"
                  >
                    Remove
                  </button>
                </div>
              ) : (
                <div className="space-y-4">
                  <UploadIcon />
                  <div>
                    <p className="text-lg font-medium text-gray-900 mb-2">
                      Drop file here or{' '}
                      <button
                        onClick={() => fileInputRef.current?.click()}
                        className="text-indigo-600 hover:text-indigo-700"
                      >
                        browse
                      </button>
                    </p>
                  </div>
                </div>
              )}
            </div>

            <input
              ref={fileInputRef}
              type="file"
              accept=".pdf,.txt,.docx,.doc"
              onChange={handleFileSelect}
              className="hidden"
            />

            {/* Collection Selection */}
            <div className="mt-6">
              <label htmlFor="collection" className="block text-sm font-medium text-gray-700 mb-2">
                Collection
              </label>
              <div className="space-y-3">
                {/* Existing Collections Dropdown */}
                {collections.filter(c => c !== 'default').length > 0 && (
                  <div>
                    <label className="block text-xs text-gray-600 mb-1">Select existing collection:</label>
                    <select
                      value={collections.includes(collectionName) ? collectionName : ''}
                      onChange={(e) => setCollectionName(e.target.value)}
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent text-sm"
                    >
                      <option value="">Choose existing collection...</option>
                      {collections.filter(c => c !== 'default').map((collection) => (
                        <option key={collection} value={collection}>
                          {collection}
                        </option>
                      ))}
                    </select>
                  </div>
                )}
                
                {/* OR divider */}
                {collections.filter(c => c !== 'default').length > 0 && (
                  <div className="flex items-center">
                    <div className="flex-1 border-t border-gray-300"></div>
                    <span className="px-3 text-xs text-gray-500 bg-white">OR</span>
                    <div className="flex-1 border-t border-gray-300"></div>
                  </div>
                )}
                
                {/* New Collection Input */}
                <div>
                  <label className="block text-xs text-gray-600 mb-1">
                    {collections.filter(c => c !== 'default').length > 0 ? 'Create new collection:' : 'Collection name:'}
                  </label>
                  <input
                    id="collection"
                    type="text"
                    value={!collections.includes(collectionName) ? collectionName : ''}
                    onChange={(e) => setCollectionName(e.target.value)}
                    placeholder="Enter collection name"
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent text-sm"
                  />
                  {collections.filter(c => c !== 'default').length > 0 && (
                    <p className="text-xs text-gray-500 mt-1">
                      Existing: {collections.filter(c => c !== 'default').join(', ')}
                    </p>
                  )}
                </div>
              </div>
            </div>

            {/* Upload Button */}
            <div className="mt-8">
              <button
                onClick={handleUpload}
                disabled={!file || !collectionName.trim() || uploadStatus === 'uploading'}
                className={`w-full py-3 px-6 rounded-lg font-medium transition-all duration-200 ${
                  !file || !collectionName.trim() || uploadStatus === 'uploading'
                    ? 'bg-gray-300 text-gray-500 cursor-not-allowed'
                    : 'bg-indigo-600 text-white hover:bg-indigo-700 hover:shadow-lg'
                }`}
              >
                {uploadStatus === 'uploading' ? (
                  <div className="flex items-center justify-center space-x-2">
                    <LoadingSpinner />
                    <span>Uploading...</span>
                  </div>
                ) : (
                  'Upload'
                )}
              </button>
            </div>
          </div>

          {/* Results Section */}
          {uploadResult && (
            <div className="border-t border-gray-200 p-8">
              <div className={`rounded-lg p-4 ${
                uploadStatus === 'success' ? 'bg-green-50 border border-green-200' : 'bg-red-50 border border-red-200'
              }`}>
                <div className="flex items-start space-x-3">
                  {uploadStatus === 'success' ? <CheckIcon /> : <XIcon />}
                  <div className="flex-1">
                    <h3 className={`font-medium ${
                      uploadStatus === 'success' ? 'text-green-900' : 'text-red-900'
                    }`}>
                      {uploadStatus === 'success' ? 'Upload Successful' : 'Upload Failed'}
                    </h3>
                    <p className={`mt-1 text-sm ${
                      uploadStatus === 'success' ? 'text-green-700' : 'text-red-700'
                    }`}>
                      {uploadResult.message}
                    </p>
                    {uploadStatus === 'success' && (
                      <div className="mt-3 text-sm text-green-700">
                        <p><strong>Collection:</strong> {uploadResult.collection_name}</p>
                        <p><strong>Documents:</strong> {uploadResult.document_count}</p>
                      </div>
                    )}
                  </div>
                </div>
              </div>

              {uploadStatus === 'success' && (
                <div className="mt-6 flex space-x-4">
                  <button
                    onClick={resetForm}
                    className="px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 transition-colors"
                  >
                    Upload Another
                  </button>
                  <button
                    onClick={() => router.push('/')}
                    className="px-4 py-2 bg-gray-600 text-white rounded-lg hover:bg-gray-700 transition-colors"
                  >
                    Back to Chat
                  </button>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
} 