import type { AnnotationBox } from '../types/pdf-annotation';

export const generateId = (prefix: string): string => {
  return `${prefix}-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
};

export const calculateBoundingBox = (boxes: AnnotationBox[]): {
  x: number;
  y: number;
  width: number;
  height: number;
} => {
  if (boxes.length === 0) {
    return { x: 0, y: 0, width: 0, height: 0 };
  }

  const minX = Math.min(...boxes.map(box => box.x));
  const minY = Math.min(...boxes.map(box => box.y));
  const maxX = Math.max(...boxes.map(box => box.x + box.width));
  const maxY = Math.max(...boxes.map(box => box.y + box.height));

  return {
    x: minX,
    y: minY,
    width: maxX - minX,
    height: maxY - minY
  };
};

export const checkBoxIntersection = (
  box: AnnotationBox,
  selectionRect: { x: number; y: number; width: number; height: number }
): boolean => {
  return !(
    box.x > selectionRect.x + selectionRect.width ||
    box.x + box.width < selectionRect.x ||
    box.y > selectionRect.y + selectionRect.height ||
    box.y + box.height < selectionRect.y
  );
};

export const constrainToMinimumSize = (
  width: number,
  height: number,
  minSize: number = 10
): { width: number; height: number } => {
  return {
    width: Math.max(minSize, width),
    height: Math.max(minSize, height)
  };
};

export const constrainToPositive = (
  x: number,
  y: number
): { x: number; y: number } => {
  return {
    x: Math.max(0, x),
    y: Math.max(0, y)
  };
}; 