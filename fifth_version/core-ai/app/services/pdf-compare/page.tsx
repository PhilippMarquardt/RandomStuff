"use client"

import React, { useState, useRef } from 'react';
import { fileService, chatService, type ChatMessage } from '../../api';
import ChatWindow from '../../components/ChatWindow';
import { useRouter } from 'next/navigation';
import Header from '../../components/Header';
import dynamic from 'next/dynamic';
import type { FileAttachment } from '../../types';

import { UploadCloudIcon, LoadingIcon, PlusIcon, CloseIcon } from '@/app/components/icons';
const PDFViewer = dynamic(() => import('../../components/PDFViewer'), {
  ssr: false,
  loading: () => <div className="w-1/2 bg-white flex items-center justify-center"><p>Loading PDF viewer...</p></div>,
});



interface PDFFile {
  id: string;
  file: File | null;
  content: string;
  isLoading: boolean;
  error: string | null;
}

export default function PDFComparePage() {
  const router = useRouter();
  const [pdfs, setPdfs] = useState<PDFFile[]>([
    { id: '1', file: null, content: '', isLoading: false, error: null },
    { id: '2', file: null, content: '', isLoading: false, error: null }
  ]);
  const [systemPrompt, setSystemPrompt] = useState(`You are an expert document analyst specializing in comprehensive document comparison and data visualization. 

ANALYSIS REQUIREMENTS:
- Find identical sections across ALL uploaded documents and show differences
- Only compare sections present in ALL documents
- Highlight key differences, similarities, and trends
- Focus on numerical data, financial metrics, portfolio performance, and benchmark comparisons
- Don't miss any important details or data points

VISUALIZATION CAPABILITIES:
Use <START_FIGURE> and <END_FIGURE> markers to create interactive visualizations:

<START_FIGURE>{"type": "table", "data": {"Document": ["Doc A", "Doc B"], "Metric": [100, 120], "Change": ["+5%", "+12%"]}}<END_FIGURE>

<START_FIGURE>{"type": "line", "data": [{"x": ["Q1", "Q2", "Q3"], "y": [10, 15, 12], "name": "Portfolio A"}, {"x": ["Q1", "Q2", "Q3"], "y": [8, 14, 16], "name": "Portfolio B"}], "layout": {"title": "Performance Comparison", "xaxis": {"title": "Quarter"}, "yaxis": {"title": "Returns (%)"}}}<END_FIGURE>

<START_FIGURE>{"type": "bar", "data": {"x": ["Asset A", "Asset B", "Asset C"], "y": [25, 30, 15], "name": "Allocation %"}, "layout": {"title": "Asset Allocation Comparison"}}<END_FIGURE>

<START_FIGURE>{"type": "pie", "data": {"labels": ["Stocks", "Bonds", "Real Estate", "Cash"], "values": [60, 25, 10, 5]}, "layout": {"title": "Portfolio Composition"}}<END_FIGURE>

<START_FIGURE>{"type": "scatter", "data": {"x": [5, 8, 12, 15], "y": [3, 7, 9, 12], "mode": "markers", "name": "Risk vs Return"}, "layout": {"title": "Risk-Return Analysis", "xaxis": {"title": "Risk (%)"}, "yaxis": {"title": "Return (%)"}}}<END_FIGURE>

<START_FIGURE>{"type": "heatmap", "data": {"z": [[1, 0.8, 0.3], [0.8, 1, 0.5], [0.3, 0.5, 1]], "x": ["Stock A", "Stock B", "Stock C"], "y": ["Stock A", "Stock B", "Stock C"]}, "layout": {"title": "Asset Correlation Matrix"}}<END_FIGURE>

<START_FIGURE>{"type": "box", "data": {"y": [2, 4, 6, 8, 10, 12, 15], "name": "Return Distribution"}, "layout": {"title": "Return Distribution Analysis"}}<END_FIGURE>

<START_FIGURE>{"type": "bubble", "data": {"x": [10, 15, 20], "y": [5, 8, 12], "size": [20, 30, 40], "name": "Performance Metrics"}, "layout": {"title": "Multi-Factor Analysis"}}<END_FIGURE>
`);
  const [showChat, setShowChat] = useState(false);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [inputValue, setInputValue] = useState('');
  const [attachments, setAttachments] = useState<FileAttachment[]>([]);
  const [isComparing, setIsComparing] = useState(false);
  const [isDragging] = useState(false);
  const [selectedPdfId, setSelectedPdfId] = useState<string>('');
  const dropZoneRef = useRef<HTMLDivElement>(null!);
  const fileInputRef = useRef<HTMLInputElement>(null!);

  const handleFileUpload = async (file: File, pdfId: string) => {
    setPdfs(prev => prev.map(pdf => 
      pdf.id === pdfId 
        ? { ...pdf, file, isLoading: true, error: null }
        : pdf
    ));
    
    try {
      const result = await fileService.convertFile(file);
      setPdfs(prev => prev.map(pdf => 
        pdf.id === pdfId 
          ? { ...pdf, content: result.text, isLoading: false }
          : pdf
      ));
    } catch (error) {
      setPdfs(prev => prev.map(pdf => 
        pdf.id === pdfId 
          ? { 
              ...pdf, 
              isLoading: false, 
              error: `Failed to convert PDF: ${error instanceof Error ? error.message : 'Unknown error'}`
            }
          : pdf
      ));
    }
  };

  const handleDrop = (e: React.DragEvent<HTMLDivElement>, pdfId: string) => {
    e.preventDefault();
    const files = e.dataTransfer.files;
    if (files.length > 0 && files[0].type === 'application/pdf') {
      handleFileUpload(files[0], pdfId);
    }
  };

  const handleDragOver = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
  };

  const addPDF = () => {
    const newId = Date.now().toString();
    setPdfs(prev => [...prev, { id: newId, file: null, content: '', isLoading: false, error: null }]);
  };

  const removePDF = (pdfId: string) => {
    setPdfs(prev => prev.filter(pdf => pdf.id !== pdfId));
  };

  const handleStartComparison = async () => {
    const readyPdfs = pdfs.filter(pdf => pdf.content);
    if (readyPdfs.length < 2) return;

    setIsComparing(true);
    setMessages([{
      text: `Starting comparison analysis of ${readyPdfs.length} PDF documents...`,
      sender: 'llm'
    }]);
    setShowChat(true);
    setSelectedPdfId(readyPdfs[0].id);

    try {
      const documentsSection = readyPdfs.map((pdf, index) => 
        `Document ${index + 1}: "${pdf.file?.name}"
Content:
${pdf.content}`
      ).join('\n\n');

      const comparisonPrompt = `
${systemPrompt}

${documentsSection}

Please provide a detailed comparison analysis.`;

      const response = await chatService.sendMessage({
        text: comparisonPrompt,
        temperature: 0.1,
        history: [],
        enabledTools: [],
        systemPrompt: systemPrompt
      });

      setMessages([{
        text: response.text,
        sender: 'llm'
      }]);
    } catch (error) {
      setMessages([{
        text: `Comparison failed: ${error instanceof Error ? error.message : 'Unknown error'}`,
        sender: 'llm'
      }]);
    } finally {
      setIsComparing(false);
    }
  };

  const handleSendMessage = async () => {
    if (!inputValue.trim()) return;

    const userMessage: ChatMessage = {
      text: inputValue.trim(),
      sender: 'user'
    };
    setInputValue('');
    setMessages(prev => [...prev, userMessage]);

    try {
      const readyPdfs = pdfs.filter(pdf => pdf.content);
      const documentsSection = readyPdfs.map((pdf, index) => 
        `Document ${index + 1}: "${pdf.file?.name}"
Content:
${pdf.content}`
      ).join('\n\n');

      const contextualPrompt = `Based on the following documents:
${documentsSection}

And the previous conversation history:
${messages.map(msg => `${msg.sender}: ${msg.text}`).join('\n')}

Answer the user's new question: ${userMessage.text}`;

      const response = await chatService.sendMessage({
        text: contextualPrompt,
        temperature: 0.1,
        history: messages.map(msg => ({ sender: msg.sender as "user" | "llm", text: msg.text })),
        enabledTools: [],
        systemPrompt: systemPrompt
      });

      setMessages(prev => [...prev, {
        text: response.text,
        sender: 'llm'
      }]);
    } catch (error) {
      setMessages(prev => [...prev, {
        text: `Error: ${error instanceof Error ? error.message : 'Unknown error'}`,
        sender: 'llm'
      }]);
    }
  };

  const handleFileSelect = () => {
    // This is required by ChatWindow but we don't use it in this implementation
  };

  const handleRemoveFile = () => {
    // This is required by ChatWindow but we don't use it in this implementation
  };

  const PDFUploadBox = ({ pdf }: { pdf: PDFFile }) => (
    <div className="relative">
      {pdfs.length > 2 && (
        <button
          onClick={() => removePDF(pdf.id)}
          className="absolute -top-2 -right-2 z-10 bg-red-500 text-white rounded-full p-1 hover:bg-red-600 transition-colors duration-200"
        >
          <CloseIcon />
        </button>
      )}
      <div
        onDrop={(e) => handleDrop(e, pdf.id)}
        onDragOver={handleDragOver}
        className="border-2 border-dashed border-gray-300 rounded-lg p-8 text-center hover:border-indigo-500 transition-colors duration-200 bg-white h-full"
      >
        <input
          type="file"
          id={`pdf${pdf.id}`}
          accept="application/pdf"
          onChange={(e) => {
            const files = e.target.files;
            if (files && files.length > 0) {
              handleFileUpload(files[0], pdf.id);
            }
          }}
          className="hidden"
        />
        
        {pdf.isLoading ? (
          <div className="flex flex-col items-center">
            <LoadingIcon />
            <p className="mt-2 text-sm text-gray-600">Converting PDF...</p>
          </div>
        ) : pdf.file ? (
          <div className="flex flex-col items-center">
            <svg className="w-16 h-16 text-green-500 mb-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <p className="text-sm text-gray-700 font-medium">{pdf.file.name}</p>
            <p className="text-xs text-gray-500 mt-1">
              {Math.round(pdf.file.size / 1024)} KB
            </p>
            {pdf.content && (
              <p className="text-xs text-green-600 mt-2">✓ Ready for comparison</p>
            )}
            <label
              htmlFor={`pdf${pdf.id}`}
              className="mt-4 text-sm text-indigo-600 hover:text-indigo-500 cursor-pointer"
            >
              Change file
            </label>
          </div>
        ) : (
          <label htmlFor={`pdf${pdf.id}`} className="cursor-pointer">
            <UploadCloudIcon />
            <p className="mt-2 text-sm text-gray-600">
              Drop PDF here or <span className="text-indigo-600">browse</span>
            </p>
            <p className="text-xs text-gray-500 mt-1">PDF files only</p>
          </label>
        )}
        
        {pdf.error && (
          <p className="mt-2 text-sm text-red-600">{pdf.error}</p>
        )}
      </div>
    </div>
  );

  const readyPdfCount = pdfs.filter(pdf => pdf.content).length;

  if (showChat) {
    const readyPdfs = pdfs.filter(pdf => pdf.content);

    return (
      <div className="flex h-screen bg-[#FAFBFC] text-gray-800">
        {/* Chat Area */}
        <div className="flex-1 flex flex-col overflow-hidden border-r border-gray-200">
          {/* Header */}
          <Header 
            title="PDF Comparison Results"
            showBackButton={true}
            backButtonText="Back to Upload"
            backButtonPath="/services/pdf-compare"
          >
            
          </Header>

          {/* Chat Window */}
          <ChatWindow
            messages={messages}
            inputValue={inputValue}
            setInputValue={setInputValue}
            attachments={attachments}
            setAttachments={setAttachments}
            selectedCollection="default"
            onSendMessage={handleSendMessage}
            onFileSelect={handleFileSelect}
            onRemoveFile={handleRemoveFile}
            isDragging={isDragging}
            dropZoneRef={dropZoneRef}
            fileInputRef={fileInputRef}
            isLoading={isComparing}
          />
        </div>

        {/* PDF Viewer Area - Now dynamically loaded */}
        <PDFViewer
          readyPdfs={readyPdfs}
          selectedPdfId={selectedPdfId}
          setSelectedPdfId={setSelectedPdfId}
          onAddTextToChat={(text) => {
            // Add the selected text to the current input value
            const newValue = inputValue ? `${inputValue}\n\n"${text}"` : `"${text}"`;
            setInputValue(newValue);
          }}
        />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <Header 
        title="Report Comparison"
        subtitle=""
        showBackButton={true}
        backButtonText="Back to Services"
        backButtonPath="/services"
      >
        <button
          onClick={() => router.push('/')}
          className="inline-flex items-center text-gray-600 hover:text-gray-500"
        >
          <svg className="w-5 h-5 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
          </svg>
          Chat
        </button>
      </Header>
      
      <div className="py-8">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8">

        {/* System Prompt */}
        <div className="bg-white rounded-lg shadow-sm p-6 mb-6">
          <label className="block text-sm font-medium text-black mb-2">
            System Prompt
          </label>
          <textarea
            value={systemPrompt}
            onChange={(e) => setSystemPrompt(e.target.value)}
            rows={4}
            className="w-full px-3 py-2 border text-black border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
            placeholder="Enter instructions for how the AI should compare the documents..."
          />
        </div>

        {/* PDF Upload Section */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 mb-6">
          {pdfs.map((pdf, index) => (
            <div key={pdf.id}>
              <h3 className="text-lg font-medium text-gray-900 mb-3">
                {index === 0 ? 'First' : index === 1 ? 'Second' : `${index + 1}${['st', 'nd', 'rd'][index] || 'th'}`} PDF
              </h3>
              <PDFUploadBox pdf={pdf} />
            </div>
          ))}
          
          {/* Add PDF Button */}
          <div>
            <h3 className="text-lg font-medium text-gray-900 mb-3 opacity-0">Add</h3>
            <button
              onClick={addPDF}
              className="w-full h-full min-h-[200px] border-2 border-dashed border-gray-300 rounded-lg p-8 text-center hover:border-indigo-500 hover:bg-indigo-50 transition-all duration-200 bg-white flex items-center justify-center flex-col group"
            >
              <div className="text-indigo-600 group-hover:text-indigo-700">
                <PlusIcon />
              </div>
              <p className="mt-2 text-sm text-gray-600 group-hover:text-indigo-700">
                Add another PDF
              </p>
            </button>
          </div>
        </div>

        {/* Compare Button */}
        <div className="text-center">
          <button
            onClick={handleStartComparison}
            disabled={readyPdfCount < 2 || isComparing}
            className={`inline-flex items-center px-6 py-3 border border-transparent text-base font-medium rounded-md shadow-sm text-white 
                      ${readyPdfCount < 2 || isComparing
                        ? 'bg-gray-400 cursor-not-allowed'
                        : 'bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500'
                      } transition-colors duration-200`}
          >
            {isComparing ? (
              <>
                <LoadingIcon />
                <span className="ml-2">Starting comparison...</span>
              </>
            ) : (
              <>
                <svg className="w-5 h-5 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
                </svg>
                Compare {readyPdfCount > 0 ? readyPdfCount : ''} PDFs
              </>
            )}
          </button>
          {readyPdfCount === 1 && (
            <p className="mt-2 text-sm text-gray-600">Upload at least 2 PDFs to compare</p>
          )}
        </div>
        </div>
      </div>
    </div>
  );
} 