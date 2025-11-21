import axios from 'axios';

// API Base URL from environment variables
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'https://1l0ep7fajj.execute-api.us-east-1.amazonaws.com/prod';

console.log('API Base URL:', API_BASE_URL);
console.log('Environment vars:', import.meta.env);

// Create axios instance with default config
const axiosInstance = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Response interceptor for error handling
axiosInstance.interceptors.response.use(
  (response) => response,
  (error) => {
    console.error('API Error:', {
      url: error.config?.url,
      method: error.config?.method,
      status: error.response?.status,
      message: error.message,
      data: error.response?.data,
    });
    return Promise.reject(error);
  }
);

// Request interceptor for logging
axiosInstance.interceptors.request.use(
  (config) => {
    console.log('API Request:', config.method?.toUpperCase(), config.url);
    return config;
  },
  (error) => Promise.reject(error)
);

export const api = {
  /**
   * Get presigned URL for S3 upload
   * @param {string} fileName - Name of the file to upload
   * @param {string} fileType - MIME type of the file
   * @param {string} userId - User identifier (default: 'anonymous')
   * @returns {Promise<Object>} Presigned URL data
   */
  async getPresignedUrl(fileName, fileType, userId = 'anonymous') {
    try {
      const response = await axiosInstance.post('/upload-url', {
        fileName,
        fileType,
        userId,
      });
      return response.data;
    } catch (error) {
      console.error('Error getting presigned URL:', error);
      throw new Error(
        error.response?.data?.message || 'Failed to get upload URL'
      );
    }
  },

  /**
   * Upload file directly to S3 using presigned URL
   * @param {string} presignedUrl - Presigned S3 URL
   * @param {File} file - File object to upload
   * @returns {Promise<void>}
   */
  async uploadToS3(presignedUrl, file) {
    try {
      await axios.put(presignedUrl, file, {
        headers: {
          'Content-Type': file.type,
        },
        onUploadProgress: (progressEvent) => {
          const percentCompleted = Math.round(
            (progressEvent.loaded * 100) / progressEvent.total
          );
          console.log('Upload progress:', percentCompleted + '%');
        },
      });
    } catch (error) {
      console.error('Error uploading to S3:', error);
      throw new Error('Failed to upload file to S3');
    }
  },

  /**
   * Get analysis results for a specific image
   * @param {string} imageId - Unique image identifier
   * @returns {Promise<Object>} Analysis results
   */
  async getAnalysisResults(imageId) {
    try {
      const response = await axiosInstance.get(`/results/${imageId}`);
      return response.data;
    } catch (error) {
      // Don't throw immediately for 404, let caller handle it
      if (error.response?.status === 404) {
        const notFoundError = new Error('Results not found');
        notFoundError.response = error.response;
        throw notFoundError;
      }
      console.error('Error fetching analysis results:', error);
      throw new Error(
        error.response?.data?.message || error.message || 'Failed to fetch analysis results'
      );
    }
  },

  /**
   * List recent uploads with optional filters
   * @param {number} limit - Maximum number of results to return
   * @param {Object} filters - Optional filters (confidence, is_safe, has_faces, etc.)
   * @returns {Promise<Object>} List of uploads
   */
  async listRecentUploads(limit = 20, filters = {}) {
    try {
      const params = {
        limit,
        ...filters,
      };
      
      const response = await axiosInstance.get('/results', { params });
      
      // Transform backend response to match expected format
      return {
        items: response.data.results || response.data.items || [],
        count: response.data.count || 0,
        has_more: response.data.has_more || false,
      };
    } catch (error) {
      console.error('Error fetching recent uploads:', error);
      throw new Error(
        error.response?.data?.message || 'Failed to fetch recent uploads'
      );
    }
  },

  /**
   * Get filtered results
   * @param {Object} filters - Filter parameters
   * @returns {Promise<Object>} Filtered results
   */
  async getFilteredResults(filters) {
    return this.listRecentUploads(filters.limit || 20, filters);
  },

  /**
   * Health check endpoint
   * @returns {Promise<Object>} API health status
   */
  async healthCheck() {
    try {
      const response = await axiosInstance.get('/health');
      return response.data;
    } catch (error) {
      console.error('Health check failed:', error);
      return { status: 'error', message: error.message };
    }
  },
};

export default api;