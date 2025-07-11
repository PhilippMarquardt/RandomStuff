// assets/renderer.js
window.dashAgGridComponentFunctions = window.dashAgGridComponentFunctions || {};

window.dashAgGridComponentFunctions.HtmlRenderer = function(props) {
  return React.createElement('span', {dangerouslySetInnerHTML: {__html: props.value}});
};

window.dashAgGridComponentFunctions.DualDivergeRenderer = function(props) {
  if (!props.data.pf_chart || !props.data.bm_chart) {
    return React.createElement('div');
  }
  return React.createElement('div', {style: {display: 'flex', flexDirection: 'column', height: '100%'}},
    React.createElement(window.dash_core_components.Graph, {figure: props.data.pf_chart, config: {displayModeBar: false}, style: {flex: 1}}),
    React.createElement(window.dash_core_components.Graph, {figure: props.data.bm_chart, config: {displayModeBar: false}, style: {flex: 1}})
  );
};

