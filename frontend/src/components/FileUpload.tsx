import { useState, useRef } from 'react'
import { Upload, File, AlertCircle, CheckCircle, X } from 'lucide-react'
import axios from 'axios'

interface FileUploadProps {
  onUploadSuccess?: (data: any) => void
  onUploadError?: (error: string) => void
  uploadType?: 'process' | 'match'
}

interface UploadResult {
  message: string
  total_patients: number
  anonymized_patients?: any[]
  matching_results?: any[]
  file_info: {
    filename: string
    file_type: string
    processed_at: string
  }
}

const FileUpload = ({ onUploadSuccess, onUploadError, uploadType = 'process' }: FileUploadProps) => {
  const [isDragging, setIsDragging] = useState(false)
  const [uploading, setUploading] = useState(false)
  const [uploadResult, setUploadResult] = useState<UploadResult | null>(null)
  const [error, setError] = useState<string | null>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(true)
  }

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(false)
  }

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(false)
    
    const files = Array.from(e.dataTransfer.files)
    if (files.length > 0) {
      handleFileUpload(files[0])
    }
  }

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files
    if (files && files.length > 0) {
      handleFileUpload(files[0])
    }
  }

  const handleFileUpload = async (file: File) => {
    // Validate file type
    const allowedTypes = ['application/json', 'text/csv', 'application/vnd.ms-excel']
    const allowedExtensions = ['.json', '.csv']
    
    const hasValidType = allowedTypes.includes(file.type) || 
                        allowedExtensions.some(ext => file.name.toLowerCase().endsWith(ext))
    
    if (!hasValidType) {
      const errorMsg = 'Please upload a JSON or CSV file only.'
      setError(errorMsg)
      onUploadError?.(errorMsg)
      return
    }

    // Check file size (16MB limit)
    if (file.size > 16 * 1024 * 1024) {
      const errorMsg = 'File size must be less than 16MB.'
      setError(errorMsg)
      onUploadError?.(errorMsg)
      return
    }

    setUploading(true)
    setError(null)
    setUploadResult(null)

    const formData = new FormData()
    formData.append('file', file)

    try {
      const endpoint = uploadType === 'match' ? '/api/upload-and-match' : '/api/upload-patients'
      const response = await axios.post(`http://localhost:5000${endpoint}`, formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      })

      setUploadResult(response.data)
      onUploadSuccess?.(response.data)
    } catch (err: any) {
      const errorMsg = err.response?.data?.message || 'File upload failed'
      setError(errorMsg)
      onUploadError?.(errorMsg)
    } finally {
      setUploading(false)
    }
  }

  const clearResults = () => {
    setUploadResult(null)
    setError(null)
    if (fileInputRef.current) {
      fileInputRef.current.value = ''
    }
  }

  return (
    <div className="space-y-4">
      {/* Upload Area */}
      <div
        className={`border-2 border-dashed rounded-lg p-8 text-center transition-colors ${
          isDragging
            ? 'border-blue-500 bg-blue-50'
            : 'border-gray-300 hover:border-gray-400'
        } ${uploading ? 'opacity-50 pointer-events-none' : ''}`}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
      >
        <input
          ref={fileInputRef}
          type="file"
          accept=".json,.csv"
          onChange={handleFileSelect}
          className="hidden"
        />
        
        <div className="space-y-4">
          <div className="flex justify-center">
            <Upload className={`h-12 w-12 ${isDragging ? 'text-blue-500' : 'text-gray-400'}`} />
          </div>
          
          <div>
            <h3 className="text-lg font-medium text-gray-900">
              {uploadType === 'match' ? 'Upload & Match Patients' : 'Upload Patient Data'}
            </h3>
            <p className="text-sm text-gray-600 mt-1">
              Drag and drop your JSON or CSV file here, or click to browse
            </p>
          </div>
          
          <button
            onClick={() => fileInputRef.current?.click()}
            disabled={uploading}
            className="bg-blue-600 text-white px-4 py-2 rounded-md hover:bg-blue-700 disabled:opacity-50"
          >
            {uploading ? 'Uploading...' : 'Choose File'}
          </button>
          
          <div className="text-xs text-gray-500">
            Supported formats: JSON, CSV • Max size: 16MB
          </div>
        </div>
      </div>

      {/* Loading State */}
      {uploading && (
        <div className="bg-blue-50 border border-blue-200 rounded-md p-4">
          <div className="flex items-center">
            <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-blue-600 mr-3"></div>
            <span className="text-blue-700">
              {uploadType === 'match' ? 'Processing file and matching to trials...' : 'Processing and anonymizing patient data...'}
            </span>
          </div>
        </div>
      )}

      {/* Error State */}
      {error && (
        <div className="bg-red-50 border border-red-200 rounded-md p-4">
          <div className="flex items-start">
            <AlertCircle className="h-5 w-5 text-red-400 mr-3 mt-0.5" />
            <div className="flex-1">
              <h4 className="text-red-800 font-medium">Upload Failed</h4>
              <p className="text-red-700 text-sm mt-1">{error}</p>
            </div>
            <button
              onClick={clearResults}
              className="text-red-400 hover:text-red-600"
            >
              <X className="h-4 w-4" />
            </button>
          </div>
        </div>
      )}

      {/* Success State */}
      {uploadResult && (
        <div className="bg-green-50 border border-green-200 rounded-md p-4">
          <div className="flex items-start">
            <CheckCircle className="h-5 w-5 text-green-400 mr-3 mt-0.5" />
            <div className="flex-1">
              <h4 className="text-green-800 font-medium">Upload Successful</h4>
              <div className="text-green-700 text-sm mt-1 space-y-1">
                <p>{uploadResult.message}</p>
                <div className="flex items-center space-x-4 text-xs">
                  <span className="flex items-center">
                    <File className="h-3 w-3 mr-1" />
                    {uploadResult.file_info.filename}
                  </span>
                  <span>
                    {uploadResult.total_patients} patient{uploadResult.total_patients !== 1 ? 's' : ''} processed
                  </span>
                  <span>
                    {uploadResult.file_info.file_type.toUpperCase()} format
                  </span>
                </div>
              </div>
            </div>
            <button
              onClick={clearResults}
              className="text-green-400 hover:text-green-600"
            >
              <X className="h-4 w-4" />
            </button>
          </div>
        </div>
      )}

      {/* File Format Help */}
      <div className="bg-gray-50 rounded-md p-4">
        <h4 className="text-sm font-medium text-gray-900 mb-2">Supported File Formats</h4>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs text-gray-600">
          <div>
            <p className="font-medium mb-1">JSON Format:</p>
            <pre className="bg-white p-2 rounded border text-xs overflow-x-auto">
{`{
  "patient_id": "P001",
  "name": "John Doe",
  "age": 45,
  "gender": "male",
  "diagnosis": ["Diabetes"],
  "medications": ["Metformin"]
}`}
            </pre>
          </div>
          <div>
            <p className="font-medium mb-1">CSV Format:</p>
            <pre className="bg-white p-2 rounded border text-xs overflow-x-auto">
{`patient_id,name,age,gender,diagnosis
P001,John Doe,45,male,Diabetes
P002,Jane Smith,32,female,Cancer`}
            </pre>
          </div>
        </div>
      </div>
    </div>
  )
}

export default FileUpload
