import { useState } from 'react';
import { api } from '../services/api';
import './ImageUpload.css';

function ImageUpload({ onUploadSuccess }) {
  const [selectedFile, setSelectedFile] = useState(null);
  const [preview, setPreview] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [processing, setProcessing] = useState(false);
  const [uploadStatus, setUploadStatus] = useState('');
  const [error, setError] = useState('');

  const handleFileSelect = (event) => {
    const file = event.target.files[0];
    if (file) {
      const validTypes = ['image/jpeg', 'image/jpg', 'image/png', 'image/gif', 'image/bmp', 'image/webp'];
      if (!validTypes.includes(file.type)) {
        setError('Please select a valid image file (JPEG, PNG, GIF, BMP, WEBP)');
        return;
      }

      if (file.size > 10 * 1024 * 1024) {
        setError('File size must be less than 10MB');
        return;
      }

      setSelectedFile(file);
      setError('');

      const reader = new FileReader();
      reader.onloadend = () => {
        setPreview(reader.result);
      };
      reader.readAsDataURL(file);
    }
  };

  // Updated polling function with better error handling
  const pollForResults = async (imageId, maxAttempts = 30) => {
    for (let attempt = 0; attempt < maxAttempts; attempt++) {
      try {
        console.log(`Polling attempt ${attempt + 1}/${maxAttempts} for image ${imageId}`);
        const results = await api.getAnalysisResults(imageId);
        
        // Check if we have valid results
        if (results && (results.status === 'completed' || results.labels || results.faces)) {
          console.log('Analysis completed:', results);
          return results;
        }
        
        // Wait before next attempt
        await new Promise(resolve => setTimeout(resolve, 2000));
      } catch (error) {
        const statusCode = error.response?.status;
        const errorMessage = error.message || '';
        
        // These errors mean "not ready yet", keep polling
        if (statusCode === 404 || 
            errorMessage.includes('not found') || 
            errorMessage.includes('Failed to fetch')) {
          console.log(`Results not ready (attempt ${attempt + 1}), waiting...`);
          await new Promise(resolve => setTimeout(resolve, 2000));
          continue;
        }
        
        // Other errors are real problems
        console.error('Error polling for results:', error);
        throw error;
      }
    }
    
    throw new Error('Processing timeout - results not available after 60 seconds');
  };

  const handleUpload = async () => {
    if (!selectedFile) {
      setError('Please select a file first');
      return;
    }

    setUploading(true);
    setProcessing(false);
    setUploadStatus('Getting upload URL...');
    setError('');

    try {
      // Step 1: Get presigned URL
      const { uploadUrl, imageId } = await api.getPresignedUrl(
        selectedFile.name,
        selectedFile.type
      );
      console.log('Got presigned URL for image:', imageId);

      // Step 2: Upload to S3
      setUploadStatus('Uploading image...');
      await api.uploadToS3(uploadUrl, selectedFile);
      console.log('Upload complete');

      // Step 3: Wait for processing
      setUploading(false);
      setProcessing(true);
      setUploadStatus('Processing with AWS Rekognition... (this may take 10-30 seconds)');

      const results = await pollForResults(imageId);
      
      // Step 4: Success
      setProcessing(false);
      setUploadStatus('Analysis complete!');

      // Reset form and notify parent
      setTimeout(() => {
        setSelectedFile(null);
        setPreview(null);
        setUploadStatus('');
        if (onUploadSuccess) {
          onUploadSuccess(results);
        }
      }, 2000);

    } catch (err) {
      console.error('Upload/Processing error:', err);
      setError('Error: ' + (err.message || 'Upload failed'));
      setUploadStatus('');
      setProcessing(false);
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="upload-container">
      <h2>Upload Image for Analysis</h2>

      <div className="upload-area">
        <input
          type="file"
          id="file-input"
          accept="image/jpeg,image/jpg,image/png,image/gif,image/bmp,image/webp"
          onChange={handleFileSelect}
          disabled={uploading || processing}
          className="file-input"
        />

        <label htmlFor="file-input" className="file-label">
          {selectedFile ? selectedFile.name : 'Choose an image file'}
        </label>

        {preview && (
          <div className="preview-container">
            <img src={preview} alt="Preview" className="preview-image" />
          </div>
        )}

        <button
          onClick={handleUpload}
          disabled={!selectedFile || uploading || processing}
          className="upload-button"
        >
          {uploading ? 'Uploading...' : processing ? 'Processing...' : 'Upload & Analyze'}
        </button>

        {uploadStatus && (
          <div className="status-message success">{uploadStatus}</div>
        )}

        {error && (
          <div className="status-message error">{error}</div>
        )}
      </div>

      <div className="info-box">
        <h3>Supported Formats</h3>
        <p>JPEG, PNG, GIF, BMP, WEBP (Max 10MB)</p>
        <h3>Analysis Includes</h3>
        <ul>
          <li>Object Detection</li>
          <li>Face Detection & Attributes</li>
          <li>Content Moderation</li>
        </ul>
      </div>
    </div>
  );
}

export default ImageUpload;