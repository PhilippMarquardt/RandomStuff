// Placeholder type for a tool
export type WorkflowTool = {
  id: string; // Original ID from the sidebar
  name: string;
  category: 'prompt' | 'data' | 'code' | 'logic' | 'output'; // Add category for color coding
  icon: string; // Simple icon representation
};

// Type for a tool instance on the canvas
export type CanvasTool = WorkflowTool & {
  instanceId: string; // Unique ID for this instance on the canvas
  x: number;
  y: number;
  properties?: Record<string, unknown>; // For storing editable properties
};

// State for active dragging of a canvas tool
export type DraggingToolDetails = {
  instanceId: string;
  offsetX: number; // Offset of mouse click from tool's left edge
  offsetY: number; // Offset of mouse click from tool's top edge
};

export type DrawingConnectionDetails = {
  startToolInstanceId: string;
  startX: number; // Relative to canvas
  startY: number; // Relative to canvas
  currentX: number; // Relative to canvas
  currentY: number; // Relative to canvas
  fromPortType: 'input' | 'output';
};

export type Connection = {
  id: string;
  fromToolInstanceId: string;
  toToolInstanceId: string;
  // Later: fromPortId, toPortId
};

export type EditingNodeDetails = {
  instanceId: string;
  x: number; // Position for the popover
  y: number;
}; 