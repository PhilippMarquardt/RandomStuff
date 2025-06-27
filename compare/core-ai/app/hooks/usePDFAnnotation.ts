import { useState, useCallback, useEffect } from 'react';
import type { AnnotationBox, SelectionState, DrawingState } from '../types/pdf-annotation';
import type { PDFWordsData } from '../api/services/file-service';
import { calculateBoundingBox, checkBoxIntersection, generateId } from '../utils/pdf-annotation';

interface PDFAnnotationSettings {
  defaultChatModel: string;
  defaultVisionModel: string;
  availableModels: string[];
}

interface UsePDFAnnotationOptions {
  wordsData: PDFWordsData | null;
  pageNumber: number;
  onSelectBoxes: (boxes: AnnotationBox[]) => void;
  defaultSettings: PDFAnnotationSettings;
}

export const usePDFAnnotation = ({ wordsData, pageNumber, onSelectBoxes, defaultSettings }: UsePDFAnnotationOptions) => {
  const [annotationBoxes, setAnnotationBoxes] = useState<AnnotationBox[]>([]);
  const [selectionState, setSelectionState] = useState<SelectionState>({
    isSelecting: false,
    start: null,
    current: null
  });
  const [drawingState, setDrawingState] = useState<DrawingState>({
    isDrawing: false,
    start: null,
    current: null
  });

  // Convert word and image data to annotation boxes when wordsData changes
  useEffect(() => {
    if (wordsData) {
      const extractedBoxes: AnnotationBox[] = [];
      
      wordsData.pages.forEach((page) => {
        // Process word boxes
        page.words.forEach((word, index) => {
          const [x0, y0, x1, y1] = word.bbox;
          extractedBoxes.push({
            id: `word-${page.page_number}-${index}`,
            x: x0,
            y: y0,
            width: x1 - x0,
            height: y1 - y0,
            page: page.page_number,
            type: 'word',
            settings: { 
              mustMatchExactly: false,
              canMatchExactly: true,
              positionIsNotGuaranteed: false,
              useVisionModel: false,
              visionModel: 'None',
              guideWithTextIfAvailable: false,
              visionTaskDescription: '',
              chatModel: defaultSettings.defaultChatModel || '',
              chatTaskDescription: 'Return the exact text content from this word region.'
            }
          });
        });

        // Process image boxes
        if (page.images) {
          page.images.forEach((image, index) => {
            const [x0, y0, x1, y1] = image.bbox;
            extractedBoxes.push({
              id: `image-${page.page_number}-${index}`,
              x: x0,
              y: y0,
              width: x1 - x0,
              height: y1 - y0,
              page: page.page_number,
              type: 'image',
              settings: { 
                mustMatchExactly: false,
                canMatchExactly: false,
                positionIsNotGuaranteed: false,
                useVisionModel: true,
                visionModel: defaultSettings.defaultVisionModel || 'None',
                guideWithTextIfAvailable: true,
                visionTaskDescription: 'Analyze this image and describe its content.',
                chatModel: defaultSettings.defaultChatModel || '',
                chatTaskDescription: 'Summarize the analysis of the image.'
              },
              originalData: {
                area: image.area,
                imageType: image.type
              }
            });
          });
        }
      });
      
      // Keep existing custom boxes and replace extracted boxes
      setAnnotationBoxes(prev => [
        ...prev.filter(box => box.type === 'custom'),
        ...extractedBoxes
      ]);
    }
  }, [wordsData, defaultSettings.defaultChatModel, defaultSettings.defaultVisionModel]);

  const currentPageBoxes = annotationBoxes.filter(box => box.page === pageNumber);

  const updateAnnotationBox = useCallback((id: string, updates: Partial<AnnotationBox>) => {
    setAnnotationBoxes(prev => prev.map(box => 
      box.id === id ? { ...box, ...updates } : box
    ));
  }, []);

  const deleteAnnotationBox = useCallback((id: string) => {
    setAnnotationBoxes(prev => prev.filter(box => box.id !== id));
  }, []);

  const addAnnotationBox = useCallback((box: AnnotationBox) => {
    setAnnotationBoxes(prev => [...prev, box]);
  }, []);

  const loadAnnotationBoxes = useCallback((boxes: AnnotationBox[]) => {
    // This function will replace all existing boxes with the loaded set.
    // This is useful for loading a template.
    setAnnotationBoxes(boxes);
  }, []);

  const groupBoxes = useCallback((selectedBoxes: AnnotationBox[]) => {
    if (selectedBoxes.length < 2) return null;
    
    const bounds = calculateBoundingBox(selectedBoxes);
    
    const hasWordBoxes = selectedBoxes.some(box => box.type === 'word');
    const hasImageBoxes = selectedBoxes.some(box => box.type === 'image');
    
    // Create new grouped box
    const groupedBox: AnnotationBox = {
      id: generateId('grouped'),
      x: bounds.x,
      y: bounds.y,
      width: bounds.width,
      height: bounds.height,
      page: pageNumber,
      type: 'custom',
      settings: { 
        mustMatchExactly: false,
        canMatchExactly: hasWordBoxes,
        positionIsNotGuaranteed: false,
        useVisionModel: hasImageBoxes,
        visionModel: hasImageBoxes ? (defaultSettings.defaultVisionModel || 'None') : 'None',
        guideWithTextIfAvailable: hasImageBoxes,
        visionTaskDescription: hasImageBoxes ? 'Analyze this combined region and its contents.' : '',
        chatModel: defaultSettings.defaultChatModel || '',
        chatTaskDescription: 'Summarize the content of this grouped region.'
      }
    };
    
    // Remove selected boxes and add grouped box
    const selectedIds = selectedBoxes.map(box => box.id);
    setAnnotationBoxes(prev => [
      ...prev.filter(box => !selectedIds.includes(box.id)),
      groupedBox
    ]);
    
    return groupedBox;
  }, [pageNumber, defaultSettings.defaultChatModel, defaultSettings.defaultVisionModel]);

  const selectBoxesInArea = useCallback((selectionRect: { x: number; y: number; width: number; height: number }) => {
    const selectedInArea = currentPageBoxes.filter(box => 
      checkBoxIntersection(box, selectionRect)
    );
    onSelectBoxes(selectedInArea);
  }, [currentPageBoxes, onSelectBoxes]);

  return {
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
  };
}; 