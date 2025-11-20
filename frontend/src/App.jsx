import { useState } from 'react'
import ImageUpload from './components/ImageUpload'
import ResultsDisplay from './components/ResultsDisplay'
import './App.css'

function App() {
  const [uploadedImageId, setUploadedImageId] = useState(null)

  const handleUploadSuccess = (imageId) => {
    setUploadedImageId(imageId)
  }

  return (
    <div className="app">
      <header className="app-header">
        <h1>AWS Image Analysis</h1>
        <p className="subtitle">AI-powered image analysis using AWS Rekognition</p>
      </header>

      <main className="app-main">
        <div className="app-grid">
          <div className="upload-section">
            <ImageUpload onUploadSuccess={handleUploadSuccess} />
          </div>

          <div className="results-section">
            <ResultsDisplay imageId={uploadedImageId} />
          </div>
        </div>
      </main>

      <footer className="app-footer">
        <p>Powered by AWS Lambda, Step Functions, Rekognition & DynamoDB</p>
      </footer>
    </div>
  )
}

export default App
