# Visualization Examples for Chat Window

This document provides examples of all supported visualization types in the chat window using the `<START_FIGURE>` and `<END_FIGURE>` markers.

## Tables

Basic table example:
```
<START_FIGURE>
{
  "type": "table",
  "data": {
    "Product": ["Widget A", "Widget B", "Widget C"],
    "Sales": [100, 150, 80],
    "Revenue": [5000, 7500, 4000]
  }
}
<END_FIGURE>
```

## Line Charts

Simple line chart:
```
<START_FIGURE>
{
  "type": "line",
  "data": {
    "x": [1, 2, 3, 4, 5],
    "y": [10, 15, 13, 17, 20],
    "name": "Sales Trend"
  },
  "layout": {
    "title": "Monthly Sales",
    "xaxis": {"title": "Month"},
    "yaxis": {"title": "Sales ($1000s)"}
  }
}
<END_FIGURE>
```

Multi-series line chart:
```
<START_FIGURE>
{
  "type": "line",
  "data": [
    {
      "x": [1, 2, 3, 4, 5],
      "y": [10, 15, 13, 17, 20],
      "name": "Product A"
    },
    {
      "x": [1, 2, 3, 4, 5],
      "y": [16, 18, 17, 19, 25],
      "name": "Product B"
    }
  ],
  "layout": {
    "title": "Product Comparison",
    "xaxis": {"title": "Month"},
    "yaxis": {"title": "Sales"}
  }
}
<END_FIGURE>
```

## Bar Charts

Simple bar chart:
```
<START_FIGURE>
{
  "type": "bar",
  "data": {
    "x": ["Q1", "Q2", "Q3", "Q4"],
    "y": [20, 14, 23, 25],
    "name": "Quarterly Results"
  },
  "layout": {
    "title": "Quarterly Performance",
    "xaxis": {"title": "Quarter"},
    "yaxis": {"title": "Revenue (M$)"}
  }
}
<END_FIGURE>
```

## Scatter Plots

Simple scatter:
```
<START_FIGURE>
{
  "type": "scatter",
  "data": {
    "x": [1, 2, 3, 4, 5, 6],
    "y": [10, 11, 12, 13, 14, 15],
    "mode": "markers",
    "name": "Data Points"
  },
  "layout": {
    "title": "Correlation Analysis",
    "xaxis": {"title": "Variable X"},
    "yaxis": {"title": "Variable Y"}
  }
}
<END_FIGURE>
```

## Histograms

```
<START_FIGURE>
{
  "type": "histogram",
  "data": {
    "x": [1, 2, 2, 3, 3, 3, 4, 4, 4, 4, 5, 5, 5, 6, 6, 7],
    "name": "Distribution"
  },
  "layout": {
    "title": "Value Distribution",
    "xaxis": {"title": "Value"},
    "yaxis": {"title": "Frequency"}
  }
}
<END_FIGURE>
```

## Pie Charts

```
<START_FIGURE>
{
  "type": "pie",
  "data": {
    "labels": ["Product A", "Product B", "Product C", "Product D"],
    "values": [30, 25, 20, 25],
    "name": "Market Share"
  },
  "layout": {
    "title": "Market Share Distribution"
  }
}
<END_FIGURE>
```

## Box Plots

```
<START_FIGURE>
{
  "type": "box",
  "data": {
    "y": [0, 1, 1, 2, 3, 5, 8, 13, 21, 34, 55, 89],
    "name": "Sample Data"
  },
  "layout": {
    "title": "Statistical Distribution"
  }
}
<END_FIGURE>
```

## Heatmaps

```
<START_FIGURE>
{
  "type": "heatmap",
  "data": {
    "z": [[1, 20, 30], [20, 1, 60], [30, 60, 1]],
    "x": ["A", "B", "C"],
    "y": ["X", "Y", "Z"]
  },
  "layout": {
    "title": "Correlation Matrix"
  }
}
<END_FIGURE>
```

## Area Charts

```
<START_FIGURE>
{
  "type": "area",
  "data": {
    "x": [1, 2, 3, 4, 5],
    "y": [10, 15, 13, 17, 20],
    "name": "Area Series"
  },
  "layout": {
    "title": "Area Chart Example",
    "xaxis": {"title": "Time"},
    "yaxis": {"title": "Value"}
  }
}
<END_FIGURE>
```

## Bubble Charts

```
<START_FIGURE>
{
  "type": "bubble",
  "data": {
    "x": [1, 2, 3, 4],
    "y": [10, 11, 12, 13],
    "size": [20, 30, 40, 50],
    "name": "Bubble Data"
  },
  "layout": {
    "title": "Bubble Chart",
    "xaxis": {"title": "X Value"},
    "yaxis": {"title": "Y Value"}
  }
}
<END_FIGURE>
```

## 3D Scatter Plots

```
<START_FIGURE>
{
  "type": "3d_scatter",
  "data": {
    "x": [1, 2, 3, 4, 5],
    "y": [1, 4, 9, 16, 25],
    "z": [1, 8, 27, 64, 125],
    "mode": "markers",
    "name": "3D Points"
  },
  "layout": {
    "title": "3D Scatter Plot",
    "scene": {
      "xaxis": {"title": "X"},
      "yaxis": {"title": "Y"},
      "zaxis": {"title": "Z"}
    }
  }
}
<END_FIGURE>
```

## Advanced Examples

Multi-visualization message:
```
Here's the sales analysis:

<START_FIGURE>
{
  "type": "table",
  "data": {
    "Month": ["Jan", "Feb", "Mar"],
    "Sales": [100, 120, 115],
    "Target": [110, 110, 110]
  }
}
<END_FIGURE>

And here's the trend visualization:

<START_FIGURE>
{
  "type": "line",
  "data": [
    {
      "x": ["Jan", "Feb", "Mar"],
      "y": [100, 120, 115],
      "name": "Actual Sales"
    },
    {
      "x": ["Jan", "Feb", "Mar"],
      "y": [110, 110, 110],
      "name": "Target",
      "line": {"dash": "dash"}
    }
  ],
  "layout": {
    "title": "Sales vs Target"
  }
}
<END_FIGURE>
```

## Usage Tips

1. **Always wrap visualizations** in `<START_FIGURE>` and `<END_FIGURE>` markers
2. **Use proper JSON format** - ensure all quotes are double quotes
3. **Include layout configuration** for better-looking charts
4. **Test data formats** - ensure your data matches the expected Plotly format
5. **Multiple visualizations** are supported in a single message
6. **Error handling** - invalid JSON or data will show an error message instead of breaking the chat

## Data Format Guidelines

- **Line/Area/Scatter**: Use `x` and `y` arrays, or array of objects with `x`, `y`, and `name` properties
- **Bar**: Use `x` and `y` arrays for categories and values
- **Histogram**: Use `x` array for values to be binned
- **Pie**: Use `labels` and `values` arrays
- **Heatmap**: Use `z` for 2D array of values, `x` and `y` for axis labels
- **Box**: Use `y` for the data points
- **3D plots**: Use `x`, `y`, and `z` arrays

All visualization types support additional Plotly configuration through the `layout` and `config` properties. 