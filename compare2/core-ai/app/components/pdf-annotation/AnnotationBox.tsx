import React, { useState, useRef, useCallback, useEffect } from 'react';
import type { AnnotationBoxComponentProps } from '../../types/pdf-annotation';

const AnnotationBox: React.FC<AnnotationBoxComponentProps> = ({ 
  box, 
  scale, 
  isSelected, 
  isDrawingMode, 
  onSelect, 
  onDelete, 
  onUpdate,
  onContextMenu
}) => {
  const [isDragging, setIsDragging] = useState(false);
  const [isResizing, setIsResizing] = useState(false);
  const [resizeHandle, setResizeHandle] = useState<string>('');
  const [dragOffset, setDragOffset] = useState({ x: 0, y: 0 });
  const [resizeOffset, setResizeOffset] = useState({ x: 0, y: 0, width: 0, height: 0 });
  const [justFinishedDrag, setJustFinishedDrag] = useState(false);
  const dragStartRef = useRef<{ x: number; y: number; boxX: number; boxY: number } | null>(null);
  const resizeStartRef = useRef<{ x: number; y: number; boxX: number; boxY: number; boxWidth: number; boxHeight: number } | null>(null);
  const animationFrameRef = useRef<number | null>(null);

  const handleMouseDown = useCallback((e: React.MouseEvent) => {
    if (isDrawingMode) return;
    
    // Don't handle drag/select on right-click
    if (e.button === 2) {
      return;
    }
    
    e.stopPropagation();
    onSelect();
    
    const target = e.target as HTMLElement;
    if (target.style.cursor && target.style.cursor.includes('resize')) {
      return;
    }
    
    e.preventDefault();
    
    dragStartRef.current = {
      x: e.clientX,
      y: e.clientY,
      boxX: box.x,
      boxY: box.y
    };
    setIsDragging(true);
    setDragOffset({ x: 0, y: 0 });
  }, [isDrawingMode, box.x, box.y, onSelect]);

  const handleResizeMouseDown = useCallback((e: React.MouseEvent, handle: string) => {
    if (isDrawingMode) return;
    
    e.stopPropagation();
    e.preventDefault();
    
    resizeStartRef.current = {
      x: e.clientX,
      y: e.clientY,
      boxX: box.x,
      boxY: box.y,
      boxWidth: box.width,
      boxHeight: box.height
    };
    setIsResizing(true);
    setResizeHandle(handle);
    setResizeOffset({ x: 0, y: 0, width: 0, height: 0 });
  }, [isDrawingMode, box.x, box.y, box.width, box.height]);

  const handleMouseMove = useCallback((e: MouseEvent) => {
    if ((!isDragging || !dragStartRef.current) && (!isResizing || !resizeStartRef.current)) return;
    
    if (animationFrameRef.current) {
      cancelAnimationFrame(animationFrameRef.current);
    }
    
    animationFrameRef.current = requestAnimationFrame(() => {
      if (isDragging && dragStartRef.current) {
        const deltaX = (e.clientX - dragStartRef.current.x) / scale;
        const deltaY = (e.clientY - dragStartRef.current.y) / scale;
        setDragOffset({ x: deltaX, y: deltaY });
      } else if (isResizing && resizeStartRef.current) {
        const deltaX = (e.clientX - resizeStartRef.current.x) / scale;
        const deltaY = (e.clientY - resizeStartRef.current.y) / scale;
        
        let newX = 0, newY = 0, newWidth = 0, newHeight = 0;
        
        switch (resizeHandle) {
          case 'nw': newX = deltaX; newY = deltaY; newWidth = -deltaX; newHeight = -deltaY; break;
          case 'ne': newY = deltaY; newWidth = deltaX; newHeight = -deltaY; break;
          case 'sw': newX = deltaX; newWidth = -deltaX; newHeight = deltaY; break;
          case 'se': newWidth = deltaX; newHeight = deltaY; break;
          case 'n': newY = deltaY; newHeight = -deltaY; break;
          case 's': newHeight = deltaY; break;
          case 'w': newX = deltaX; newWidth = -deltaX; break;
          case 'e': newWidth = deltaX; break;
        }
        
        setResizeOffset({ x: newX, y: newY, width: newWidth, height: newHeight });
      }
    });
  }, [isDragging, isResizing, scale, resizeHandle]);

  const handleMouseUp = useCallback((e: MouseEvent) => {
    if ((!isDragging || !dragStartRef.current) && (!isResizing || !resizeStartRef.current)) return;
    if (!onUpdate) return;
    
    if (animationFrameRef.current) {
      cancelAnimationFrame(animationFrameRef.current);
    }
    
    if (isDragging && dragStartRef.current) {
      const finalDeltaX = (e.clientX - dragStartRef.current.x) / scale;
      const finalDeltaY = (e.clientY - dragStartRef.current.y) / scale;
      
      const finalX = Math.max(0, dragStartRef.current.boxX + finalDeltaX);
      const finalY = Math.max(0, dragStartRef.current.boxY + finalDeltaY);
      
      onUpdate(box.id, { x: finalX, y: finalY });
      
      setIsDragging(false);
      setDragOffset({ x: 0, y: 0 });
      dragStartRef.current = null;
    } else if (isResizing && resizeStartRef.current) {
      const finalDeltaX = (e.clientX - resizeStartRef.current.x) / scale;
      const finalDeltaY = (e.clientY - resizeStartRef.current.y) / scale;
      
      let finalX = resizeStartRef.current.boxX;
      let finalY = resizeStartRef.current.boxY;
      let finalWidth = resizeStartRef.current.boxWidth;
      let finalHeight = resizeStartRef.current.boxHeight;
      
      switch (resizeHandle) {
        case 'nw': finalX += finalDeltaX; finalY += finalDeltaY; finalWidth -= finalDeltaX; finalHeight -= finalDeltaY; break;
        case 'ne': finalY += finalDeltaY; finalWidth += finalDeltaX; finalHeight -= finalDeltaY; break;
        case 'sw': finalX += finalDeltaX; finalWidth -= finalDeltaX; finalHeight += finalDeltaY; break;
        case 'se': finalWidth += finalDeltaX; finalHeight += finalDeltaY; break;
        case 'n': finalY += finalDeltaY; finalHeight -= finalDeltaY; break;
        case 's': finalHeight += finalDeltaY; break;
        case 'w': finalX += finalDeltaX; finalWidth -= finalDeltaX; break;
        case 'e': finalWidth += finalDeltaX; break;
      }
      
      finalWidth = Math.max(10, finalWidth);
      finalHeight = Math.max(10, finalHeight);
      finalX = Math.max(0, finalX);
      finalY = Math.max(0, finalY);
      
      onUpdate(box.id, { x: finalX, y: finalY, width: finalWidth, height: finalHeight });
      
      setIsResizing(false);
      setResizeHandle('');
      setResizeOffset({ x: 0, y: 0, width: 0, height: 0 });
      resizeStartRef.current = null;
    }
    
    setJustFinishedDrag(true);
    setTimeout(() => setJustFinishedDrag(false), 100);
  }, [isDragging, isResizing, onUpdate, box.id, scale, resizeHandle]);

  useEffect(() => {
    if (isDragging || isResizing) {
      document.addEventListener('mousemove', handleMouseMove, { passive: true });
      document.addEventListener('mouseup', handleMouseUp);
      document.body.style.userSelect = 'none';
      
      return () => {
        document.removeEventListener('mousemove', handleMouseMove);
        document.removeEventListener('mouseup', handleMouseUp);
        document.body.style.userSelect = '';
        
        if (animationFrameRef.current) {
          cancelAnimationFrame(animationFrameRef.current);
        }
      };
    }
  }, [isDragging, isResizing, handleMouseMove, handleMouseUp]);

  const isWordBox = box.type === 'word';
  const isImageBox = box.type === 'image';
  const isCustomBox = box.type === 'custom';
  
  // Different colors for different box types
  let borderColor = 'border-blue-500'; // default word box color
  let selectedBorderColor = 'border-blue-700';
  let hoverBorderColor = 'hover:border-blue-700';
  let selectedBackgroundColor = 'rgba(59, 130, 246, 0.3)'; // blue-500 with 30% opacity
  let handleColor = 'bg-blue-500';
  let deleteButtonColor = 'bg-blue-500 hover:bg-blue-600';
  
  if (isCustomBox) {
    borderColor = 'border-red-500';
    selectedBorderColor = 'border-red-700';
    hoverBorderColor = 'hover:border-red-700';
    selectedBackgroundColor = 'rgba(239, 68, 68, 0.3)'; // red-500 with 30% opacity
    handleColor = 'bg-red-500';
    deleteButtonColor = 'bg-red-500 hover:bg-red-600';
  } else if (isImageBox) {
    borderColor = 'border-green-500';
    selectedBorderColor = 'border-green-700';
    hoverBorderColor = 'hover:border-green-700';
    selectedBackgroundColor = 'rgba(34, 197, 94, 0.3)'; // green-500 with 30% opacity
    handleColor = 'bg-green-500';
    deleteButtonColor = 'bg-green-500 hover:bg-green-600';
  }
  
  // Create appropriate title based on box type
  let boxTitle = '';
  if (isWordBox) {
    boxTitle = `Word box - ${box.width.toFixed(0)}×${box.height.toFixed(0)} at (${box.x.toFixed(0)}, ${box.y.toFixed(0)}) ${isSelected ? '(selected)' : '(click to select)'}`;
  } else if (isImageBox) {
    const area = box.originalData?.area ? ` - Area: ${box.originalData.area.toFixed(0)}` : '';
    boxTitle = `Image box - ${box.width.toFixed(0)}×${box.height.toFixed(0)} at (${box.x.toFixed(0)}, ${box.y.toFixed(0)})${area} ${isSelected ? '(selected)' : '(click to select)'}`;
  } else {
    boxTitle = `Custom box - ${box.width.toFixed(0)}×${box.height.toFixed(0)} at (${box.x.toFixed(0)}, ${box.y.toFixed(0)}) ${isSelected ? '(selected)' : '(click to select)'}`;
  }
  
  return (
    <div
      data-annotation-box
      className={`absolute border-2 group ${
        isSelected 
          ? selectedBorderColor
          : `${borderColor} ${hoverBorderColor}`
      } ${
        isDragging || isResizing || justFinishedDrag ? 'transition-none' : 'transition-all duration-150'
      } ${
        isDrawingMode 
          ? 'opacity-60' 
          : isDragging 
            ? 'cursor-grabbing shadow-lg' 
            : isResizing
              ? 'shadow-lg'
              : 'cursor-grab'
      }`}
      style={{
        left: (box.x + (isResizing ? resizeOffset.x : 0)) * scale,
        top: (box.y + (isResizing ? resizeOffset.y : 0)) * scale,
        width: (box.width + (isResizing ? resizeOffset.width : 0)) * scale,
        height: (box.height + (isResizing ? resizeOffset.height : 0)) * scale,
        transform: isDragging ? `translate(${dragOffset.x * scale}px, ${dragOffset.y * scale}px)` : 'translate(0px, 0px)',
        backgroundColor: isSelected ? selectedBackgroundColor : 'transparent',
        pointerEvents: isDrawingMode ? 'none' : 'auto',
        zIndex: isDragging || isResizing ? 50 : 10,
        minWidth: '10px',
        minHeight: '10px',
      }}
      title={boxTitle}
      onMouseDown={handleMouseDown}
      onContextMenu={(e) => onContextMenu(e, box.id)}
    >
      {/* Resize Handles - only for custom boxes and when not in drawing mode */}
      {isCustomBox && !isDrawingMode && !isDragging && (
        <>
          {/* Corner handles */}
          <div className={`absolute w-2 h-2 ${handleColor} border border-white cursor-nw-resize opacity-0 group-hover:opacity-100 transition-opacity duration-150`} style={{ top: -4, left: -4 }} onMouseDown={(e) => handleResizeMouseDown(e, 'nw')} />
          <div className={`absolute w-2 h-2 ${handleColor} border border-white cursor-ne-resize opacity-0 group-hover:opacity-100 transition-opacity duration-150`} style={{ top: -4, right: -4 }} onMouseDown={(e) => handleResizeMouseDown(e, 'ne')} />
          <div className={`absolute w-2 h-2 ${handleColor} border border-white cursor-sw-resize opacity-0 group-hover:opacity-100 transition-opacity duration-150`} style={{ bottom: -4, left: -4 }} onMouseDown={(e) => handleResizeMouseDown(e, 'sw')} />
          <div className={`absolute w-2 h-2 ${handleColor} border border-white cursor-se-resize opacity-0 group-hover:opacity-100 transition-opacity duration-150`} style={{ bottom: -4, right: -4 }} onMouseDown={(e) => handleResizeMouseDown(e, 'se')} />
          
          {/* Edge handles */}
          <div className={`absolute w-4 h-1 ${handleColor} border border-white cursor-n-resize opacity-0 group-hover:opacity-100 transition-opacity duration-150`} style={{ top: -2, left: '50%', transform: 'translateX(-50%)' }} onMouseDown={(e) => handleResizeMouseDown(e, 'n')} />
          <div className={`absolute w-4 h-1 ${handleColor} border border-white cursor-s-resize opacity-0 group-hover:opacity-100 transition-opacity duration-150`} style={{ bottom: -2, left: '50%', transform: 'translateX(-50%)' }} onMouseDown={(e) => handleResizeMouseDown(e, 's')} />
          <div className={`absolute w-1 h-4 ${handleColor} border border-white cursor-w-resize opacity-0 group-hover:opacity-100 transition-opacity duration-150`} style={{ top: '50%', left: -2, transform: 'translateY(-50%)' }} onMouseDown={(e) => handleResizeMouseDown(e, 'w')} />
          <div className={`absolute w-1 h-4 ${handleColor} border border-white cursor-e-resize opacity-0 group-hover:opacity-100 transition-opacity duration-150`} style={{ top: '50%', right: -2, transform: 'translateY(-50%)' }} onMouseDown={(e) => handleResizeMouseDown(e, 'e')} />
        </>
      )}

      {/* Delete button - now for all box types */}
      {!isDrawingMode && onDelete && (
        <button
          onClick={(e) => {
            e.stopPropagation();
            onDelete(box.id);
          }}
          className={`absolute -top-2 -right-2 w-5 h-5 ${deleteButtonColor} text-white rounded-full text-xs transition-opacity duration-150 flex items-center justify-center z-10 opacity-0 group-hover:opacity-100`}
        >
          ×
        </button>
      )}
    </div>
  );
};

export default AnnotationBox; 