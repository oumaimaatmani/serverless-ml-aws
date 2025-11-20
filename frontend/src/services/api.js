import axios from 'axios';

// This will be set via environment variables
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:3000/api';

console.log('API Base URL:', API_BASE_URL);
console.log('Environment vars:', import.meta.env);

export const api = {
  // Get presigned URL for S3 upload
  async getPresignedUrl(fileName, fileType, userId = 'anonymous') {
    try {
      const response = await axios.post(`${API_BASE_URL}/upload-url`, {
        fileName,
        fileType,
        userId
      });
      return response.data;
    } catch (error) {
      console.error('Error getting presigned URL:', error);
      throw error;
    }
  },

  // Upload file directly to S3 using presigned URL
  async uploadToS3(presignedUrl, file) {
    try {
      await axios.put(presignedUrl, file, {
        headers: {
          'Content-Type': file.type
        }
      });
    } catch (error) {
      console.error('Error uploading to S3:', error);
      throw error;
    }
  },

  // Get analysis results for a specific image
  async getAnalysisResults(imageId) {
    try {
      const response = await axios.get(`${API_BASE_URL}/results/${imageId}`);
      return response.data;
    } catch (error) {
      console.error('Error fetching results:', error);
      throw error;
    }
  },

  // List recent uploads
  async listRecentUploads(limit = 20) {
    try {
      const response = await axios.get(`${API_BASE_URL}/results`, {
        params: { limit }
      });
      // Backend returns {count, results, has_more}, transform to match expected format
      return {
        items: response.data.results || [],
        count: response.data.count || 0,
        has_more: response.data.has_more || false
      };
    } catch (error) {
      console.error('Error fetching recent uploads:', error);
      throw error;
    }
  }
};
