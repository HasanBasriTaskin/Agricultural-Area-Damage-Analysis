/**
 * A basic API client for communicating with the FastAPI backend.
 */

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export async function fetcher<T>(endpoint: string, options?: RequestInit): Promise<T> {
  const url = `${API_BASE_URL}${endpoint}`;
  
  const headers: HeadersInit = {
    'Content-Type': 'application/json',
    ...(options?.headers || {}),
  };

  // İleride Next-Auth session üzerinden JWT token alıp Authorization header'ına eklenebilir
  // const session = await getSession();
  // if (session?.accessToken) headers['Authorization'] = `Bearer ${session.accessToken}`;

  const response = await fetch(url, {
    ...options,
    headers,
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.detail || `API request failed: ${response.status}`);
  }

  return response.json();
}

export const aoiApi = {
  list: () => fetcher<any[]>('/api/v1/aois/'),
  create: (data: { name: string; geom: any; properties?: any }) => 
    fetcher<any>('/api/v1/aois/', {
      method: 'POST',
      body: JSON.stringify(data),
    }),
};
