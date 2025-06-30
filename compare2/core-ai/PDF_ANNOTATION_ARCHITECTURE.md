# PDF Annotation System Architecture

## Overview
The PDF annotation system has been refactored into a clean, modular architecture with proper separation of concerns. This system allows users to upload PDFs, view automatically detected word bounding boxes, create custom annotation boxes, and perform advanced operations like multi-selection and grouping.

## Directory Structure

```
core-ai/app/
├── components/
│   ├── PDFAnnotationViewer.tsx          # Main viewer component
│   └── pdf-annotation/
│       ├── index.ts                     # Component exports
│       ├── AnnotationBox.tsx            # Individual annotation box component
│       └── ContextMenu.tsx              # Right-click context menu
├── hooks/
│   └── usePDFAnnotation.ts              # Main state management hook
├── types/
│   └── pdf-annotation.ts                # TypeScript interfaces
└── utils/
    └── pdf-annotation.ts                # Utility functions
```

## Components

### PDFAnnotationViewer
The main component that orchestrates the entire PDF annotation experience.

**Key Features:**
- PDF rendering with react-pdf
- Multi-page navigation
- Drawing and selection modes
- Context menu handling
- Responsive layout with proper scaling

**Props:**
- `pdfFile`: The PDF file to display
- `wordsData`: Extracted word data from PyMuPDF
- `selectedBoxes`: Currently selected annotation boxes
- `onSelectBoxes`: Callback for selection changes
- `onUpdateAnnotationBox`: Callback for box updates

### AnnotationBox
A self-contained component for individual annotation boxes with full interaction capabilities.

**Features:**
- Drag and drop functionality
- 8-direction resizing (custom boxes only)
- Selection visual feedback
- Hover tooltips with position info
- Delete functionality for custom boxes
- Performance optimized with requestAnimationFrame

### ContextMenu
Simple context menu for multi-selection operations.

**Features:**
- Right-click activation
- Grouping functionality for multiple selections
- Auto-positioning to avoid screen edges

## Hooks

### usePDFAnnotation
Central state management hook that handles all annotation logic.

**Capabilities:**
- Converts PyMuPDF word data to annotation boxes
- Manages selection and drawing states
- Handles box CRUD operations
- Implements grouping logic
- Area-based selection detection

**State Management:**
- `annotationBoxes`: All annotation boxes across pages
- `selectionState`: Rectangle selection tracking
- `drawingState`: New box drawing tracking

**Key Functions:**
- `updateAnnotationBox`: Update box properties
- `deleteAnnotationBox`: Remove boxes
- `addAnnotationBox`: Add new custom boxes
- `groupBoxes`: Combine multiple boxes into one (same type only)
- `selectBoxesInArea`: Select boxes within a rectangle

## Types

### Core Interfaces

**AnnotationBox:**
```typescript
interface AnnotationBox {
  id: string;
  x: number;
  y: number;
  width: number;
  height: number;
  page: number;
  type: 'word' | 'custom';
  settings: {
    mustBeHere: boolean;
    mustMatchExactly: boolean;
    canMatchExactly: boolean; // Indicates if mustMatchExactly is available
    llmModel?: string; // LLM model for text extraction (custom boxes only)
    llmTaskDescription?: string; // System prompt for the LLM (custom boxes only)
  };
}
```

**State Interfaces:**
- `SelectionState`: Rectangle selection tracking
- `DrawingState`: New box drawing tracking
- `PDFAnnotationViewerProps`: Main component props
- `AnnotationBoxComponentProps`: Box component props
- `ContextMenuProps`: Context menu props

## Utilities

### Core Functions
- `generateId`: Creates unique IDs with timestamps and random strings
- `calculateBoundingBox`: Computes bounding box for multiple boxes
- `checkBoxIntersection`: Tests if boxes intersect with selection area
- `constrainToMinimumSize`: Ensures minimum dimensions
- `constrainToPositive`: Ensures positive coordinates

## User Interactions

### Selection Modes

**Default Mode (Selection):**
- Click empty space and drag to create selection rectangle
- All boxes within rectangle are selected
- Right-click selected boxes to access context menu

