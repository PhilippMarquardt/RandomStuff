import { API_BASE_URL, API_ENDPOINTS } from './config';

export async function fetchCollections(): Promise<string[]> {
  try {
    const response = await fetch(`${API_BASE_URL}${API_ENDPOINTS.collections}`);
    if (response.ok) {
      const data = await response.json();
      return data;
    }
    return [];
  } catch (error) {
    console.error('Error fetching collections:', error);
    return [];
  }
}

export async function searchDocuments(query: string, collectionName: string): Promise<string> {
  try {
    const response = await fetch(`${API_BASE_URL}${API_ENDPOINTS.search}`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        query: query,
        collection_name: collectionName,
        k: 3 // Get top 3 relevant documents
      }),
    });

    if (response.ok) {
      const searchResults = await response.json();
      if (searchResults.results && searchResults.results.length > 0) {
        // Format the search results into context
        const context = searchResults.results
          .map((result: any, index: number) => 
            `Document ${index + 1} (from ${result.metadata.source_file}):\n${result.content}`
          )
          .join('\n\n');
        return context;
      }
    }
  } catch (error) {
    console.error('Error searching documents:', error);
  }
  return '';
} 