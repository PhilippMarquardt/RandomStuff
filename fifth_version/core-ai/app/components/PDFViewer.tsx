"use client";

import React, { useState, useEffect, useRef, useCallback } from 'react';
import { Document, Page, pdfjs } from 'react-pdf';
import 'react-pdf/dist/Page/AnnotationLayer.css';
import 'react-pdf/dist/Page/TextLayer.css';

// Configure PDF.js worker
pdfjs.GlobalWorkerOptions.workerSrc = new URL(
  'pdfjs-dist/build/pdf.worker.min.mjs',
  import.meta.url,
).toString();

interface PDFFile {
  id: string;
  file: File | null;
  content: string;
  isLoading: boolean;
  error: string | null;
}

interface PDFViewerProps {
  readyPdfs: PDFFile[];
  selectedPdfId: string;
  setSelectedPdfId: (id: string) => void;
  onAddTextToChat?: (text: string) => void;
}

interface ContextMenuProps {
  x: number;
  y: number;
  onAddToChat: () => void;
  onClose: () => void;
}

function ContextMenu({ x, y, onAddToChat, onClose }: ContextMenuProps) {
  const menuRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(event.target as Node)) {
        onClose();
      }
    };

    const handleEscape = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        onClose();
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    document.addEventListener('keydown', handleEscape);

    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
      document.removeEventListener('keydown', handleEscape);
    };
  }, [onClose]);

  return (
    <div
      ref={menuRef}
      className="fixed z-50 bg-white border border-gray-200 rounded-lg shadow-lg py-1 min-w-[160px]"
      style={{ left: x, top: y }}
    >
      <button
        onClick={() => {
          onAddToChat();
          onClose();
        }}
        className="w-full text-left px-4 py-2 text-sm text-gray-700 hover:bg-indigo-50 hover:text-indigo-700 flex items-center"
      >
        <svg className="w-4 h-4 mr-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
        </svg>
        Add to chat
      </button>
    </div>
  );
}

export default function PDFViewer({ readyPdfs, selectedPdfId, setSelectedPdfId, onAddTextToChat }: PDFViewerProps) {
  const [numPages, setNumPages] = useState<number>(0);
  const [pageNumber, setPageNumber] = useState<number>(1);
  const [contextMenu, setContextMenu] = useState<{ x: number; y: number; text: string } | null>(null);
  const [selectedText, setSelectedText] = useState<string>('');
  const pdfContainerRef = useRef<HTMLDivElement>(null);

  const selectedPdf = readyPdfs.find(pdf => pdf.id === selectedPdfId);

  // reset page number
  useEffect(() => {
    setPageNumber(1);
  }, [selectedPdfId]);

  function onDocumentLoadSuccess({ numPages }: { numPages: number }) {
    setNumPages(numPages);
    setPageNumber(1);
  }

  function onDocumentLoadError(error: Error) {
    console.error('Failed to load PDF:', error);
  }

  const getSelectedText = useCallback(() => {
    const selection = window.getSelection();
    if (selection && selection.toString().trim()) {
      return selection.toString().trim();
    }
    return '';
  }, []);

  const handleContextMenu = useCallback((event: React.MouseEvent) => {
    event.preventDefault();
    
    const text = getSelectedText();
    if (text) {
      setSelectedText(text);
      setContextMenu({
        x: event.clientX,
        y: event.clientY,
        text: text
      });
    }
  }, [getSelectedText]);

  const handleAddToChat = useCallback(() => {
    if (selectedText && onAddTextToChat) {
      onAddTextToChat(selectedText);
    }
  }, [selectedText, onAddTextToChat]);

  const closeContextMenu = useCallback(() => {
    setContextMenu(null);
    setSelectedText('');
  }, []);

  // Close context menu when clicking elsewhere or scrolling
  useEffect(() => {
    const handleScroll = () => {
      if (contextMenu) {
        closeContextMenu();
      }
    };

    const container = pdfContainerRef.current;
    if (container) {
      container.addEventListener('scroll', handleScroll);
      return () => container.removeEventListener('scroll', handleScroll);
    }
  }, [contextMenu, closeContextMenu]);

  return (
    <div className="w-1/2 bg-white flex flex-col">
      {/* PDF Viewer Header */}
      <div className="bg-white border-b border-gray-200 px-4 py-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-4">
            <label className="text-sm font-medium text-gray-700">View PDF:</label>
            <select
              value={selectedPdfId}
              onChange={(e) => setSelectedPdfId(e.target.value)}
              className="border border-gray-300 rounded-md px-3 py-1 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
            >
              <option value="">Select PDF to view</option>
              {readyPdfs.map((pdf, index) => (
                <option key={pdf.id} value={pdf.id}>
                  {pdf.file?.name || `Document ${index + 1}`}
                </option>
              ))}
            </select>
          </div>
          
          {selectedPdf && numPages > 0 && (
            <div className="flex items-center space-x-2">
              <button
                onClick={() => setPageNumber(prev => Math.max(1, prev - 1))}
                disabled={pageNumber <= 1}
                className="px-2 py-1 bg-gray-100 text-gray-600 rounded hover:bg-gray-200 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                Previous
              </button>
              <span className="text-sm text-gray-600">
                Page {pageNumber} of {numPages}
              </span>
              <button
                onClick={() => setPageNumber(prev => Math.min(numPages, prev + 1))}
                disabled={pageNumber >= numPages}
                className="px-2 py-1 bg-gray-100 text-gray-600 rounded hover:bg-gray-200 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                Next
              </button>
            </div>
          )}
        </div>
      </div>

      {/* PDF Display Area */}
      <div 
        ref={pdfContainerRef}
        className="flex-1 overflow-auto p-4 bg-gray-50"
        onContextMenu={handleContextMenu}
      >
        {selectedPdf?.file ? (
          <div className="flex justify-center">
            <Document
              file={selectedPdf.file}
              onLoadSuccess={onDocumentLoadSuccess}
              onLoadError={onDocumentLoadError}
              className="border border-gray-300 shadow-lg"
              loading={<p>Loading PDF...</p>}
            >
              <Page 
                pageNumber={pageNumber}
                width={Math.min(600, (typeof window !== 'undefined' ? window.innerWidth : 600) * 0.4)}
                renderAnnotationLayer={true}
                renderTextLayer={true}
              />
            </Document>
          </div>
        ) : (
          <div className="flex items-center justify-center h-full text-gray-500">
            <div className="text-center">
              <svg className="w-16 h-16 mx-auto mb-4 text-gray-300" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
              </svg>
              <p className="text-lg font-medium">Select a PDF to view</p>
              <p className="text-sm">Choose a document from the dropdown above</p>
              <p className="text-xs text-gray-400 mt-2">Tip: Select text and right-click to add to chat</p>
            </div>
          </div>
        )}
      </div>

      {/* Context Menu */}
      {contextMenu && (
        <ContextMenu
          x={contextMenu.x}
          y={contextMenu.y}
          onAddToChat={handleAddToChat}
          onClose={closeContextMenu}
        />
      )}
    </div>
  );
} 