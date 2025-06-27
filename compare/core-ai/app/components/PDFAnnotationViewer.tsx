"use client";

import React, { useState, useEffect, useRef, useCallback } from 'react';
import { Document, Page, pdfjs } from 'react-pdf';
import 'react-pdf/dist/Page/AnnotationLayer.css';
import 'react-pdf/dist/Page/TextLayer.css';

import type { PDFAnnotationViewerProps } from '../types/pdf-annotation';
import { AnnotationBox } from './pdf-annotation';
import { generateId } from '../utils/pdf-annotation';
import { usePDFAnnotationSettings } from '../contexts/PDFAnnotationContext';

// Configure PDF.js worker
pdfjs.GlobalWorkerOptions.workerSrc = new URL(
  'pdfjs-dist/build/pdf.worker.min.mjs',
  import.meta.url,
).toString();

export default function PDFAnnotationViewer({ 
  pdfFile, 
  wordsData, 
  isLoading, 
  selectedBoxes, 
  onSelectBoxes, 
  onUpdateAnnotationBox,
  // Lifted state and handlers
  numPages,
  setNumPages,
  pageNumber,
  setPageNumber,
  isDrawingMode,
  setIsDrawingMode,
  setContextMenu,
  currentPageBoxes,
  selectionState,
  setSelectionState,
  drawingState,
  setDrawingState,
  deleteAnnotationBox,
  addAnnotationBox,
  selectBoxesInArea
}: PDFAnnotationViewerProps) {
  const { settings } = usePDFAnnotationSettings();
  const [pdfScale, setPdfScale] = useState<number>(1);
  const [showBoundingBoxes, setShowBoundingBoxes] = useState<boolean>(true);
  const pdfContainerRef = useRef<HTMLDivElement>(null);
  
  // Reset page number when PDF changes
  useEffect(() => {
    setPageNumber(1);
  }, [pdfFile, setPageNumber]);

  function onDocumentLoadSuccess({ numPages }: { numPages: number }) {
    setNumPages(numPages);
    setPageNumber(1);
  }

  function onDocumentLoadError(error: Error) {
    console.error('Failed to load PDF:', error);
  }

  // Calculate scale factor based on PDF render size vs original dimensions
  const calculateScale = useCallback((renderedWidth: number) => {
    const currentPageDimensions = wordsData?.pages.find(page => page.page_number === pageNumber)?.dimensions;
    if (!currentPageDimensions) return 1;
    return renderedWidth / currentPageDimensions.width;
  }, [wordsData, pageNumber]);

  const onPageRenderSuccess = useCallback((page: any) => {
    const renderedWidth = page.width;
    const scale = calculateScale(renderedWidth);
    setPdfScale(scale);
  }, [calculateScale]);

  // Get relative coordinates
  const getRelativeCoordinates = useCallback((e: React.MouseEvent) => {
    const pdfPage = pdfContainerRef.current?.querySelector('.react-pdf__Page');
    if (!pdfPage) return { x: 0, y: 0 };
    const rect = pdfPage.getBoundingClientRect();
    return {
      x: (e.clientX - rect.left) / pdfScale,
      y: (e.clientY - rect.top) / pdfScale
    };
  }, [pdfScale]);

  const handleMouseDown = useCallback((e: React.MouseEvent) => {
    if (e.button === 2) return;
    setContextMenu({ x: 0, y: 0, show: false });
    const target = e.target as HTMLElement;
    if (target.closest('[data-annotation-box]')) return;
    const coords = getRelativeCoordinates(e);
    if (isDrawingMode) {
      setDrawingState({ isDrawing: true, start: coords, current: coords });
    } else {
      setSelectionState({ isSelecting: true, start: coords, current: coords });
      onSelectBoxes([]);
    }
  }, [isDrawingMode, getRelativeCoordinates, onSelectBoxes, setSelectionState, setDrawingState, setContextMenu]);

  const handleMouseMove = useCallback((e: React.MouseEvent) => {
    const coords = getRelativeCoordinates(e);
    if (drawingState.isDrawing && drawingState.start) {
      setDrawingState(prev => ({ ...prev, current: coords }));
    } else if (selectionState.isSelecting && selectionState.start) {
      setSelectionState(prev => ({ ...prev, current: coords }));
    }
  }, [drawingState.isDrawing, drawingState.start, selectionState.isSelecting, selectionState.start, getRelativeCoordinates, setDrawingState, setSelectionState]);

  const handleMouseUp = useCallback((e: React.MouseEvent) => {
    const coords = getRelativeCoordinates(e);
    if (drawingState.isDrawing && drawingState.start && drawingState.current) {
      const x = Math.min(drawingState.start.x, coords.x);
      const y = Math.min(drawingState.start.y, coords.y);
      const width = Math.abs(coords.x - drawingState.start.x);
      const height = Math.abs(coords.y - drawingState.start.y);
      if (width > 5 && height > 5) {
        addAnnotationBox({
          id: generateId('custom'),
          x, y, width, height, page: pageNumber, type: 'custom' as const,
          settings: { 
            mustMatchExactly: false, canMatchExactly: false,
            positionIsNotGuaranteed: false,
            useVisionModel: true,
            visionModel: settings.defaultVisionModel || 'None',
            guideWithTextIfAvailable: true,
            visionTaskDescription: 'Analyze this region and describe its content, extracting any visible text.',
            chatModel: settings.defaultChatModel || '',
            chatTaskDescription: 'Summarize the analysis of the selected region.'
          }
        });
      }
      setDrawingState({ isDrawing: false, start: null, current: null });
    } else if (selectionState.isSelecting && selectionState.start && selectionState.current) {
      const x = Math.min(selectionState.start.x, coords.x);
      const y = Math.min(selectionState.start.y, coords.y);
      const width = Math.abs(coords.x - selectionState.start.x);
      const height = Math.abs(coords.y - selectionState.start.y);
      if (width > 5 && height > 5) {
        selectBoxesInArea({ x, y, width, height });
      }
      setSelectionState({ isSelecting: false, start: null, current: null });
    }
  }, [drawingState, selectionState, getRelativeCoordinates, pageNumber, addAnnotationBox, selectBoxesInArea, setDrawingState, setSelectionState, settings]);
  
  const handleSelectBox = useCallback((box: any) => {
    onSelectBoxes([box]);
  }, [onSelectBoxes]);

  const handleContextMenu = useCallback((e: React.MouseEvent, boxId: string) => {
    e.preventDefault();
    if (!selectedBoxes.some(box => box.id === boxId)) {
      const clickedBox = currentPageBoxes.find(box => box.id === boxId);
      if (clickedBox) onSelectBoxes([clickedBox]);
    }
    setContextMenu({ x: e.clientX, y: e.clientY, show: true });
  }, [selectedBoxes, currentPageBoxes, onSelectBoxes, setContextMenu]);

  return (
    <div className="flex flex-col h-full bg-white">
      {/* PDF Viewer Header */}
      <div className="bg-white border-b border-gray-200 px-4 py-3 flex-shrink-0">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-4">
            <h3 className="text-sm font-medium text-gray-700">
              {pdfFile?.name || 'PDF Annotation'}
            </h3>
            {selectedBoxes.length > 0 && (
              <span className="text-xs text-indigo-600 font-medium">
                {selectedBoxes.length} selected
              </span>
            )}
          </div>
          
          <div className="flex items-center space-x-4">
            {/* Draw Mode Toggle */}
            <button
              onClick={() => setIsDrawingMode(!isDrawingMode)}
              className={`px-3 py-1 text-sm rounded-md transition-colors duration-200 ${
                isDrawingMode 
                  ? 'bg-red-500 text-white hover:bg-red-600' 
                  : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
              }`}
            >
              {isDrawingMode ? 'Selection Mode' : 'Draw Box'}
            </button>

            {/* Bounding Box Toggle */}
            <label className="flex items-center space-x-2">
              <input
                type="checkbox"
                checked={showBoundingBoxes}
                onChange={(e) => setShowBoundingBoxes(e.target.checked)}
                className="rounded border-gray-300 text-indigo-600 focus:ring-indigo-500"
              />
              <span className="text-sm text-gray-700">Show Word Boxes</span>
            </label>

            {/* Page Navigation */}
            {pdfFile && numPages > 0 && (
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
      </div>

      {/* PDF Display Area */}
      <div 
        ref={pdfContainerRef}
        className="flex-1 overflow-auto p-4 bg-gray-50 flex justify-center"
      >
        {isLoading ? (
          <div className="flex items-center justify-center h-full">
            <div className="text-center">
              <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-600 mx-auto mb-4"></div>
              <p className="text-gray-600">Processing PDF...</p>
            </div>
          </div>
        ) : pdfFile ? (
          <div 
            className={`relative cursor-crosshair`}
            onMouseDown={handleMouseDown}
            onMouseMove={handleMouseMove}
            onMouseUp={handleMouseUp}
            onContextMenu={(e) => {
              if (selectedBoxes.length > 0) e.preventDefault();
            }}
          >
            <Document
              file={pdfFile}
              onLoadSuccess={onDocumentLoadSuccess}
              onLoadError={onDocumentLoadError}
              className="border border-gray-300 shadow-lg"
              loading={<p>Loading PDF...</p>}
            >
              <Page 
                pageNumber={pageNumber}
                width={Math.min(800, (typeof window !== 'undefined' ? window.innerWidth : 800) * 0.6)}
                renderAnnotationLayer={false}
                renderTextLayer={false}
                onRenderSuccess={onPageRenderSuccess}
              />
            </Document>

            {/* Annotation Boxes Overlay */}
            <div 
              className="absolute top-0 left-0 pointer-events-none"
              style={{ width: '100%', height: '100%' }}
            >
              {currentPageBoxes
                .filter(box => showBoundingBoxes || box.type === 'custom' || box.type === 'image')
                .map((box) => {
                  const isSelected = selectedBoxes.some(selected => selected.id === box.id);
                  return (
                    <AnnotationBox
                      key={box.id}
                      box={box}
                      scale={pdfScale}
                      isSelected={isSelected}
                      isDrawingMode={isDrawingMode}
                      onSelect={() => handleSelectBox(box)}
                      onDelete={deleteAnnotationBox}
                      onUpdate={onUpdateAnnotationBox}
                      onContextMenu={handleContextMenu}
                    />
                  );
                })}
            </div>

            {/* Drawing Preview */}
            {drawingState.isDrawing && drawingState.start && drawingState.current && (
              <div
                className="absolute border-2 border-red-500 border-dashed pointer-events-none"
                style={{
                  left: Math.min(drawingState.start.x, drawingState.current.x) * pdfScale,
                  top: Math.min(drawingState.start.y, drawingState.current.y) * pdfScale,
                  width: Math.abs(drawingState.current.x - drawingState.start.x) * pdfScale,
                  height: Math.abs(drawingState.current.y - drawingState.start.y) * pdfScale,
                }}
              />
            )}

            {/* Selection Preview */}
            {selectionState.isSelecting && selectionState.start && selectionState.current && (
              <div
                className="absolute border-2 border-blue-500 border-dashed bg-blue-200 bg-opacity-20 pointer-events-none"
                style={{
                  left: Math.min(selectionState.start.x, selectionState.current.x) * pdfScale,
                  top: Math.min(selectionState.start.y, selectionState.current.y) * pdfScale,
                  width: Math.abs(selectionState.current.x - selectionState.start.x) * pdfScale,
                  height: Math.abs(selectionState.current.y - selectionState.start.y) * pdfScale,
                }}
              />
            )}
          </div>
        ) : (
          <div className="flex items-center justify-center h-full text-gray-500">
            <div className="text-center">
              <svg className="w-16 h-16 mx-auto mb-4 text-gray-300" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
              </svg>
              <p className="text-lg font-medium">No PDF loaded</p>
              <p className="text-sm">Upload a PDF to see bounding boxes</p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
} 