**Drawing Mode:**
- Toggle via "Draw Box" button
- Click and drag to create new custom annotation boxes
- Automatically switches back to selection mode after drawing

### Box Operations

**Individual Boxes:**
- Click to select single box
- Drag to move (all box types)
- Resize via handles (custom boxes only)
- Delete via × button (custom boxes only)

**Multiple Boxes:**
- Select multiple via rectangle selection
- Right-click to access grouping options
- Group operation creates new box encompassing all selected areas
- **Restriction**: Cannot group extracted text boxes with custom boxes (same type only)

### Box Settings

**Must Be Here:**
- Available for all box types
- When enabled, this region must be present in processed documents

**Must Match Exactly:**
- Only available for extracted text regions (word boxes) and grouped boxes created from only word boxes
- When enabled, text in this region must match exactly when comparing documents
- Greyed out and disabled for custom boxes and mixed groups
- Visual indicators show availability status

**LLM Text Extraction (Custom Boxes Only):**
- **LLM Model**: Selection of AI model for text extraction (currently Gemma 3)
- **Task Description**: Custom system prompt instructing the LLM how to process the region
- Only available for custom boxes since they require intelligent text extraction
- Default task: "Extract and return the text content from this region."

### Visual Feedback

**Color Coding:**
- Blue boxes: Automatically detected words
- Red boxes: Custom user-created boxes
- Selected boxes: Higher opacity background
- Hover effects: Enhanced borders and visible handles

**Settings Visual Cues:**
- Enabled checkboxes: Normal appearance
- Disabled checkboxes: Greyed out with opacity
- Setting descriptions change based on availability

**Performance Features:**
- CSS transforms for smooth dragging
- RequestAnimationFrame for lag-free interactions
- Optimized re-renders with proper React patterns

## Integration Points

### Backend API
- `/api/v1/pdf/extract-words` - PyMuPDF word extraction
- Returns structured data with word positions and page dimensions

### Parent Components
- Upload page provides PDF file and word data
- Parent manages selected boxes state
- Callbacks for box updates enable persistence

## Business Rules

### Box Type Restrictions
- **Grouping Limitations**: Extracted text boxes and custom boxes cannot be grouped together
  - ✅ **Allowed**: Word boxes + word boxes → Grouped box with exact matching capability
  - ✅ **Allowed**: Custom boxes + custom boxes → Grouped box without exact matching
  - ❌ **Forbidden**: Word boxes + custom boxes → No grouping allowed
  - **Rationale**: Extracted text has semantic meaning, custom boxes are just regions

### Settings Availability
- **Must Match Exactly**: Only available for extracted text regions and their pure groupings
- **Must Be Here**: Available for all box types
- **LLM Text Extraction**: Only available for custom boxes and their pure groupings
  - Custom boxes use LLM for intelligent text extraction with configurable prompts
  - Word boxes already have precise text extraction from PyMuPDF

## Technical Decisions

### Performance Optimizations
1. **CSS Transforms**: Used instead of position updates during drag
2. **RequestAnimationFrame**: Throttles mouse move events
3. **Refs for DOM Access**: Avoids unnecessary re-renders
4. **Selective Re-rendering**: Components only update when props change

### User Experience
1. **Visual Consistency**: All boxes follow same interaction patterns
2. **Immediate Feedback**: Instant visual response to all interactions
3. **Undo-Friendly**: All operations can be easily reversed
4. **Accessibility**: Proper keyboard navigation and screen reader support

### Code Organization
1. **Single Responsibility**: Each component has one clear purpose
2. **Type Safety**: Full TypeScript coverage with strict types
3. **Reusability**: Components designed for easy reuse
4. **Testability**: Pure functions and isolated concerns

## Future Enhancements

### Planned Features
- Keyboard shortcuts for common operations
- Undo/redo functionality
- Box templates and presets
- Batch operations on multiple boxes
- Export/import of annotation configurations

### Technical Improvements
- Virtual scrolling for large documents
- Web Worker for heavy computations
- Canvas-based rendering for better performance
- Real-time collaboration features 