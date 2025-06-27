"use client"

import React, { useState, useEffect, useRef, useCallback } from 'react';
import dynamic from 'next/dynamic';
import { fileService, type PDFWordsData } from '../../../api/services/file-service';
import { ChatService } from '../../../api/services/chat-service';
import { API_BASE_URL } from '../../../api/config';
import type { AnnotationBox } from '../../../types/pdf-annotation';
import Header from '../../../components/Header';
import { UploadCloudIcon, LoadingIcon } from '@/app/components/icons';
import PDFAnnotationViewer from '@/app/components/PDFAnnotationViewer';
import { usePDFAnnotation } from '../../../hooks/usePDFAnnotation';
import { generateId } from '../../../utils/pdf-annotation';
import { ContextMenu } from '../../../components/pdf-annotation';
import { PDFAnnotationProvider, usePDFAnnotationSettings } from '../../../contexts/PDFAnnotationContext';
import { useSearchParams } from 'next/navigation';

// Dynamically import PDFAnnotationViewer with SSR disabled
const PDFAnnotationViewerComponent = dynamic(() => import('../../../components/PDFAnnotationViewer'), {
  ssr: false,
  loading: () => (
    <div className="flex items-center justify-center h-full">
      <div className="text-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-600 mx-auto mb-4"></div>
        <p className="text-gray-600">Loading PDF viewer...</p>
      </div>
    </div>
  )
});

interface PDFFile {
  id: string;
  file: File | null;
  wordsData: PDFWordsData | null;
  isLoading: boolean;
  error: string | null;
}

