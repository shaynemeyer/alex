// API configuration that works for both local and production environments
export const getApiUrl = () => {
  if (process.env.NODE_ENV === 'development') {
    return 'http://localhost:8000';
  }
  // Production: use relative path (CloudFront handles routing /api/* to API Gateway)
  return '';
};

export const API_URL = getApiUrl();