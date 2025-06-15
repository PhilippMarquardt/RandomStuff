import React, { useState, useEffect } from 'react';
import dynamic from 'next/dynamic';
import { AgGridReact } from 'ag-grid-react';
import { themeAlpine } from 'ag-grid-community';
import type { VisualizationData, GraphData } from '../../types';

const Plot = dynamic(() => import('react-plotly.js'), { ssr: false });

const PlotlyGraphRenderer = ({ graphData }: { graphData: GraphData }) => {
  const [isClient, setIsClient] = useState(false);

  useEffect(() => {
    setIsClient(true);
  }, []);

  if (!isClient) {
    return (
      <div className="flex items-center justify-center h-64 bg-gray-50 border border-gray-200 rounded-lg my-4">
        <div className="text-gray-500">Loading chart...</div>
      </div>
    );
  }

  // Convert graph data to Plotly format
  const convertToPlotlyData = (type: string, data: Record<string, unknown> | Record<string, unknown>[]) => {
    // If data is already in array format (multiple series), return as is
    if (Array.isArray(data)) {
      return data.map((series: Record<string, unknown>) => ({
        ...series,
        type: getPlotlyType(type)
      }));
    }

    // Single series data
    const plotlyData: Record<string, unknown> = {
      type: getPlotlyType(type),
      ...data
    };

    return [plotlyData];
  };

  const getPlotlyType = (type: string): string => {
    switch (type) {
      case 'line': return 'scatter';
      case 'area': return 'scatter';
      case 'bubble': return 'scatter';
      case '3d_scatter': return 'scatter3d';
      case 'surface': return 'surface';
      default: return type;
    }
  };

  // Apply type-specific configurations
  const applyTypeSpecificConfig = (type: string, data: Record<string, unknown>[]) => {
    return data.map((trace: Record<string, unknown>) => {
      switch (type) {
        case 'line':
          return { ...trace, mode: 'lines+markers' };
        case 'area':
          return { ...trace, fill: 'tonexty', mode: 'lines' };
        case 'bubble':
          return { 
            ...trace, 
            mode: 'markers',
            marker: {
              size: (trace.size as number[]) || ((trace.marker as Record<string, unknown>)?.size as number) || 10,
              ...(trace.marker as Record<string, unknown>)
            }
          };
        case 'histogram':
          return { ...trace, nbinsx: (trace.nbinsx as number) || 20 };
        default:
          return trace;
      }
    });
  };

  try {
    const plotlyData = convertToPlotlyData(graphData.type, graphData.data);
    const configuredData = applyTypeSpecificConfig(graphData.type, plotlyData);

    const defaultLayout: Record<string, unknown> = {
      autosize: true,
      margin: { l: 50, r: 50, t: 50, b: 50 },
      paper_bgcolor: 'rgba(0,0,0,0)',
      plot_bgcolor: 'rgba(0,0,0,0)',
      font: { family: 'Inter, sans-serif', size: 12 },
      ...graphData.layout
    };

    const defaultConfig: Record<string, unknown> = {
      displayModeBar: true,
      displaylogo: false,
      modeBarButtonsToRemove: ['pan2d', 'lasso2d', 'select2d'],
      responsive: true,
      ...graphData.config
    };

    return (
      <div className="my-4 p-4 bg-white border border-gray-200 rounded-lg shadow-sm">
        <Plot
          data={configuredData as never}
          layout={defaultLayout as never}
          config={defaultConfig as never}
          style={{ width: '100%', height: '400px' }}
          useResizeHandler={true}
        />
      </div>
    );
  } catch (error) {
    return (
      <div className="text-red-500 text-sm p-4 bg-red-50 border border-red-200 rounded-md my-4">
        <div className="font-medium">Error rendering chart:</div>
        <div className="mt-2">{error instanceof Error ? error.message : 'Unknown error occurred'}</div>
      </div>
    );
  }
};

export const RenderVisualization = ({ visData }: { visData: VisualizationData }) => {
    if (visData.type === 'table' && visData.data) {
      const keys = Object.keys(visData.data);
      const columnDefs = keys.map(key => ({
        headerName: key,
        field: key,
        sortable: true,
        filter: true,
        resizable: true,
      }));

      const rowData: { [key: string]: string | number }[] = [];
      if (keys.length > 0) {
        const numRows = visData.data[keys[0]].length;
        for (let i = 0; i < numRows; i++) {
          const row: { [key: string]: string | number } = {};
          keys.forEach(key => {
            row[key] = visData.data[key][i];
          });
          rowData.push(row);
        }
      }

      return (
        <div className="bg-white p-4 rounded-lg shadow-md my-4">
          <div style={{ height: 400, width: '100%' }}>
            <AgGridReact
              rowData={rowData}
              columnDefs={columnDefs}
              pagination={true}
              paginationPageSize={10}
              theme={themeAlpine}
            />
          </div>
        </div>
      );
    } else if (visData.type !== 'table') {
        return <PlotlyGraphRenderer graphData={visData} />
    }
    return null;
}; 