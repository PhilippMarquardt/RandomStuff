"use client"

import React, { useState, useRef, DragEvent, MouseEvent as ReactMouseEvent, useEffect } from 'react';

// Placeholder type for a tool
type WorkflowTool = {
  id: string; // Original ID from the sidebar
  name: string;
  category: 'prompt' | 'data' | 'code' | 'logic' | 'output'; // Add category for color coding
  icon: string; // Simple icon representation
};

// Type for a tool instance on the canvas
type CanvasTool = WorkflowTool & {
  instanceId: string; // Unique ID for this instance on the canvas
  x: number;
  y: number;
  properties?: Record<string, any>; // For storing editable properties
};

// Placeholder list of available tools
const initialAvailableTools: WorkflowTool[] = [
  { id: 'tool-1', name: 'PDFParser', category: 'data', icon: '📄' },
  { id: 'tool-2', name: 'LLMPrompt', category: 'prompt', icon: '💬' },
  { id: 'tool-3', name: 'JSONFormatter', category: 'code', icon: '{ }' },
  { id: 'tool-4', name: 'Summary', category: 'output', icon: '📝' },
  { id: 'tool-5', name: 'Conditional Logic', category: 'logic', icon: '🔀' },
  { id: 'tool-6', name: 'Concatenation', category: 'logic', icon: '🔗' },
];

// Get category color based on type
const getCategoryColor = (category: string): { border: string; bg: string; light: string } => {
  switch (category) {
    case 'prompt':
      return { border: 'border-indigo-500', bg: 'bg-indigo-600', light: 'bg-indigo-50' };
    case 'data':
      return { border: 'border-teal-500', bg: 'bg-teal-600', light: 'bg-teal-50' };
    case 'code':
      return { border: 'border-amber-500', bg: 'bg-amber-600', light: 'bg-amber-50' };
    case 'logic':
      return { border: 'border-purple-500', bg: 'bg-purple-600', light: 'bg-purple-50' };
    case 'output':
      return { border: 'border-green-500', bg: 'bg-green-600', light: 'bg-green-50' };
    default:
      return { border: 'border-indigo-500', bg: 'bg-indigo-600', light: 'bg-indigo-50' };
  }
};

// State for active dragging of a canvas tool
type DraggingToolDetails = {
  instanceId: string;
  offsetX: number; // Offset of mouse click from tool's left edge
  offsetY: number; // Offset of mouse click from tool's top edge
};

type DrawingConnectionDetails = {
  startToolInstanceId: string;
  startX: number; // Relative to canvas
  startY: number; // Relative to canvas
  currentX: number; // Relative to canvas
  currentY: number; // Relative to canvas
  fromPortType: 'input' | 'output';
};

type Connection = {
  id: string;
  fromToolInstanceId: string;
  toToolInstanceId: string;
  // Later: fromPortId, toPortId
};

type EditingNodeDetails = {
  instanceId: string;
  x: number; // Position for the popover
  y: number;
};

const TOOL_WIDTH = 200; // Slightly wider for better presentation
const TOOL_HEIGHT = 80; // Taller to accommodate header and content
const HEADER_HEIGHT = 24; // Height of the node header
const PORT_SIZE = 8; // Diameter of the port circle
const PORT_OFFSET_Y = PORT_SIZE / 2; // How much port sticks out from tool edge
const GRID_SIZE = 20; // Grid size for snapping

