import { useState } from 'react';
import { api } from '../services/api';
import './ImageUpload.css';

function ImageUpload({ onUploadSuccess }) {
  const [selectedFile, setSelectedFile] = useState(null);
  const [preview, setPreview] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [uploadStatus, setUploadStatus] = useState('');
  const [error, setError] = useState('');

  const handleFileSelect = (event) => {
    const file = event.target.files[0];
    if (file) {
      // Validate file type
      const validTypes = ['image/jpeg', 'image/jpg', 'image/png', 'image/gif', 'image/bmp', 'image/webp'];
      if (!validTypes.includes(file.type)) {
        setError('Please select a valid image file (JPEG, PNG, GIF, BMP, WEBP)');
        return;
      }

      // Validate file size (max 10MB)
      if (file.size > 10 * 1024 * 1024) {
        setError('File size must be less than 10MB');
        return;
      }

      setSelectedFile(file);
      setError('');

      // Create preview
      const reader = new FileReader();
      reader.onloadend = () => {
        setPreview(reader.result);
      };
      reader.readAsDataURL(file);
    }
  };

  const handleUpload = async () => {
    if (!selectedFile) {
      setError('Please select a file first');
      return;
    }

    setUploading(true);
    setUploadStatus('Getting upload URL...');
    setError('');

    try {
      // Step 1: Get presigned URL
      const { uploadUrl, imageId } = await api.getPresignedUrl(
        selectedFile.name,
        selectedFile.type
      );

      // Step 2: Upload to S3
      setUploadStatus('Uploading image...');
      await api.uploadToS3(uploadUrl, selectedFile);

      // Step 3: Success
      setUploadStatus('Upload successful! Analysis in progress...');

      // Reset form
      setTimeout(() => {
        setSelectedFile(null);
        setPreview(null);
        setUploadStatus('');
        if (onUploadSuccess) {
          onUploadSuccess(imageId);
        }
      }, 2000);

    } catch (err) {
      setError('Upload failed: ' + (err.response?.data?.error || err.message));
      setUploadStatus('');
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
          disabled={uploading}
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
          disabled={!selectedFile || uploading}
          className="upload-button"
        >
          {uploading ? 'Uploading...' : 'Upload & Analyze'}
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
