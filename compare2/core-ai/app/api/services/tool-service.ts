import { API_BASE_URL, API_ENDPOINTS } from '../config';

export interface Tool {
  name: string;
  description: string;
  enabled: boolean;
}

interface ApiTool {
  name: string;
  description: string;
}

export const toolService = {
  /**
   * Fetch all available tools
   */
  async fetchTools(): Promise<Tool[]> {
    try {
      const response = await fetch(`${API_BASE_URL}${API_ENDPOINTS.toolsList}`);
      if (response.ok) {
        const data = await response.json();
        // Initialize tools with 'enabled' state
        const initialTools = data.map((tool: ApiTool) => ({
          ...tool,
          enabled: true, // All tools enabled by default
        }));
        return initialTools;
      } else {
        // Fallback for UI testing if backend is down
        return [
          { name: 'get_weather', description: 'Get current weather', enabled: true },
          { name: 'search_web', description: 'Search the web', enabled: true },
          { name: 'calculate', description: 'Perform calculations', enabled: true },
        ];
      }
    } catch (error) {
      console.error('Error fetching tools:', error);
      // Fallback for UI testing if backend is down
      return [
        { name: 'get_weather', description: 'Get current weather', enabled: true },
        { name: 'search_web', description: 'Search the web', enabled: true },
        { name: 'calculate', description: 'Perform calculations', enabled: true },
      ];
    }
  }
};

// Legacy exports for backward compatibility
export const fetchTools = toolService.fetchTools; 