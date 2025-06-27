import type { PDFWordsData } from '../api/services/file-service';

export interface AnnotationBox {
  id: string;
  x: number;
  y: number;
  width: number;
  height: number;
  page: number;
  type: 'word' | 'custom' | 'image';
  settings: {
    mustMatchExactly: boolean;
    canMatchExactly: boolean;
    positionIsNotGuaranteed?: boolean;
    useVisionModel?: boolean;
    visionModel?: string; // e.g., 'gemma-vision' or 'None'
    guideWithTextIfAvailable?: boolean;
    visionTaskDescription?: string;
    chatModel?: string; // e.g., 'gemma-chat'
    chatTaskDescription?: string;
    comparisonModel?: string;
    comparisonTaskDescription?: string;
    base64Image?: string;
    referenceGuidingText?: string;
  };
  originalData?: {
    // For word boxes
    text?: string;
    block_no?: number;
    line_no?: number;
    word_no?: number;
    // For image boxes
    area?: number;
    imageType?: string;
  };
}

export interface SelectionState {
  isSelecting: boolean;
  start: { x: number; y: number } | null;
  current: { x: number; y: number } | null;
}

export interface DrawingState {
  isDrawing: boolean;
  start: { x: number; y: number } | null;
  current: { x: number; y: number } | null;
}

export interface PDFAnnotationViewerProps {
  pdfFile: File | null;
  wordsData: PDFWordsData | null;
  isLoading?: boolean;
  selectedBoxes: AnnotationBox[];
  onSelectBoxes: (boxes: AnnotationBox[]) => void;
  onUpdateAnnotationBox: (id: string, updates: Partial<AnnotationBox>) => void;
  
  // Lifted state and handlers
  numPages: number;
  setNumPages: React.Dispatch<React.SetStateAction<number>>;
  pageNumber: number;
  setPageNumber: React.Dispatch<React.SetStateAction<number>>;
  isDrawingMode: boolean;
  setIsDrawingMode: React.Dispatch<React.SetStateAction<boolean>>;
  contextMenu: { x: number; y: number; show: boolean };
  setContextMenu: React.Dispatch<React.SetStateAction<{ x: number; y: number; show: boolean }>>;
  currentPageBoxes: AnnotationBox[];
  selectionState: SelectionState;
  setSelectionState: React.Dispatch<React.SetStateAction<SelectionState>>;
  drawingState: DrawingState;
  setDrawingState: React.Dispatch<React.SetStateAction<DrawingState>>;
  deleteAnnotationBox: (id: string) => void;
  addAnnotationBox: (box: AnnotationBox) => void;
  selectBoxesInArea: (selectionRect: { x: number; y: number; width: number; height: number }) => void;
}

export interface AnnotationBoxComponentProps {
  box: AnnotationBox;
  scale: number;
  isSelected: boolean;
  isDrawingMode: boolean;
  onSelect: () => void;
  onDelete: (id: string) => void;
  onUpdate: (id: string, updates: Partial<AnnotationBox>) => void;
  onContextMenu: (e: React.MouseEvent, boxId: string) => void;
}

export interface ContextMenuProps {
  show: boolean;
  x: number;
  y: number;
  selectedBoxes: AnnotationBox[];
  onGroup: () => void;
  onHide: () => void;
} 