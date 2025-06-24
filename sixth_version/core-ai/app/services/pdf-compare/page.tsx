"use client"

import React, { useState, useEffect, useRef, useCallback } from 'react';
import dynamic from 'next/dynamic';
import { fileService, type PDFWordsData } from '../../api/services/file-service';
import { ChatService } from '../../api/services/chat-service';
import type { AnnotationBox } from '../../types/pdf-annotation';
import Header from '../../components/Header';
import { UploadCloudIcon, LoadingIcon } from '@/app/components/icons';
import PDFAnnotationViewer from '@/app/components/PDFAnnotationViewer';
import { usePDFAnnotation } from '../../hooks/usePDFAnnotation';
import { generateId } from '../../utils/pdf-annotation';
import { ContextMenu } from '../../components/pdf-annotation';

// Dynamically import PDFAnnotationViewer with SSR disabled
const PDFAnnotationViewerComponent = dynamic(() => import('../../components/PDFAnnotationViewer'), {
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

export default function PDFAnnotationPage() {
  const [pdf, setPdf] = useState<PDFFile>({
    id: '1',
    file: null,
    wordsData: null,
    isLoading: false,
    error: null
  });
  const [selectedBoxes, setSelectedBoxes] = useState<AnnotationBox[]>([]);
  const [availableModels, setAvailableModels] = useState<string[]>([]);
  const [isLoadingModels, setIsLoadingModels] = useState<boolean>(false);
  
  const [numPages, setNumPages] = useState<number>(0);
  const [pageNumber, setPageNumber] = useState<number>(1);
  const [isDrawingMode, setIsDrawingMode] = useState<boolean>(false);
  const [contextMenu, setContextMenu] = useState<{ x: number; y: number; show: boolean }>({ x: 0, y: 0, show: false });

  const fileInputRef = useRef<HTMLInputElement>(null);
  const chatService = new ChatService();

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
    groupBoxes,
    selectBoxesInArea
  } = usePDFAnnotation({ 
    wordsData: pdf.wordsData, 
    pageNumber, 
    onSelectBoxes: handleSelectBoxes 
  });

  const handleFileUpload = async (file: File) => {
    setPdf(prev => ({ ...prev, file, isLoading: true, error: null }));
    
    try {
      const wordsData = await fileService.extractPDFWords(file);
      setPdf(prev => ({ ...prev, wordsData, isLoading: false }));
      setPageNumber(1);
      setSelectedBoxes([]);
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

  const handleExportToJson = () => {
    if (!pdf.file || annotationBoxes.length === 0) return;

    const dataToExport = {
      document: pdf.file.name,
      exportDate: new Date().toISOString(),
      annotationBoxes: annotationBoxes,
    };

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
  };

  // Fetch available models on component mount
  useEffect(() => {
    const fetchModels = async () => {
      setIsLoadingModels(true);
      try {
        const models = await chatService.fetchModels();
        setAvailableModels(models);
      } catch (error) {
        console.error('Failed to fetch models:', error);
        // Fall back to default models if fetch fails
        setAvailableModels([]);
      } finally {
        setIsLoadingModels(false);
      }
    };

    fetchModels();
  }, []);

  return (
    <div className="flex flex-col h-screen bg-[#FAFBFC] text-gray-800">
             <Header 
         title="PDF Workflow Designer"
         showBackButton={true}
         backButtonText="Back to Services"
         backButtonPath="/services"
       />

             <div className="flex-1 flex">
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
                                     onChange={(e) => handleUpdateAnnotationBox(selectedBoxes[0].id, {
                                       settings: {
                                         ...selectedBoxes[0].settings,
                                         positionIsNotGuaranteed: e.target.checked
                                       }
                                     })}
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
                                               onChange={(e) => handleUpdateAnnotationBox(selectedBoxes[0].id, {
                                                 settings: {
                                                   ...selectedBoxes[0].settings,
                                                   visionModel: e.target.value,
                                                   ...(e.target.value === 'None' && { visionTaskDescription: '' })
                                                 }
                                               })}
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
                                               value={selectedBoxes[0].settings.chatModel || (availableModels.length > 0 ? availableModels[0] : '')}
                                               onChange={(e) => handleUpdateAnnotationBox(selectedBoxes[0].id, {
                                                 settings: {
                                                   ...selectedBoxes[0].settings,
                                                   chatModel: e.target.value
                                                 }
                                               })}
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
                                               className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:ring-indigo-500 focus:border-indigo-500 resize-none"
            rows={4}
          />
        </div>
                                         </div>
                                       </div>
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