export default function DesignerPage() {
  const [availableTools, setAvailableTools] = useState<WorkflowTool[]>(initialAvailableTools);
  const [droppedToolsOnCanvas, setDroppedToolsOnCanvas] = useState<CanvasTool[]>([]);
  const designerCanvasRef = useRef<HTMLDivElement>(null); // Ref for the canvas area
  const [draggingTool, setDraggingTool] = useState<DraggingToolDetails | null>(null);
  const [drawingConnection, setDrawingConnection] = useState<DrawingConnectionDetails | null>(null);
  const [connections, setConnections] = useState<Connection[]>([]);
  const [selectedToolId, setSelectedToolId] = useState<string | null>(null);
  const [snapToGrid, setSnapToGrid] = useState(true);
  const [zoomLevel, setZoomLevel] = useState(100); // Percentage
  const [showMiniMap, setShowMiniMap] = useState(false);
  const [editingNode, setEditingNode] = useState<EditingNodeDetails | null>(null);

  // Function to snap a coordinate to the grid
  const snapToGridFunc = (coord: number) => {
    return snapToGrid ? Math.round(coord / GRID_SIZE) * GRID_SIZE : coord;
  };

  const getPortPosition = (tool: CanvasTool, portType: 'input' | 'output') => {
    if (portType === 'input') {
      return { x: tool.x + TOOL_WIDTH / 2, y: tool.y };
    }
    // Output port
    return { x: tool.x + TOOL_WIDTH / 2, y: tool.y + TOOL_HEIGHT };
  };

  // Generate bezier curve path for connections
  const generatePath = (startX: number, startY: number, endX: number, endY: number) => {
    const controlPointOffset = Math.abs(endY - startY) / 2;
    return `M ${startX} ${startY} C ${startX} ${startY + controlPointOffset}, ${endX} ${endY - controlPointOffset}, ${endX} ${endY}`;
  };

  const handleSidebarToolDragStart = (event: DragEvent<HTMLDivElement>, tool: WorkflowTool) => {
    event.dataTransfer.setData('application/json', JSON.stringify(tool));
    event.dataTransfer.effectAllowed = 'move';
  };

  const handleCanvasDragOver = (event: DragEvent<HTMLDivElement>) => {
    event.preventDefault();
    event.dataTransfer.dropEffect = 'move';
  };

  const handleCanvasDrop = (event: DragEvent<HTMLDivElement>) => {
    event.preventDefault();
    const toolDataString = event.dataTransfer.getData('application/json');
    if (!toolDataString) return;
    const droppedSidebarTool: WorkflowTool = JSON.parse(toolDataString);
    
    if (designerCanvasRef.current) {
      const canvasRect = designerCanvasRef.current.getBoundingClientRect();
      let x = event.clientX - canvasRect.left - (TOOL_WIDTH / 2);
      let y = event.clientY - canvasRect.top - (TOOL_HEIGHT / 2);

      // Apply snapping
      x = snapToGridFunc(x);
      y = snapToGridFunc(y);

      x = Math.max(0, Math.min(x, canvasRect.width - TOOL_WIDTH));
      y = Math.max(0, Math.min(y, canvasRect.height - TOOL_HEIGHT));

      const newCanvasTool: CanvasTool = {
        ...droppedSidebarTool,
        instanceId: `canvas-${droppedSidebarTool.id}-${Date.now()}`,
        x,
        y,
        properties: {},
      };
      setDroppedToolsOnCanvas(prevTools => [...prevTools, newCanvasTool]);
      setSelectedToolId(newCanvasTool.instanceId);
    }
  };

  const handleCanvasToolMouseDown = (event: ReactMouseEvent<HTMLDivElement>, toolInstanceId: string) => {
    // Check if the click is on a port, if so, don't drag the tool itself
    const target = event.target as HTMLElement;
    if (target.dataset.portType) {
        return; // Handled by handlePortMouseDown
    }

    setSelectedToolId(toolInstanceId);
    const toolElement = event.currentTarget as HTMLDivElement;
    const offsetX = event.clientX - toolElement.getBoundingClientRect().left;
    const offsetY = event.clientY - toolElement.getBoundingClientRect().top;
    setDraggingTool({ instanceId: toolInstanceId, offsetX, offsetY });
    event.preventDefault(); 
  };

  const handleNodeDoubleClick = (event: ReactMouseEvent<HTMLDivElement>, toolInstanceId: string) => {
    event.stopPropagation();
    const toolElement = event.currentTarget as HTMLDivElement;
    const rect = toolElement.getBoundingClientRect();
    
    setEditingNode({
      instanceId: toolInstanceId,
      x: rect.left + rect.width / 2,
      y: rect.top + rect.height / 2
    });
  };

  const handlePortMouseDown = (event: ReactMouseEvent<HTMLDivElement>, toolInstanceId: string, portType: 'input' | 'output') => {
    event.stopPropagation(); // Important: Prevent tool drag
    event.preventDefault();

    const tool = droppedToolsOnCanvas.find(t => t.instanceId === toolInstanceId);
    if (!tool || !designerCanvasRef.current) return;

    const canvasRect = designerCanvasRef.current.getBoundingClientRect();
    const portPos = getPortPosition(tool, portType);
    
    setDrawingConnection({
      startToolInstanceId: toolInstanceId,
      startX: portPos.x,
      startY: portPos.y,
      currentX: event.clientX - canvasRect.left,
      currentY: event.clientY - canvasRect.top,
      fromPortType: portType
    });
  };

  const handleCanvasMouseMove = (event: ReactMouseEvent<HTMLDivElement>) => {
    if (draggingTool && designerCanvasRef.current) {
      const canvasRect = designerCanvasRef.current.getBoundingClientRect();
      let newX = event.clientX - canvasRect.left - draggingTool.offsetX;
      let newY = event.clientY - canvasRect.top - draggingTool.offsetY;
      
      // Apply snapping
      newX = snapToGridFunc(newX);
      newY = snapToGridFunc(newY);
      
      newX = Math.max(0, Math.min(newX, canvasRect.width - TOOL_WIDTH));
      newY = Math.max(0, Math.min(newY, canvasRect.height - TOOL_HEIGHT));
      setDroppedToolsOnCanvas(prevTools =>
        prevTools.map(t =>
          t.instanceId === draggingTool.instanceId ? { ...t, x: newX, y: newY } : t
        )
      );
    } else if (drawingConnection && designerCanvasRef.current) {
      const canvasRect = designerCanvasRef.current.getBoundingClientRect();
      setDrawingConnection(prev => (
        prev ? {
          ...prev,
          currentX: event.clientX - canvasRect.left,
          currentY: event.clientY - canvasRect.top,
        } : null
      ));
    }
  };

  const handleCanvasMouseUpOrLeave = (event: ReactMouseEvent<HTMLDivElement>) => {
    if (draggingTool) setDraggingTool(null);
    if (drawingConnection) {
      const targetElement = document.elementFromPoint(event.clientX, event.clientY) as HTMLElement | null;
      const portElement = targetElement?.closest('[data-port-type]');
      
      if (portElement) {
        const targetPortType = portElement.getAttribute('data-port-type') as 'input' | 'output';
        // Only allow connecting output->input or input->output
        if (targetPortType !== drawingConnection.fromPortType) {
          const targetToolElement = portElement.closest('[data-tool-instance-id]');
          const targetToolInstanceId = targetToolElement?.getAttribute('data-tool-instance-id');

          if (targetToolInstanceId && targetToolInstanceId !== drawingConnection.startToolInstanceId) {
            // Prevent connecting to self
            // Determine the fromId and toId based on port types
            let fromId = drawingConnection.startToolInstanceId;
            let toId = targetToolInstanceId;
            
            // If we started from an input, swap the direction
            if (drawingConnection.fromPortType === 'input') {
              [fromId, toId] = [toId, fromId];
            }
            
            // Prevent duplicate connections
            const alreadyExists = connections.some(
              conn => conn.fromToolInstanceId === fromId && conn.toToolInstanceId === toId
            );
            
            // More complex: prevent an input from having multiple sources
            const inputAlreadyHasConnection = connections.some(conn => conn.toToolInstanceId === toId);

            if (!alreadyExists && !inputAlreadyHasConnection) {
              const newConnection: Connection = {
                id: `conn-${fromId}-${toId}-${Date.now()}`,
                fromToolInstanceId: fromId,
                toToolInstanceId: toId,
              };
              setConnections(prev => [...prev, newConnection]);
            }
          }
        }
      }
      setDrawingConnection(null);
    }
  };

  const handleCanvasKeyDown = (event: KeyboardEvent) => {
    if (selectedToolId) {
      // Delete selected node
      if (event.key === 'Delete' || event.key === 'Backspace') {
        setConnections(prev => prev.filter(
          conn => conn.fromToolInstanceId !== selectedToolId && conn.toToolInstanceId !== selectedToolId
        ));
        setDroppedToolsOnCanvas(prev => prev.filter(tool => tool.instanceId !== selectedToolId));
        setSelectedToolId(null);
      }
      
      // Duplicate selected node
      if ((event.ctrlKey || event.metaKey) && event.key === 'd') {
        event.preventDefault();
        const selectedTool = droppedToolsOnCanvas.find(t => t.instanceId === selectedToolId);
        if (selectedTool) {
          const newTool: CanvasTool = {
            ...selectedTool,
            instanceId: `canvas-${selectedTool.id}-${Date.now()}`,
            x: selectedTool.x + GRID_SIZE * 2,
            y: selectedTool.y + GRID_SIZE * 2,
            properties: {...selectedTool.properties}
          };
          setDroppedToolsOnCanvas(prev => [...prev, newTool]);
          setSelectedToolId(newTool.instanceId);
        }
      }
    }
  };

  // Set up keyboard listener
  useEffect(() => {
    document.addEventListener('keydown', handleCanvasKeyDown);
    return () => {
      document.removeEventListener('keydown', handleCanvasKeyDown);
    };
  }, [selectedToolId]);

  // Zoom controls
  const handleZoomIn = () => {
    setZoomLevel(prev => Math.min(prev + 10, 200));
  };

  const handleZoomOut = () => {
    setZoomLevel(prev => Math.max(prev - 10, 50));
  };

  return (
    <div className="flex h-screen bg-[#FAFBFC] text-gray-800 font-['Inter',_sans-serif] antialiased">
      {/* Left Sidebar for Tools */}
      <aside className="w-72 bg-white p-4 border-r border-gray-200 shadow-sm flex flex-col space-y-3">
        <h2 className="text-lg font-semibold text-gray-800 mb-2 border-b border-gray-200 pb-2">Tools</h2>
        <div className="flex-1 overflow-y-auto space-y-2 pr-1">
          {availableTools.map(tool => {
            const colors = getCategoryColor(tool.category);
            return (
              <div 
                key={tool.id}
                draggable={true}
                onDragStart={(e) => handleSidebarToolDragStart(e, tool)}
                className={`p-3 bg-white rounded-lg cursor-grab hover:${colors.light} hover:text-${colors.bg.replace('bg-', '')} active:cursor-grabbing transition-colors duration-150 shadow-sm border ${colors.border}`}
                title={`Drag ${tool.name} to the canvas`}
              >
                <p className="text-sm font-medium text-gray-700">{tool.name}</p>
              </div>
            );
          })}
        </div>
      </aside>

      {/* Main Designer Panel */}
      <main className="flex-1 flex flex-col overflow-hidden">
        {/* Header for the designer */}
        <nav className="w-full bg-white backdrop-blur-sm border-b border-gray-200 shadow-sm">
          <div className="container mx-auto px-6 py-4 flex justify-between items-center">
            <div className="flex items-center">
              <h1 className="text-xl font-bold text-gray-800 tracking-tight uppercase">AI Workflow Designer</h1>
            </div>
            <div className="flex items-center space-x-3">
              <button className="px-4 py-2 text-sm bg-indigo-600 hover:bg-indigo-500 rounded-md text-white transition-colors duration-200 font-medium">
                Save Workflow
              </button>
            </div>
          </div>
        </nav>

        {/* Designer Canvas Area */}
        <div 
          ref={designerCanvasRef} 
          onDragOver={handleCanvasDragOver}
          onDrop={handleCanvasDrop}
          onMouseMove={handleCanvasMouseMove}
          onMouseUp={handleCanvasMouseUpOrLeave}
          onMouseLeave={handleCanvasMouseUpOrLeave}
          className="flex-1 bg-gray-50 overflow-hidden relative cursor-default select-none"
          style={{
            backgroundImage: 'radial-gradient(circle, #d1d5db 1px, transparent 1px)',
            backgroundSize: '20px 20px',
            transform: `scale(${zoomLevel / 100})`,
            transformOrigin: 'center center'
          }}
        >
          {/* SVG Layer for Connections */}
          <svg className="absolute top-0 left-0 w-full h-full pointer-events-none z-0">
            <defs>
              <marker id="arrowhead" markerWidth="10" markerHeight="7" refX="9" refY="3.5" orient="auto" fill="#6366f1">
                <polygon points="0 0, 10 3.5, 0 7" />
              </marker>
            </defs>
            {/* Draw established connections */}
            {connections.map(conn => {
              const fromTool = droppedToolsOnCanvas.find(t => t.instanceId === conn.fromToolInstanceId);
              const toTool = droppedToolsOnCanvas.find(t => t.instanceId === conn.toToolInstanceId);
              if (!fromTool || !toTool) return null;
              const startPos = getPortPosition(fromTool, 'output');
              const endPos = getPortPosition(toTool, 'input');
              return (
                <path
                  key={conn.id}
                  d={generatePath(startPos.x, startPos.y, endPos.x, endPos.y - PORT_OFFSET_Y)}
                  stroke="#6366f1"
                  strokeWidth="2"
                  fill="none"
                  markerEnd="url(#arrowhead)"
                />
              );
            })}
            {/* Draw temporary connection line */}
            {drawingConnection && (
              <path
                d={generatePath(
                  drawingConnection.startX,
                  drawingConnection.startY,
                  drawingConnection.currentX,
                  drawingConnection.currentY
                )}
                stroke="#818cf8"
                strokeWidth="2"
                strokeDasharray="5,5"
                fill="none"
                markerEnd="url(#arrowhead)"
              />
            )}
          </svg>

          {/* Empty State */}
          {droppedToolsOnCanvas.length === 0 && !draggingTool && !drawingConnection && (
            <div className="w-full h-full border-2 border-dashed border-gray-300 rounded-lg flex items-center justify-center pointer-events-none">
              <p className="text-gray-400 text-lg">Drag tools here to build your workflow</p>
            </div>
          )}

          {/* Render nodes on canvas */}
          {droppedToolsOnCanvas.map(tool => {
            const colors = getCategoryColor(tool.category);
            const isSelected = selectedToolId === tool.instanceId;
            
            return (
              <div
                key={tool.instanceId}
                data-tool-instance-id={tool.instanceId}
                onMouseDown={(e) => handleCanvasToolMouseDown(e, tool.instanceId)}
                onDoubleClick={(e) => handleNodeDoubleClick(e, tool.instanceId)}
                className={`absolute rounded-lg shadow-sm select-none z-10 flex flex-col ${
                  isSelected ? 'outline outline-2 outline-indigo-300' : ''
                }`}
                style={{
                  left: `${tool.x}px`, top: `${tool.y}px`,
                  width: `${TOOL_WIDTH}px`, height: `${TOOL_HEIGHT}px`,
                  cursor: draggingTool && draggingTool.instanceId === tool.instanceId ? 'grabbing' : 'grab',
                  boxShadow: '0 2px 6px rgba(0,0,0,0.05)'
                }}
              >
                {/* Header */}
                <div className={`h-6 ${colors.bg} text-white px-2 flex items-center rounded-t-lg`}>
                  <p className="text-xs font-semibold truncate">{tool.name}</p>
                </div>
                
                {/* Body */}
                <div className={`flex-1 bg-white p-3 rounded-b-lg border-x border-b ${colors.border}`}>
                  <p className="text-xs text-gray-500 truncate">
                    {tool.properties?.description || `Double-click to edit ${tool.name} properties`}
                  </p>
                </div>
                
                {/* Ports */}
                <div 
                  data-port-type="input"
                  className={`absolute -top-1 left-1/2 -translate-x-1/2 w-2 h-2 rounded-full cursor-crosshair border-2 border-green-600 bg-white hover:border-green-400 hover:scale-150 transition-all`}
                  style={{width: `${PORT_SIZE}px`, height: `${PORT_SIZE}px`, transform: `translate(-50%, -${PORT_OFFSET_Y}px)`}}
                  title={`Input for ${tool.name}`}
                  onMouseDown={(e) => handlePortMouseDown(e, tool.instanceId, 'input')}
                ></div>
                <div 
                  data-port-type="output"
                  onMouseDown={(e) => handlePortMouseDown(e, tool.instanceId, 'output')}
                  className={`absolute -bottom-1 left-1/2 -translate-x-1/2 w-2 h-2 rounded-full cursor-pointer border-2 border-red-600 bg-white hover:border-red-400 hover:scale-150 transition-all`}
                  style={{width: `${PORT_SIZE}px`, height: `${PORT_SIZE}px`, transform: `translate(-50%, ${PORT_OFFSET_Y}px)`}}
                  title={`Output from ${tool.name}`}
                ></div>
                
                {/* Action buttons for selected node */}
                {isSelected && (
                  <div className="absolute -right-10 top-0 flex flex-col space-y-1 bg-white shadow-md rounded-md p-1 z-20">
                    <button 
                      className="text-gray-500 hover:text-red-500 p-1 rounded hover:bg-gray-100"
                      title="Delete node"
                      onClick={() => {
                        setConnections(prev => prev.filter(
                          conn => conn.fromToolInstanceId !== tool.instanceId && conn.toToolInstanceId !== tool.instanceId
                        ));
                        setDroppedToolsOnCanvas(prev => prev.filter(t => t.instanceId !== tool.instanceId));
                        setSelectedToolId(null);
                      }}
                    >
                      <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4" viewBox="0 0 20 20" fill="currentColor">
                        <path fillRule="evenodd" d="M9 2a1 1 0 00-.894.553L7.382 4H4a1 1 0 000 2v10a2 2 0 002 2h8a2 2 0 002-2V6a1 1 0 100-2h-3.382l-.724-1.447A1 1 0 0011 2H9zM7 8a1 1 0 012 0v6a1 1 0 11-2 0V8zm5-1a1 1 0 00-1 1v6a1 1 0 102 0V8a1 1 0 00-1-1z" clipRule="evenodd" />
                      </svg>
                    </button>
                    <button 
                      className="text-gray-500 hover:text-indigo-500 p-1 rounded hover:bg-gray-100"
                      title="Duplicate node (Ctrl+D)"
                      onClick={() => {
                        const newTool: CanvasTool = {
                          ...tool,
                          instanceId: `canvas-${tool.id}-${Date.now()}`,
                          x: tool.x + GRID_SIZE * 2,
                          y: tool.y + GRID_SIZE * 2,
                          properties: {...tool.properties}
                        };
                        setDroppedToolsOnCanvas(prev => [...prev, newTool]);
                        setSelectedToolId(newTool.instanceId);
                      }}
                    >
                      <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4" viewBox="0 0 20 20" fill="currentColor">
                        <path d="M7 9a2 2 0 012-2h6a2 2 0 012 2v6a2 2 0 01-2 2H9a2 2 0 01-2-2V9z" />
                        <path d="M5 3a2 2 0 00-2 2v6a2 2 0 002 2V5h8a2 2 0 00-2-2H5z" />
                      </svg>
                    </button>
                  </div>
                )}
              </div>
            );
          })}

          {/* Property editor popover */}
          {editingNode && (
            <div 
              className="fixed bg-white shadow-lg border border-gray-200 rounded-lg p-4 z-50"
              style={{
                top: editingNode.y,
                left: editingNode.x,
                transform: 'translate(-50%, -50%)'
              }}
            >
              <div className="flex justify-between items-center mb-3">
                <h3 className="text-sm font-medium">Edit Properties</h3>
                <button 
                  className="text-gray-400 hover:text-gray-600"
                  onClick={() => setEditingNode(null)}
                >
                  <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
                    <path fillRule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clipRule="evenodd" />
                  </svg>
                </button>
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-700 mb-1">
                  Description
                </label>
                <textarea 
                  className="w-full p-2 border border-gray-300 rounded-md text-sm"
                  rows={3}
                  placeholder="Enter description..."
                  onChange={(e) => {
                    const description = e.target.value;
                    setDroppedToolsOnCanvas(prev => 
                      prev.map(tool => 
                        tool.instanceId === editingNode.instanceId 
                          ? { ...tool, properties: { ...tool.properties, description } } 
                          : tool
                      )
                    );
                  }}
                  defaultValue={droppedToolsOnCanvas.find(t => t.instanceId === editingNode.instanceId)?.properties?.description || ''}
                />
              </div>
              <div className="mt-3 flex justify-end">
                <button
                  className="px-3 py-1 text-xs bg-indigo-600 hover:bg-indigo-500 text-white rounded-md transition-colors"
                  onClick={() => setEditingNode(null)}
                >
                  Done
                </button>
              </div>
            </div>
          )}
        </div>
        
        {/* Canvas Controls */}
        <div className="absolute bottom-4 right-4 flex flex-col space-y-2">
          {/* Snap to grid toggle */}
          <button
            className={`w-8 h-8 rounded-full flex items-center justify-center shadow ${
              snapToGrid ? 'bg-indigo-600 text-white' : 'bg-white text-gray-500'
            }`}
            onClick={() => setSnapToGrid(!snapToGrid)}
            title={snapToGrid ? "Disable snap to grid" : "Enable snap to grid"}
          >
            <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4" viewBox="0 0 20 20" fill="currentColor">
              <path fillRule="evenodd" d="M5 3a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2V5a2 2 0 00-2-2H5zm0 2h10v10H5V5zm2 2a1 1 0 011-1h2a1 1 0 011 1v2a1 1 0 01-1 1H8a1 1 0 01-1-1V7zm6 0a1 1 0 011-1h2a1 1 0 011 1v2a1 1 0 01-1 1h-2a1 1 0 01-1-1V7zm-6 6a1 1 0 011-1h2a1 1 0 011 1v2a1 1 0 01-1 1H8a1 1 0 01-1-1v-2zm6 0a1 1 0 011-1h2a1 1 0 011 1v2a1 1 0 01-1 1h-2a1 1 0 01-1-1v-2z" clipRule="evenodd" />
            </svg>
          </button>
          
          {/* Zoom controls */}
          <div className="bg-white shadow rounded-lg p-1 flex flex-col items-center">
            <button
              className="p-1 hover:bg-gray-100 rounded-md text-gray-500"
              onClick={handleZoomIn}
              title="Zoom in"
            >
              <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4" viewBox="0 0 20 20" fill="currentColor">
                <path fillRule="evenodd" d="M10 5a1 1 0 011 1v3h3a1 1 0 110 2h-3v3a1 1 0 11-2 0v-3H6a1 1 0 110-2h3V6a1 1 0 011-1z" clipRule="evenodd" />
              </svg>
            </button>
            <div className="text-xs font-medium text-gray-500 py-1">{zoomLevel}%</div>
            <button
              className="p-1 hover:bg-gray-100 rounded-md text-gray-500"
              onClick={handleZoomOut}
              title="Zoom out"
            >
              <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4" viewBox="0 0 20 20" fill="currentColor">
                <path fillRule="evenodd" d="M5 10a1 1 0 011-1h8a1 1 0 110 2H6a1 1 0 01-1-1z" clipRule="evenodd" />
              </svg>
            </button>
          </div>
          
          {/* Mini-map (on hover) */}
          <div 
            className="relative"
            onMouseEnter={() => setShowMiniMap(true)}
            onMouseLeave={() => setShowMiniMap(false)}
          >
            <button className="w-8 h-8 bg-white shadow rounded-full flex items-center justify-center text-gray-500">
              <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4" viewBox="0 0 20 20" fill="currentColor">
                <path fillRule="evenodd" d="M12 1.586l-4 4v12.828l4-4V1.586zM3.707 3.293A1 1 0 002 4v10a1 1 0 00.293.707L6 18.414V5.586L3.707 3.293zM17.707 5.293L14 1.586v12.828l2.293 2.293A1 1 0 0018 16V6a1 1 0 00-.293-.707z" clipRule="evenodd" />
              </svg>
            </button>
            
            {showMiniMap && (
              <div className="absolute bottom-10 right-0 w-40 h-40 bg-white shadow-lg rounded-lg p-2 border border-gray-200">
                <div className="w-full h-full bg-gray-50 rounded relative">
                  {droppedToolsOnCanvas.map(tool => {
                    const colors = getCategoryColor(tool.category);
                    // Calculate relative position for minimap
                    const maxX = designerCanvasRef.current?.scrollWidth || 1;
                    const maxY = designerCanvasRef.current?.scrollHeight || 1;
                    const relX = (tool.x / maxX) * 100;
                    const relY = (tool.y / maxY) * 100;
                    
                    return (
                      <div 
                        key={`mini-${tool.instanceId}`}
                        className={`absolute w-2 h-2 rounded-sm ${colors.bg}`}
                        style={{
                          left: `${relX}%`,
                          top: `${relY}%`,
                        }}
                      />
                    );
                  })}
                </div>
              </div>
            )}
          </div>
        </div>
      </main>
    </div>
  );
} 