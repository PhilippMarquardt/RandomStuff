import React from 'react';
import type { ContextMenuProps } from '../../types/pdf-annotation';

const ContextMenu: React.FC<ContextMenuProps> = ({ 
  show, 
  x, 
  y, 
  selectedBoxes, 
  onGroup, 
  onHide 
}) => {
  if (!show) return null;

  const hasWordBoxes = selectedBoxes.some(box => box.type === 'word');
  const hasCustomBoxes = selectedBoxes.some(box => box.type === 'custom');
  const canGroup = selectedBoxes.length > 1 && !(hasWordBoxes && hasCustomBoxes);

  return (
    <div
      className="fixed bg-white border border-gray-200 rounded-md shadow-lg py-1 z-50"
      style={{ left: x, top: y }}
    >
      {selectedBoxes.length > 1 ? (
        <>
          {canGroup ? (
            <button
              onClick={onGroup}
              className="w-full text-left px-4 py-2 text-sm hover:bg-gray-100 transition-colors"
            >
              Group ({selectedBoxes.length} boxes)
            </button>
          ) : (
            <div className="px-4 py-2 text-sm text-gray-500">
              <div>Cannot group mixed box types</div>
              <div className="text-xs mt-1">Extracted text and custom boxes cannot be combined</div>
            </div>
          )}
        </>
      ) : (
        <div className="px-4 py-2 text-sm text-gray-500">
          Select multiple boxes to group
        </div>
      )}
    </div>
  );
};

export default ContextMenu; 