function PDFAnnotationPageContent() {
  const { settings, updateDefaultChatModel, updateDefaultVisionModel, setAvailableModels } = usePDFAnnotationSettings();
  const [pdf, setPdf] = useState<PDFFile>({
    id: '1',
    file: null,
    wordsData: null,
    isLoading: false,
    error: null
  });
  const [selectedBoxes, setSelectedBoxes] = useState<AnnotationBox[]>([]);
  const [availableModels, setLocalAvailableModels] = useState<string[]>([]);
  const [isLoadingModels, setIsLoadingModels] = useState<boolean>(false);
  
  const [numPages, setNumPages] = useState<number>(0);
  const [pageNumber, setPageNumber] = useState<number>(1);
  const [isDrawingMode, setIsDrawingMode] = useState<boolean>(false);
  const [contextMenu, setContextMenu] = useState<{ x: number; y: number; show: boolean }>({ x: 0, y: 0, show: false });

  const fileInputRef = useRef<HTMLInputElement>(null);
  const chatService = new ChatService();

  const [isLoadingTemplate, setIsLoadingTemplate] = useState(false);
  const [annotationsToLoad, setAnnotationsToLoad] = useState<AnnotationBox[] | null>(null);

  const searchParams = useSearchParams();

  const handleSelectBoxes = useCallback((boxes: AnnotationBox[]) => {
    setSelectedBoxes(boxes);
  }, []);

  const {
    annotationBoxes,
    currentPageBoxes,
    selectionState,
    setSelectionState,
    drawingState,
    setDrawingState,
    updateAnnotationBox,
    deleteAnnotationBox,
    addAnnotationBox,
    loadAnnotationBoxes,
    groupBoxes,
    selectBoxesInArea
  } = usePDFAnnotation({ 
    wordsData: pdf.wordsData, 
    pageNumber, 
    onSelectBoxes: handleSelectBoxes,
    defaultSettings: settings
  });

  const handleFileUpload = async (file: File) => {
    setPdf(prev => ({ ...prev, file, isLoading: true, error: null }));
    loadAnnotationBoxes([]); // Clear existing boxes
    setSelectedBoxes([]);
    
    try {
      const wordsData = await fileService.extractPDFWords(file);
      setPdf(prev => ({ ...prev, wordsData, isLoading: false }));
      setPageNumber(1);
    } catch (error) {
      setPdf(prev => ({ 
        ...prev, 
              isLoading: false, 
        error: `Failed to extract PDF words: ${error instanceof Error ? error.message : 'Unknown error'}`
      }));
    }
  };

  const handleDrop = useCallback((e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    const files = e.dataTransfer.files;
    if (files.length > 0 && files[0].type === 'application/pdf') {
      handleFileUpload(files[0]);
    }
  }, []);

  const handleDragOver = useCallback((e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
  }, []);

  const handleFileSelect = () => {
    fileInputRef.current?.click();
  };

  const handleFileInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (files && files.length > 0) {
      handleFileUpload(files[0]);
    }
  };

  const handleUpdateAnnotationBox = useCallback((id: string, updates: Partial<AnnotationBox>) => {
    updateAnnotationBox(id, updates);
    setSelectedBoxes(prev => prev.map(box => 
      box.id === id ? { ...box, ...updates } as AnnotationBox : box
    ));
  }, [updateAnnotationBox]);
  
  const handleDeleteAnnotationBox = useCallback((id: string) => {
    deleteAnnotationBox(id);
    setSelectedBoxes(selectedBoxes.filter(box => box.id !== id));
  }, [selectedBoxes, deleteAnnotationBox]);

  const handleGroupBoxes = useCallback(() => {
    const groupedBox = groupBoxes(selectedBoxes);
    if (groupedBox) {
      setSelectedBoxes([groupedBox]);
    } else {
      console.log('Grouping failed: Cannot combine different box types');
    }
    setContextMenu({ x: 0, y: 0, show: false });
  }, [selectedBoxes, groupBoxes]);

  useEffect(() => {
    const handleClickOutside = () => setContextMenu({ x: 0, y: 0, show: false });
    if (contextMenu.show) {
      document.addEventListener('click', handleClickOutside);
      return () => document.removeEventListener('click', handleClickOutside);
    }
  }, [contextMenu.show]);

  const handleExportToJson = async () => {
    if (!pdf.file || annotationBoxes.length === 0) return;

    console.log("Starting export process, preparing data...");

    try {
      const boxesToExport = await Promise.all(
        annotationBoxes.map(async (box) => {
          const cleanSettings: Partial<AnnotationBox['settings']> = {};
          const originalSettings = box.settings;

          // Basic settings that are always present
          cleanSettings.mustMatchExactly = originalSettings.mustMatchExactly;
          cleanSettings.positionIsNotGuaranteed = originalSettings.positionIsNotGuaranteed;

          // Conditional settings based on UI logic
          if (originalSettings.positionIsNotGuaranteed) {
            cleanSettings.useVisionModel = originalSettings.useVisionModel;
            if (cleanSettings.useVisionModel) {
              if (originalSettings.visionModel && originalSettings.visionModel !== 'None') {
                cleanSettings.visionModel = originalSettings.visionModel;
                cleanSettings.visionTaskDescription = originalSettings.visionTaskDescription || '';
              }
            }
            if (originalSettings.comparisonModel && originalSettings.comparisonModel !== 'None') {
              cleanSettings.comparisonModel = originalSettings.comparisonModel;
              cleanSettings.comparisonTaskDescription = originalSettings.comparisonTaskDescription || '';
            }
            cleanSettings.guideWithTextIfAvailable = originalSettings.guideWithTextIfAvailable !== false;
            
            // Extract reference text if guide with text is enabled
            if (cleanSettings.guideWithTextIfAvailable && pdf.file) {
              try {
                // Create a temporary endpoint call to extract text with layout
                const formData = new FormData();
                formData.append('file', pdf.file);
                formData.append('page_num', String(box.page));
                formData.append('bbox', JSON.stringify([box.x, box.y, box.x + box.width, box.y + box.height]));
                
                const response = await fetch(`${API_BASE_URL}/api/v1/pdf/extract-text-with-layout`, {
                  method: 'POST',
                  body: formData,
                });
                
                if (response.ok) {
                  const result = await response.json();
                  cleanSettings.referenceGuidingText = result.text;
                } else {
                  console.error('Failed to extract reference text');
                  cleanSettings.referenceGuidingText = '';
                }
              } catch (error) {
                console.error('Error extracting reference text:', error);
                cleanSettings.referenceGuidingText = '';
              }
            }
          } else {
            cleanSettings.useVisionModel = originalSettings.useVisionModel;
            if (originalSettings.useVisionModel) {
              if (originalSettings.visionModel && originalSettings.visionModel !== 'None') {
                cleanSettings.visionModel = originalSettings.visionModel;
                cleanSettings.visionTaskDescription = originalSettings.visionTaskDescription || '';
                cleanSettings.guideWithTextIfAvailable = originalSettings.guideWithTextIfAvailable !== false;
              }
            } else if (!originalSettings.mustMatchExactly) {
              if (originalSettings.chatModel) {
                cleanSettings.chatModel = originalSettings.chatModel;
                cleanSettings.chatTaskDescription = originalSettings.chatTaskDescription || '';
              }
            }
          }

          // Image extraction for any box using a vision model
          if (cleanSettings.useVisionModel) {
            try {
              const base64Image = await fileService.extractImageFromRegion(
                pdf.file as File,
                box.page,
                [box.x, box.y, box.x + box.width, box.y + box.height]
              );
              cleanSettings.base64Image = base64Image;
            } catch (error) {
              console.error(`Failed to extract image for box ${box.id}:`, error);
              cleanSettings.base64Image = `Error: ${(error as Error).message}`;
            }
          }

          // Return a new box object with the cleaned settings
          return {
            ...box,
            settings: cleanSettings,
          };
        })
      );

      console.log("Data processing complete. Generating JSON...");

      const dataToExport = {
        document: pdf.file.name,
        exportDate: new Date().toISOString(),
        annotationBoxes: boxesToExport,
      };
      
      // Save to server
      try {
        const formData = new FormData();
        const jsonString = JSON.stringify(dataToExport);
        const jsonBlob = new Blob([jsonString], { type: 'application/json' });
        
        formData.append('template_file', jsonBlob, 'template.json');
        formData.append('pdf_file', pdf.file);

        const response = await fetch(`${API_BASE_URL}/api/v1/templates/save-template`, {
          method: 'POST',
          body: formData, // No 'Content-Type' header needed, browser sets it for FormData
        });

        if (response.ok) {
          const result = await response.json();
          console.log('Template and PDF saved successfully on server:', result);
          // Optional: Show success message to user
        } else {
          const errorResult = await response.json();
          console.error('Failed to save template on server:', errorResult.detail);
          // Optional: Show error message to user
        }
      } catch (serverError) {
        console.error('Error sending template to server:', serverError);
      }

      // Download JSON locally for debugging
      const jsonString = JSON.stringify(dataToExport, null, 2);
      const blob = new Blob([jsonString], { type: "application/json" });
      const url = URL.createObjectURL(blob);
      
      const link = document.createElement('a');
      link.href = url;
      link.download = `workflow-${pdf.file.name}.json`;
      
      document.body.appendChild(link);
      link.click();
      
      document.body.removeChild(link);
      URL.revokeObjectURL(url);

      console.log("Local export successful.");

    } catch (exportError) {
      console.error("Failed to export JSON:", exportError);
      // Handle export error (e.g., show a notification to the user)
    }
  };

  // Fetch available models on component mount
  useEffect(() => {
    const fetchModels = async () => {
      setIsLoadingModels(true);
      try {
        const models = await chatService.fetchModels();
        setLocalAvailableModels(models);
        setAvailableModels(models); // Update context
      } catch (error) {
        console.error('Failed to fetch models:', error);
        // Fall back to default models if fetch fails
        setLocalAvailableModels([]);
        setAvailableModels([]); // Update context
      } finally {
        setIsLoadingModels(false);
      }
    };

    fetchModels();
  }, [setAvailableModels]);

  // Effect to load template from URL
  useEffect(() => {
    const loadTemplate = async (templateFilename: string) => {
      setIsLoadingTemplate(true);
      try {
        const templateRes = await fetch(`${API_BASE_URL}/api/v1/templates/${templateFilename}`);
        if (!templateRes.ok) throw new Error(`Failed to fetch template: ${templateRes.statusText}`);
        const templateData = await templateRes.json();

        if (templateData.source_pdf) {
          const pdfFilename = templateData.source_pdf.split('/').pop().split('\\').pop();
          const pdfRes = await fetch(`${API_BASE_URL}/api/v1/data/${pdfFilename}`);
          if (!pdfRes.ok) throw new Error(`Failed to fetch source PDF: ${pdfRes.statusText}`);
          
          const pdfBlob = await pdfRes.blob();
          const pdfFile = new File([pdfBlob], templateData.document, { type: 'application/pdf' });
          
          await handleFileUpload(pdfFile);
          
          setAnnotationsToLoad(templateData.annotationBoxes || []);
        }
      } catch (error) {
        console.error("Failed to load template", error);
        setPdf(prev => ({ ...prev, error: (error as Error).message }));
      } finally {
        setIsLoadingTemplate(false);
      }
    };

    const templateFilename = searchParams.get('template');
    if (templateFilename) {
      loadTemplate(templateFilename);
    }
  }, [searchParams]);

  // Effect to apply annotations once PDF is processed
  useEffect(() => {
    if (annotationsToLoad && pdf.wordsData) {
      loadAnnotationBoxes(annotationsToLoad);
      setAnnotationsToLoad(null);
    }
  }, [annotationsToLoad, pdf.wordsData, loadAnnotationBoxes]);

  return (
    <div className="flex flex-col h-screen bg-[#FAFBFC] text-gray-800">
             <Header 
         title="PDF Workflow Designer"
         showBackButton={true}
         backButtonText="Back to Services"
         backButtonPath="/services"
       />

             <div className="flex-1 flex relative">
         {isLoadingTemplate && (
           <div className="absolute inset-0 bg-white bg-opacity-75 flex items-center justify-center z-50">
             <div className="text-center">
               <LoadingIcon />
               <p className="mt-4 text-lg text-gray-600">Loading template...</p>
             </div>
           </div>
         )}
         {!pdf.file ? (
           // Upload Area
           <div className="flex-1 flex items-center justify-center p-6">
             <div className="max-w-md w-full">
      <div
                 onDrop={handleDrop}
        onDragOver={handleDragOver}
                 className="border-2 border-dashed border-gray-300 rounded-lg p-12 text-center hover:border-indigo-500 transition-colors duration-200 bg-white cursor-pointer"
                 onClick={handleFileSelect}
      >
        <input
                   ref={fileInputRef}
          type="file"
          accept="application/pdf"
                   onChange={handleFileInputChange}
          className="hidden"
        />
        
        {pdf.isLoading ? (
          <div className="flex flex-col items-center">
            <LoadingIcon />
                     <p className="mt-4 text-lg text-gray-600">Extracting PDF words...</p>
                     <p className="mt-2 text-sm text-gray-500">This may take a moment</p>
          </div>
        ) : (
                   <>
            <UploadCloudIcon />
                     <p className="mt-4 text-lg text-gray-600">
              Drop PDF here or <span className="text-indigo-600">browse</span>
            </p>
                     <p className="text-sm text-gray-500 mt-2">PDF files only</p>
                   </>
        )}
        
        {pdf.error && (
                   <p className="mt-4 text-sm text-red-600">{pdf.error}</p>
        )}
      </div>
    </div>
           </div>
         ) : (
           <>
             {/* Main PDF Viewer Area */}
             <div className="flex-1">
                               <PDFAnnotationViewerComponent
                  pdfFile={pdf.file}
                  wordsData={pdf.wordsData}
                  isLoading={pdf.isLoading}
                  selectedBoxes={selectedBoxes}
                  onSelectBoxes={handleSelectBoxes}
                  onUpdateAnnotationBox={handleUpdateAnnotationBox}
                  numPages={numPages}
                  setNumPages={setNumPages}
                  pageNumber={pageNumber}
                  setPageNumber={setPageNumber}
                  isDrawingMode={isDrawingMode}
                  setIsDrawingMode={setIsDrawingMode}
                  contextMenu={contextMenu}
                  setContextMenu={setContextMenu}
                  currentPageBoxes={currentPageBoxes}
                  selectionState={selectionState}
                  setSelectionState={setSelectionState}
                  drawingState={drawingState}
                  setDrawingState={setDrawingState}
                  deleteAnnotationBox={handleDeleteAnnotationBox}
                  addAnnotationBox={addAnnotationBox}
                  selectBoxesInArea={selectBoxesInArea}
                />
             </div>

             {/* Right Sidebar - Tools */}
             <div className="w-80 bg-white border-l border-gray-200 p-4 overflow-y-auto">
               <div className="flex items-center justify-between mb-4">
                 <h3 className="text-lg font-semibold text-gray-900">Annotation Tools</h3>
                 <button
                   onClick={() => setPdf({ id: '1', file: null, wordsData: null, isLoading: false, error: null })}
                   className="px-3 py-1 text-xs text-gray-600 hover:text-gray-800 border border-gray-300 rounded hover:bg-gray-50"
                 >
                   Upload Different PDF
                 </button>
               </div>

                <div className="mb-4">
                  <button
                    onClick={handleExportToJson}
                    className="w-full inline-flex items-center justify-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500"
                    disabled={!pdf.file}
                  >
                    <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
                    </svg>
                    Export to JSON
                  </button>
                </div>

                                {pdf.wordsData && (
                   <div className="space-y-4">
                     {/* Selection Properties Panel */}
                     {selectedBoxes.length > 0 ? (
                       <div className="bg-indigo-50 p-3 rounded-lg border border-indigo-200">
                         <h4 className="font-medium text-gray-900 mb-3">
                           {selectedBoxes.length === 1 
                             ? `${
                                 selectedBoxes[0].type === 'word' ? 'Word Box' :
                                 selectedBoxes[0].type === 'image' ? 'Image Box' :
                                 'Custom Box'
                               } Properties`
                             : `${selectedBoxes.length} Boxes Selected`
                           }
                         </h4>
                         
                         {selectedBoxes.length === 1 ? (
                           <div className="space-y-3">
                                                            {/* Box Info */}
                             <div className="space-y-2 text-sm text-gray-600">
                               <p><span className="font-medium">Type:</span> {
                                 selectedBoxes[0].type === 'word' ? 'Word Detection Box' :
                                 selectedBoxes[0].type === 'image' ? 'Image Box' :
                                 'Custom Box'
                               }</p>
                               <p><span className="font-medium">Size:</span> {selectedBoxes[0].width.toFixed(0)}×{selectedBoxes[0].height.toFixed(0)}</p>
                               <p><span className="font-medium">Position:</span> ({selectedBoxes[0].x.toFixed(0)}, {selectedBoxes[0].y.toFixed(0)})</p>
                               {selectedBoxes[0].originalData?.area && (
                                 <p><span className="font-medium">Area:</span> {selectedBoxes[0].originalData.area.toFixed(0)}</p>
                               )}
                             </div>
                             
                             {/* Box Settings */}
                             <div className="space-y-3">
                               <div>
                                 <label className="flex items-center space-x-2">
                                   <input
                                     type="checkbox"
                                     checked={selectedBoxes[0].settings?.positionIsNotGuaranteed || false}
                                     onChange={(e) => {
                                      const isChecked = e.target.checked;
                                      handleUpdateAnnotationBox(selectedBoxes[0].id, {
                                        settings: {
                                          ...selectedBoxes[0].settings,
                                          positionIsNotGuaranteed: isChecked
                                        }
                                      })
                                     }}
                                     className="rounded border-gray-300 text-indigo-600 focus:ring-indigo-500"
                                   />
                                   <span className="text-sm font-medium text-gray-900">Position is not Guarenteed</span>
                                 </label>
                                 <p className="text-xs text-gray-500 ml-6">
                                   Allows the workflow to find this element elsewhere in the document
                                 </p>
        </div>

                               <div>
                                 <label className="flex items-center space-x-2">
                                   <input
                                     type="checkbox"
                                     checked={selectedBoxes[0].settings?.mustMatchExactly || false}
                                     disabled={!selectedBoxes[0].settings?.canMatchExactly}
                                     onChange={(e) => handleUpdateAnnotationBox(selectedBoxes[0].id, {
                                       settings: {
                                         ...selectedBoxes[0].settings,
                                         mustMatchExactly: e.target.checked
                                       }
                                     })}
                                     className={`rounded border-gray-300 text-indigo-600 focus:ring-indigo-500 ${
                                       !selectedBoxes[0].settings?.canMatchExactly 
                                         ? 'opacity-50 cursor-not-allowed' 
                                         : ''
                                     }`}
                                   />
                                   <span className={`text-sm font-medium ${
                                     selectedBoxes[0].settings?.canMatchExactly 
                                       ? 'text-gray-900' 
                                       : 'text-gray-400'
                                   }`}>
                                     Must Match Exactly
                                   </span>
                                 </label>
                                 <p className="text-xs text-gray-500 ml-6">
                                   {selectedBoxes[0].settings?.canMatchExactly 
                                     ? 'Text in this region must match exactly when comparing documents'
                                     : 'Only available for extracted text regions'
                                   }
                                 </p>
      </div>

                               {/* LLM Settings - For any box when not using exact matching */}
                               {!selectedBoxes[0].settings.mustMatchExactly && (
                                 <div className="pt-3 border-t border-gray-200">
                                   <div className="space-y-3">
                                     {/* Use Vision Model Toggle */}
                                     <div>
                                       <label className="flex items-center space-x-2">
                                         <input
                                           type="checkbox"
                                           checked={selectedBoxes[0].settings.useVisionModel}
                                           onChange={(e) => handleUpdateAnnotationBox(selectedBoxes[0].id, {
                                             settings: {
                                               ...selectedBoxes[0].settings,
                                               useVisionModel: e.target.checked
                                             }
                                           })}
                                           className="rounded border-gray-300 text-indigo-600 focus:ring-indigo-500"
                                         />
                                         <span className="text-sm font-medium text-gray-900">Use Vision Model</span>
                                       </label>
                                     </div>

                                     {selectedBoxes[0].settings.positionIsNotGuaranteed ? (
                                      <>
                                        {/* Extraction Model Section */}
                                        <div className="pl-6 border-l-2 border-gray-200 ml-1">
                                         <h5 className="text-sm font-medium text-gray-900 mb-2">Extraction Model</h5>
                                         <div className="space-y-3">
                                           <div>
                                             <label className="block text-xs font-medium text-gray-700 mb-1">
                                               Exctraction Model
                                             </label>
                                             <select
                                                value={selectedBoxes[0].settings.visionModel || 'None'}
                                                onChange={(e) => {
                                                  handleUpdateAnnotationBox(selectedBoxes[0].id, {
                                                    settings: {
                                                      ...selectedBoxes[0].settings,
                                                      visionModel: e.target.value,
                                                    }
                                                  });
                                                  // Update default for future boxes
                                                  if (e.target.value !== 'None') {
                                                    updateDefaultVisionModel(e.target.value);
                                                  }
                                                }}
                                               className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:ring-indigo-500 focus:border-indigo-500"
                                                disabled={isLoadingModels}
                                              >
                                               <option value="None">None</option>
                                                {isLoadingModels ? (
                                                  <option disabled>Loading models...</option>
                                                ) : (
                                                  availableModels.map(model => (
                                                    <option key={model} value={model}>{model}</option>
                                                  ))
                                                )}
                                             </select>
                                           </div>
                                           <div>
                                             <label className="flex items-center space-x-2">
                                               <input
                                                 type="checkbox"
                                                 checked={selectedBoxes[0].settings.guideWithTextIfAvailable !== false}
                                                 onChange={(e) => handleUpdateAnnotationBox(selectedBoxes[0].id, {
                                                   settings: {
                                                     ...selectedBoxes[0].settings,
                                                     guideWithTextIfAvailable: e.target.checked
                                                   }
                                                 })}
                                                 className="rounded border-gray-300 text-indigo-600 focus:ring-indigo-500"
                                               />
                                               <span className="text-sm font-medium text-gray-900">Guide with extracted text</span>
                                             </label>
                                             <p className="text-xs text-gray-500 ml-6">
                                               Use text content to help find matching elements across documents
                                             </p>
                                           </div>
                                            <div>
                                              <label className="block text-xs font-medium text-gray-700 mb-1">
                                                Extraction Instruction
                                              </label>
                                              <textarea
                                                value={selectedBoxes[0].settings.visionTaskDescription || ''}
                                                onChange={(e) => handleUpdateAnnotationBox(selectedBoxes[0].id, {
                                                  settings: {
                                                    ...selectedBoxes[0].settings,
                                                    visionTaskDescription: e.target.value
                                                  }
                                                })}
                                                placeholder="describe how to extract information for that graph"
                                                className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:ring-indigo-500 focus:border-indigo-500 resize-none"
                                                rows={3}
                                              />
                                            </div>
                                          </div>
                                        </div>

                                        {/* Comparison Model Section */}
                                        <div className="pl-6 border-l-2 border-gray-200 ml-1 mt-4">
                                         <h5 className="text-sm font-medium text-gray-900 mb-2">Comparison Model</h5>
                                         <div className="space-y-3">
                                           <div>
                                             <label className="block text-xs font-medium text-gray-700 mb-1">
                                               Comparison Model
                                             </label>
                                             <select
                                                value={selectedBoxes[0].settings.comparisonModel || 'None'}
                                                onChange={(e) => {
                                                  handleUpdateAnnotationBox(selectedBoxes[0].id, {
                                                    settings: {
                                                      ...selectedBoxes[0].settings,
                                                      comparisonModel: e.target.value,
                                                    }
                                                  });
                                                  // Update default for future boxes
                                                  if (e.target.value !== 'None') {
                                                    updateDefaultChatModel(e.target.value);
                                                  }
                                                }}
                                               className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:ring-indigo-500 focus:border-indigo-500"
                                                disabled={isLoadingModels}
                                              >
                                               <option value="None">None</option>
                                                {isLoadingModels ? (
                                                  <option disabled>Loading models...</option>
                                                ) : (
                                                  availableModels.map(model => (
                                                    <option key={model} value={model}>{model}</option>
                                                  ))
                                                )}
                                             </select>
                                           </div>
                                            <div>
                                              <label className="block text-xs font-medium text-gray-700 mb-1">
                                                Comparison Instruction
                                              </label>
                                              <textarea
                                                value={selectedBoxes[0].settings.comparisonTaskDescription || ''}
                                                onChange={(e) => handleUpdateAnnotationBox(selectedBoxes[0].id, {
                                                  settings: {
                                                    ...selectedBoxes[0].settings,
                                                    comparisonTaskDescription: e.target.value
                                                  }
                                                })}
                                                placeholder="described how you want the final comparison to be done given the extracted data"
                                                className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:ring-indigo-500 focus:border-indigo-500 resize-none"
                                                rows={3}
                                              />
                                            </div>
                                          </div>
                                        </div>
                                      </>
                                     ) : (
                                      <>
                                        {/* Vision Model Section */}
                                        {selectedBoxes[0].settings.useVisionModel && (
                                          <div className="pl-6 border-l-2 border-gray-200 ml-1">
                                            <h5 className="text-sm font-medium text-gray-900 mb-2">Vision Analysis</h5>
                                            <div className="space-y-3">
                                              <div>
                                                <label className="block text-xs font-medium text-gray-700 mb-1">
                                                  Vision Model
                                                </label>
                                                <select
                                                  value={selectedBoxes[0].settings.visionModel || 'None'}
                                                  onChange={(e) => {
                                                    handleUpdateAnnotationBox(selectedBoxes[0].id, {
                                                      settings: {
                                                        ...selectedBoxes[0].settings,
                                                        visionModel: e.target.value,
                                                        ...(e.target.value === 'None' && { visionTaskDescription: '' })
                                                      }
                                                    });
                                                    // Update default for future boxes
                                                    if (e.target.value !== 'None') {
                                                      updateDefaultVisionModel(e.target.value);
                                                    }
                                                  }}
                                                  className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:ring-indigo-500 focus:border-indigo-500"
                                                  disabled={isLoadingModels}
          >
                                                  <option value="None">None</option>
                                                  {isLoadingModels ? (
                                                    <option disabled>Loading models...</option>
                                                  ) : (
                                                    availableModels.map(model => (
                                                      <option key={model} value={model}>{model}</option>
                                                    ))
                                                  )}
                                                </select>
                                              </div>
                                              
                                              {selectedBoxes[0].settings.visionModel && selectedBoxes[0].settings.visionModel !== 'None' && (
                                                <>
                                                  <div>
                                                    <label className="flex items-center space-x-2">
                                                      <input
                                                        type="checkbox"
                                                        checked={selectedBoxes[0].settings.guideWithTextIfAvailable !== false}
                                                        onChange={(e) => handleUpdateAnnotationBox(selectedBoxes[0].id, {
                                                          settings: {
                                                            ...selectedBoxes[0].settings,
                                                            guideWithTextIfAvailable: e.target.checked
                                                          }
                                                        })}
                                                        className="rounded border-gray-300 text-indigo-600 focus:ring-indigo-500"
                                                      />
                                                      <span className="text-sm font-medium text-gray-900">Guide with text if available</span>
                                                    </label>
                                                  </div>
                                                  <div>
                                                    <label className="block text-xs font-medium text-gray-700 mb-1">
                                                      Vision Task Description
                                                    </label>
                                                    <textarea
                                                      value={selectedBoxes[0].settings.visionTaskDescription || ''}
                                                      onChange={(e) => handleUpdateAnnotationBox(selectedBoxes[0].id, {
                                                        settings: {
                                                          ...selectedBoxes[0].settings,
                                                          visionTaskDescription: e.target.value
                                                        }
                                                      })}
                                                      placeholder="Describe what the vision model should do..."
                                                      className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:ring-indigo-500 focus:border-indigo-500 resize-none"
                                                      rows={3}
                                                    />
                                                  </div>
                                                </>
                                              )}
                                            </div>
                                          </div>
                                        )}

                                        {/* Chat Model Section - only shown if vision is not used */}
                                        {!selectedBoxes[0].settings.useVisionModel && (
                                          <div className={`pt-3 mt-3 border-t border-gray-200`}>
                                            <h5 className="text-sm font-medium text-gray-900 mb-2">Chat Model</h5>
                                            <div className="space-y-3">
                                              <div>
                                                <label className="block text-xs font-medium text-gray-700 mb-1">
                                                  Model
                                                </label>
                                                <select
                                                  value={selectedBoxes[0].settings.chatModel || ''}
                                                  onChange={(e) => {
                                                    handleUpdateAnnotationBox(selectedBoxes[0].id, {
                                                      settings: {
                                                        ...selectedBoxes[0].settings,
                                                        chatModel: e.target.value
                                                      }
                                                    });
                                                    // Update default for future boxes
                                                    updateDefaultChatModel(e.target.value);
                                                  }}
                                                  className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:ring-indigo-500 focus:border-indigo-500"
                                                  disabled={isLoadingModels}
                                                >
                                                  {isLoadingModels ? (
                                                    <option disabled>Loading models...</option>
                                                  ) : (
                                                    availableModels.map(model => (
                                                      <option key={model} value={model}>{model}</option>
                                                    ))
                                                  )}
                                                </select>
                                              </div>
                                              <div>
                                                <label className="block text-xs font-medium text-gray-700 mb-1">
                                                  Chat Task Description
            </label>
            <textarea
                                                  value={selectedBoxes[0].settings.chatTaskDescription || ''}
                                                  onChange={(e) => handleUpdateAnnotationBox(selectedBoxes[0].id, {
                                                    settings: {
                                                      ...selectedBoxes[0].settings,
                                                      chatTaskDescription: e.target.value
                                                    }
                                                  })}
                                                  placeholder="Describe how the chat model should process the result..."
                                                  className="w--full px-3 py-2 border border-gray-300 rounded-md text-sm focus:ring-indigo-500 focus:border-indigo-500 resize-none"
              rows={4}
            />
          </div>
                                            </div>
                                          </div>
                                        )}
                                      </>
                                     )}
                                   </div>
                                 </div>
                               )}
                             </div>
                           </div>
                         ) : (
                           <div className="space-y-3">
                             {/* Multi-selection Info */}
                             <div className="space-y-2 text-sm">
                               <p><span className="font-medium">Word boxes:</span> {selectedBoxes.filter(b => b.type === 'word').length}</p>
                               <p><span className="font-medium">Image boxes:</span> {selectedBoxes.filter(b => b.type === 'image').length}</p>
                               <p><span className="font-medium">Custom boxes:</span> {selectedBoxes.filter(b => b.type === 'custom').length}</p>
                             </div>

                             {/* Bulk Settings */}
                             <div className="space-y-3 pt-2 border-t border-indigo-200">
                               <h5 className="text-sm font-medium text-gray-900">Apply to All Selected:</h5>
                               
                               <div>
                                 <label className="flex items-center space-x-2">
                                   <input
                                     type="checkbox"
                                     checked={selectedBoxes.every(box => box.settings?.positionIsNotGuaranteed)}
                                     ref={(input) => {
                                       if (input) {
                                         const someChecked = selectedBoxes.some(box => box.settings?.positionIsNotGuaranteed);
                                         const allChecked = selectedBoxes.every(box => box.settings?.positionIsNotGuaranteed);
                                         input.indeterminate = someChecked && !allChecked;
                                       }
                                     }}
                                     onChange={(e) => {
                                       selectedBoxes.forEach(box => {
                                         handleUpdateAnnotationBox(box.id, {
                                           settings: {
                                             ...box.settings,
                                             positionIsNotGuaranteed: e.target.checked
                                           }
                                         });
                                       });
                                     }}
                                     className="rounded border-gray-300 text-indigo-600 focus:ring-indigo-500"
                                   />
                                   <span className="text-sm font-medium text-gray-900">Position is not Guarenteed</span>
                                 </label>
            </div>
          
          <div>
                                 <label className="flex items-center space-x-2">
                                   <input
                                     type="checkbox"
                                     checked={selectedBoxes.filter(b => b.settings?.canMatchExactly).every(box => box.settings?.mustMatchExactly)}
                                     disabled={!selectedBoxes.some(b => b.settings?.canMatchExactly)}
                                     ref={(input) => {
                                       if (input) {
                                         const eligibleBoxes = selectedBoxes.filter(b => b.settings?.canMatchExactly);
                                         if (eligibleBoxes.length > 0) {
                                           const someChecked = eligibleBoxes.some(box => box.settings?.mustMatchExactly);
                                           const allChecked = eligibleBoxes.every(box => box.settings?.mustMatchExactly);
                                           input.indeterminate = someChecked && !allChecked;
                                         }
                                       }
                                     }}
                                     onChange={(e) => {
                                       selectedBoxes.forEach(box => {
                                         if (box.settings?.canMatchExactly) {
                                           handleUpdateAnnotationBox(box.id, {
                                             settings: {
                                               ...box.settings,
                                               mustMatchExactly: e.target.checked
                                             }
                                           });
                                         }
                                       });
                                     }}
                                     className={`rounded border-gray-300 text-indigo-600 focus:ring-indigo-500 ${
                                       !selectedBoxes.some(b => b.settings?.canMatchExactly)
                                         ? 'opacity-50 cursor-not-allowed' 
                                         : ''
                                     }`}
                                   />
                                   <span className={`text-sm font-medium ${
                                     selectedBoxes.some(b => b.settings?.canMatchExactly)
                                       ? 'text-gray-900' 
                                       : 'text-gray-400'
                                   }`}>
                                     Must Match Exactly
                                   </span>
                                 </label>
          </div>
        </div>

                               {/* Bulk LLM Settings - For boxes not using exact matching */}
                               {selectedBoxes.some(box => !box.settings.mustMatchExactly) && (
                                 <div className="space-y-3 pt-2 border-t border-indigo-200">
                                   <h5 className="text-sm font-medium text-gray-900">Bulk AI Model Settings:</h5>
                                   
                                   {/* Bulk Vision Model */}
                                   <div className="space-y-1">
                                     <label className="block text-xs font-medium text-gray-700">Vision Model</label>
                                     <select
                                       onChange={(e) => {
                                         selectedBoxes.forEach(box => {
                                           handleUpdateAnnotationBox(box.id, {
                                             settings: { ...box.settings, visionModel: e.target.value }
                                           });
                                         });
                                       }}
                                       className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:ring-indigo-500 focus:border-indigo-500"
                                       disabled={isLoadingModels}
                                     >
                                       <option value="">(No Change)</option>
                                       <option value="None">None</option>
                                       {isLoadingModels ? (
                                         <option disabled>Loading models...</option>
                                       ) : (
                                         availableModels.map(model => (
                                           <option key={model} value={model}>{model}</option>
                                         ))
                                       )}
                                     </select>
                                   </div>

                                   <div className="pl-2 mt-1">
                                     <label className="flex items-center space-x-2">
                                       <input
                                         type="checkbox"
                                         checked={selectedBoxes.every(box => box.settings?.guideWithTextIfAvailable !== false)}
                                         ref={(input) => {
                                           if (input) {
                                             const someChecked = selectedBoxes.some(box => box.settings?.guideWithTextIfAvailable !== false);
                                             const allChecked = selectedBoxes.every(box => box.settings?.guideWithTextIfAvailable !== false);
                                             input.indeterminate = someChecked && !allChecked;
                                           }
                                         }}
                                         onChange={(e) => {
                                           selectedBoxes.forEach(box => {
                                             handleUpdateAnnotationBox(box.id, {
                                               settings: {
                                                 ...box.settings,
                                                 guideWithTextIfAvailable: e.target.checked
                                               }
                                             });
                                           });
                                         }}
                                         className="rounded border-gray-300 text-indigo-600 focus:ring-indigo-500"
                                       />
                                       <span className="text-sm text-gray-700">Guide with text</span>
                                     </label>
                                   </div>

                                   {/* Bulk Chat Model */}
                                   <div className="space-y-1">
                                     <label className="block text-xs font-medium text-gray-700">Chat Model</label>
                                     <select
                                       onChange={(e) => {
                                         selectedBoxes.forEach(box => {
                                           handleUpdateAnnotationBox(box.id, {
                                             settings: { ...box.settings, chatModel: e.target.value }
                                           });
                                         });
                                       }}
                                       className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:ring-indigo-500 focus:border-indigo-500"
                                       disabled={isLoadingModels}
                                     >
                                       <option value="">(No Change)</option>
                                       {isLoadingModels ? (
                                         <option disabled>Loading models...</option>
                                       ) : (
                                         availableModels.map(model => (
                                           <option key={model} value={model}>{model}</option>
                                         ))
                                       )}
                                     </select>
                                   </div>
                                 </div>
                               )}

                             {/* Grouping Info */}
                             <div className="pt-2 border-t border-indigo-200">
                               <p className="text-xs text-gray-600">Right-click to group multiple boxes together</p>
                             </div>
                           </div>
                         )}

          <button
                           onClick={() => setSelectedBoxes([])}
                           className="mt-3 text-xs text-gray-500 hover:text-gray-700"
                         >
                           Clear selection
          </button>
                       </div>
                     ) : (
                       <div className="bg-gray-50 p-3 rounded-lg">
                         <h4 className="font-medium text-gray-900 mb-2">Selection</h4>
                         <p className="text-sm text-gray-600">
                           Draw a rectangle to select multiple boxes, or click individual boxes. 
                           Right-click selected boxes to group them.
                         </p>
                       </div>
                     )}

                     
                   </div>
          )}
        </div>
           </>
         )}
      </div>

       <ContextMenu
        show={contextMenu.show}
        x={contextMenu.x}
        y={contextMenu.y}
        selectedBoxes={selectedBoxes}
        onGroup={handleGroupBoxes}
        onHide={() => setContextMenu({ x: 0, y: 0, show: false })}
      />
    </div>
  );
}

export default function PDFAnnotationPage() {
  return (
    <PDFAnnotationProvider>
      <PDFAnnotationPageContent />
    </PDFAnnotationProvider>
  );
} 