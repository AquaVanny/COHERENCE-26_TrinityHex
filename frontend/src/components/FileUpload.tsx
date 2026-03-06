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
    <div className="section-stack">
      {/* Upload Area */}
      <div
        className={`rounded-[12px] border-2 border-dashed p-8 text-center transition-colors ${
          isDragging
            ? 'border-[rgba(96,165,250,0.45)] bg-[rgba(96,165,250,0.08)]'
            : 'border-white/15 bg-[rgba(8,14,30,0.35)] hover:border-white/25'
        } ${uploading ? 'pointer-events-none opacity-50' : ''}`}
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
        
        <div className="section-stack">
          <div className="flex justify-center">
            <Upload className={`h-12 w-12 ${isDragging ? 'text-[var(--blue)]' : 'text-slate-400/80'}`} />
          </div>
          
          <div>
            <h3 className="text-lg font-medium text-white">
              {uploadType === 'match' ? 'Upload & Match Patients' : 'Upload Patient Data'}
            </h3>
            <p className="mt-1 text-sm muted-text">
              Drag and drop your JSON or CSV file here, or click to browse
            </p>
          </div>
          
          <button
            type="button"
            onClick={() => fileInputRef.current?.click()}
            disabled={uploading}
            className="soft-button mx-auto"
          >
            {uploading ? 'Uploading...' : 'Choose File'}
          </button>
          
          <div className="text-xs muted-text">
            Supported formats: JSON, CSV • Max size: 16MB
          </div>
        </div>
      </div>

      {/* Loading State */}
      {uploading && (
        <div className="rounded-[12px] border border-[rgba(96,165,250,0.2)] bg-[rgba(96,165,250,0.1)] p-4">
          <div className="flex items-center gap-3 text-sm" style={{ color: 'var(--blue)' }}>
            <div className="h-5 w-5 animate-spin rounded-full border-b-2 border-current"></div>
            <span>
              {uploadType === 'match' ? 'Processing file and matching to trials...' : 'Processing and anonymizing patient data...'}
            </span>
          </div>
        </div>
      )}

      {/* Error State */}
      {error && (
        <div className="rounded-[12px] border border-red-400/20 bg-red-500/10 p-4">
          <div className="flex items-start">
            <AlertCircle className="mr-3 mt-0.5 h-5 w-5 text-red-300" />
            <div className="flex-1">
              <h4 className="font-medium text-red-200">Upload Failed</h4>
              <p className="mt-1 text-sm text-red-200/90">{error}</p>
            </div>
            <button
              type="button"
              onClick={clearResults}
              className="text-red-300 hover:text-red-200"
            >
              <X className="h-4 w-4" />
            </button>
          </div>
        </div>
      )}

      {/* Success State */}
      {uploadResult && (
        <div className="rounded-[12px] border border-[rgba(52,211,153,0.2)] bg-[rgba(52,211,153,0.08)] p-4">
          <div className="flex items-start">
            <CheckCircle className="mr-3 mt-0.5 h-5 w-5 text-green-300" />
            <div className="flex-1">
              <h4 className="font-medium text-green-200">Upload Successful</h4>
              <div className="mt-1 space-y-1 text-sm text-green-200/90">
                <p>{uploadResult.message}</p>
                <div className="flex flex-wrap items-center gap-4 text-xs">
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
              type="button"
              onClick={clearResults}
              className="text-green-300 hover:text-green-200"
            >
              <X className="h-4 w-4" />
            </button>
          </div>
        </div>
      )}

      {/* File Format Help */}
      <div className="rounded-[12px] border border-white/10 bg-[rgba(8,14,30,0.35)] p-4">
        <h4 className="mb-2 text-sm font-medium text-white">Supported File Formats</h4>
        <div className="grid grid-cols-1 gap-4 text-xs muted-text md:grid-cols-2">
          <div>
            <p className="mb-1 font-medium text-slate-200">JSON Format:</p>
            <pre className="overflow-x-auto rounded border border-white/10 bg-[rgba(8,14,30,0.6)] p-2 text-xs text-slate-300">
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
            <p className="mb-1 font-medium text-slate-200">CSV Format:</p>
            <pre className="overflow-x-auto rounded border border-white/10 bg-[rgba(8,14,30,0.6)] p-2 text-xs text-slate-300">
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
