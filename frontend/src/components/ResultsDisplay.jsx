import { useState, useEffect } from 'react';
import { api } from '../services/api';
import './ResultsDisplay.css';

function ResultsDisplay({ imageId }) {
  const [results, setResults] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [recentUploads, setRecentUploads] = useState([]);
  const [selectedImage, setSelectedImage] = useState(null);
  const [autoRefresh, setAutoRefresh] = useState(false);

  useEffect(() => {
    loadRecentUploads();
  }, []);

  useEffect(() => {
    if (imageId) {
      setSelectedImage(imageId);
      loadResults(imageId);
      setAutoRefresh(true);
    }
  }, [imageId]);

  useEffect(() => {
    if (autoRefresh && selectedImage) {
      const interval = setInterval(() => {
        loadResults(selectedImage, true);
      }, 3000); // Poll every 3 seconds

      return () => clearInterval(interval);
    }
  }, [autoRefresh, selectedImage]);

  const loadRecentUploads = async () => {
    try {
      const data = await api.listRecentUploads(10);
      setRecentUploads(data.items || []);
    } catch (err) {
      console.error('Error loading recent uploads:', err);
    }
  };

  const loadResults = async (imgId, silent = false) => {
    if (!silent) {
      setLoading(true);
      setError('');
    }

    try {
      const data = await api.getAnalysisResults(imgId);
      setResults(data);

      // Stop auto-refresh if analysis data is present (completed)
      if (data && data.analysis) {
        setAutoRefresh(false);
        loadRecentUploads(); // Refresh the list
      }
    } catch (err) {
      // If 404, results not yet available - keep polling silently
      if (err.response?.status === 404) {
        if (autoRefresh) {
          // Keep polling silently, don't show error
          console.log('Results not ready yet, polling...');
        } else if (!silent) {
          setError('Image not found. It may have been deleted or expired.');
          setAutoRefresh(false);
        }
      } else if (!silent && !autoRefresh) {
        // Only show errors if we're not auto-refreshing
        setError('Failed to load results: ' + (err.response?.data?.error || err.message));
        setAutoRefresh(false);
      }
    } finally {
      if (!silent) {
        setLoading(false);
      }
    }
  };

  const handleSelectImage = (imgId) => {
    setSelectedImage(imgId);
    loadResults(imgId);
    setAutoRefresh(false);
  };

  const renderObjects = () => {
    const labels = results?.analysis?.labels?.labels;
    if (!labels || labels.length === 0) return null;

    return (
      <div className="results-section">
        <h3>Objects Detected ({labels.length})</h3>
        <div className="labels-grid">
          {labels.slice(0, 20).map((label, idx) => (
            <div key={idx} className="label-card">
              <div className="label-name">{label.Name}</div>
              <div className="label-confidence">{label.Confidence.toFixed(1)}%</div>
            </div>
          ))}
        </div>
      </div>
    );
  };

  const renderFaces = () => {
    const faces = results?.analysis?.faces?.faces;
    if (!faces || faces.length === 0) return null;

    return (
      <div className="results-section">
        <h3>Faces Detected ({faces.length})</h3>
        <div className="faces-grid">
          {faces.map((face, idx) => (
            <div key={idx} className="face-card">
              <h4>Face {idx + 1}</h4>
              <div className="face-details">
                <div className="face-attribute">
                  <span className="attribute-label">Confidence:</span>
                  <span className="attribute-value">
                    {face.confidence?.toFixed(1)}%
                  </span>
                </div>
                {face.age_range && (
                  <div className="face-attribute">
                    <span className="attribute-label">Age Range:</span>
                    <span className="attribute-value">
                      {face.age_range.Low} - {face.age_range.High}
                    </span>
                  </div>
                )}
                {face.gender && (
                  <div className="face-attribute">
                    <span className="attribute-label">Gender:</span>
                    <span className="attribute-value">
                      {face.gender.Value} ({face.gender.Confidence?.toFixed(1)}%)
                    </span>
                  </div>
                )}
                {face.emotions && face.emotions.length > 0 && (
                  <div className="face-attribute">
                    <span className="attribute-label">Emotions:</span>
                    <div className="emotions-list">
                      {face.emotions.slice(0, 3).map((emotion, i) => (
                        <div key={i} className="emotion">
                          {emotion.Type}: {emotion.Confidence?.toFixed(1)}%
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>
      </div>
    );
  };

  const renderModeration = () => {
    const isSafe = results?.is_safe;
    const moderationLabels = results?.analysis?.moderation?.labels || [];

    return (
      <div className="results-section">
        <h3>Content Moderation</h3>
        <div className={`safety-badge ${isSafe ? 'safe' : 'unsafe'}`}>
          {isSafe ? 'Content is Safe' : 'Content Flagged'}
        </div>
        {moderationLabels.length > 0 && (
          <div className="moderation-labels">
            {moderationLabels.map((label, idx) => (
              <div key={idx} className="moderation-label">
                <span className="label-name">{label.Name || label.name}</span>
                <span className="label-confidence">{(label.Confidence || label.confidence)?.toFixed(1)}%</span>
              </div>
            ))}
          </div>
        )}
      </div>
    );
  };

  return (
    <div className="results-container">
      <h2>Analysis Results</h2>

      <div className="recent-uploads">
        <h3>Recent Uploads</h3>
        <div className="uploads-list">
          {recentUploads.map((upload) => (
            <button
              key={upload.image_id}
              className={`upload-item ${selectedImage === upload.image_id ? 'active' : ''}`}
              onClick={() => handleSelectImage(upload.image_id)}
            >
              <div className="upload-name">{upload.image_id.substring(0, 32)}...</div>
              <div className="upload-time">
                {upload.processed_timestamp ? new Date(upload.processed_timestamp * 1000).toLocaleString() : 'Processing...'}
              </div>
              <div className="upload-confidence">
                {upload.confidence ? `${upload.confidence.toFixed(1)}%` : 'N/A'}
              </div>
            </button>
          ))}
        </div>
      </div>

      {loading && (
        <div className="loading">Loading results...</div>
      )}

      {error && (
        <div className="error-message">{error}</div>
      )}

      {results && !loading && (
        <div className="results-content">
          <div className="results-header">
            <h3>{results.image_id}</h3>
            <div className="results-meta">
              <span>Confidence: <strong>{results.confidence?.toFixed(1)}%</strong></span>
              {autoRefresh && <span className="refreshing">Refreshing...</span>}
            </div>
          </div>

          {!results.analysis && autoRefresh && (
            <div className="processing-message">
              🔄 Analysis in progress. Results will appear shortly...
              <br />
              <small>This usually takes 2-3 seconds</small>
            </div>
          )}

          {!results.analysis && !autoRefresh && (
            <div className="processing-message">
              ⏳ Waiting for analysis results...
              <br />
              <small>Try refreshing if this persists</small>
            </div>
          )}

          {results.analysis && (
            <>
              <div className="summary-section">
                <p><strong>Summary:</strong> {results.summary}</p>
              </div>
              {renderModeration()}
              {renderObjects()}
              {renderFaces()}
            </>
          )}
        </div>
      )}

      {!results && !loading && !error && (
        <div className="no-results">
          Upload an image or select one from recent uploads to view results.
        </div>
      )}
    </div>
  );
}

export default ResultsDisplay;
