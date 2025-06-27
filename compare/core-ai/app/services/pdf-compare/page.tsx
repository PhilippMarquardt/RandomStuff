"use client"

import React, { useState, useEffect } from 'react';
import Link from 'next/link';
import Header from '@/app/components/Header';
import { PlusIcon, DocumentDuplicateIcon, FolderOpenIcon, HashtagIcon, CalendarIcon } from '@heroicons/react/24/outline';
import { API_BASE_URL } from '@/app/api/config';

interface WorkflowTemplate {
  filename: string;
  document: string;
  export_date: string;
  source_pdf: string;
  box_count: number;
}

const WorkflowList = () => {
  const [templates, setTemplates] = useState<WorkflowTemplate[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchTemplates = async () => {
      try {
        const response = await fetch(`${API_BASE_URL}/api/v1/templates/list-templates`);
        if (!response.ok) {
          throw new Error('Failed to fetch templates');
        }
        const data = await response.json();
        setTemplates(data);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'An unknown error occurred');
      } finally {
        setIsLoading(false);
      }
    };

    fetchTemplates();
  }, []);

  if (isLoading) {
    return <div className="text-center p-10">Loading saved workflows...</div>;
  }

  if (error) {
    return <div className="text-center p-10 text-red-500">Error: {error}</div>;
  }

  if (templates.length === 0) {
    return <div className="text-center p-10">No saved workflows found.</div>;
  }

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-6">
      {templates.map((template) => (
        <Link 
          href={`/services/pdf-compare/create?template=${encodeURIComponent(template.filename)}`}
          key={template.filename}
          className="block bg-white border border-gray-200 rounded-lg shadow-sm hover:shadow-md transition-shadow duration-200 overflow-hidden"
        >
          <div className="bg-gray-50 border-b border-gray-200 p-3">
            <img 
              src={`${API_BASE_URL}/api/v1/pdf/thumbnail?file_path=${encodeURIComponent(template.source_pdf)}`}
              alt={`Preview of ${template.document}`}
              className="w-full h-40 object-contain bg-white"
              onError={(e) => { e.currentTarget.src = '/placeholder.png'; e.currentTarget.alt = 'Preview not available'; }}
                                                 />
                                               </div>
          <div className="p-4">
            <h3 className="text-sm font-semibold text-gray-800 truncate" title={template.document}>
              {template.document}
            </h3>
            <div className="mt-2 space-y-2 text-xs text-gray-600">
              <p className="flex items-center"><HashtagIcon className="h-4 w-4 mr-2 text-gray-400"/> {template.box_count} annotations</p>
              <p className="flex items-center"><CalendarIcon className="h-4 w-4 mr-2 text-gray-400"/> {new Date(template.export_date).toLocaleDateString()}</p>
            </div>
          </div>
        </Link>
      ))}
        </div>
  );
};


const PDFCompareLandingPage = () => {
  const [view, setView] = useState<'default' | 'list'>('default');

  return (
    <div className="flex flex-col h-screen bg-gray-50">
      <Header
        title="PDF Comparison"
        showBackButton={true}
        backButtonText="Back to Services"
        backButtonPath="/services"
      />
      <div className="flex flex-1 overflow-hidden">
        {/* Sidebar */}
        <aside className="w-64 bg-white border-r border-gray-200 p-4">
          <nav className="space-y-1">
            <Link
              href="/services/pdf-compare/create"
              className="group flex items-center px-3 py-2 text-sm font-medium rounded-md text-gray-700 hover:bg-gray-100 hover:text-gray-900"
            >
              <PlusIcon className="h-6 w-6 mr-3 text-gray-500 group-hover:text-gray-600" />
              Create new template
            </Link>
          <button
              onClick={() => setView('list')}
              className="w-full group flex items-center px-3 py-2 text-sm font-medium rounded-md text-gray-700 hover:bg-gray-100 hover:text-gray-900"
                         >
              <FolderOpenIcon className="h-6 w-6 mr-3 text-gray-500 group-hover:text-gray-600" />
              Show saved workflows
          </button>
          </nav>
        </aside>

        {/* Main Content */}
        <main className="flex-1 p-6 overflow-y-auto">
          {view === 'default' && (
            <div className="text-center">
              <DocumentDuplicateIcon className="mx-auto h-12 w-12 text-gray-400" />
              <h2 className="mt-2 text-lg font-medium text-gray-900">Welcome to PDF Comparison</h2>
              <p className="mt-1 text-sm text-gray-500">
                Select an option from the sidebar to get started.
              </p>
                   </div>
          )}
          {view === 'list' && <WorkflowList />}
        </main>
      </div>
    </div>
  );
};

export default PDFCompareLandingPage; 