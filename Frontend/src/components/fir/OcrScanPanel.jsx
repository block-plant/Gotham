import { useState } from 'react'
import { ScanLine, CheckCircle2 } from 'lucide-react'
import * as ocrService from '../../services/ocrService.js'
import Button from '../common/Button.jsx'

export default function OcrScanPanel({ file, onApply }) {
  const [isScanning, setIsScanning] = useState(false)
  const [extracted, setExtracted] = useState(null)
  const [error, setError] = useState('')

  async function handleScan() {
    setIsScanning(true)
    setError('')
    setExtracted(null)
    try {
      const result = await ocrService.scanFirDocument(file)
      setExtracted(result)
    } catch (err) {
      setError('Could not scan the document. Please fill the form manually.')
    } finally {
      setIsScanning(false)
    }
  }

  if (!file) return null

  return (
    <div className="mt-3 rounded-md border border-border bg-bg p-4">
      {!extracted && !isScanning && (
        <Button variant="secondary" onClick={handleScan}>
          <ScanLine size={16} /> Scan FIR Document
        </Button>
      )}

      {isScanning && (
        <div className="flex items-center gap-2 text-sm text-text-secondary">
          <ScanLine className="animate-pulse text-primary" size={18} />
          Scanning document...
        </div>
      )}

      {error && <p className="text-sm text-danger">{error}</p>}

      {extracted && (
        <div>
          <div className="mb-2 flex items-center gap-2 text-sm font-medium text-success">
            <CheckCircle2 size={16} /> Extracted Information (Review)
          </div>
          <div className="grid grid-cols-1 gap-x-4 gap-y-1 text-sm text-text-secondary sm:grid-cols-2">
            <div><strong className="text-text-primary">Police Station:</strong> {extracted.policeStation}</div>
            <div><strong className="text-text-primary">FIR Number:</strong> {extracted.firNumber}</div>
            <div><strong className="text-text-primary">Complainant:</strong> {extracted.complainantFullName}</div>
            <div><strong className="text-text-primary">Place of Occurrence:</strong> {extracted.occurrencePlace}</div>
            <div><strong className="text-text-primary">Date of Occurrence:</strong> {extracted.dateOfOccurrence}</div>
            <div><strong className="text-text-primary">Nature of Offence:</strong> {extracted.natureOfOffence}</div>
          </div>
          <Button
            className="mt-3"
            onClick={() => onApply(extracted)}
          >
            Apply Extracted Information
          </Button>
        </div>
      )}
    </div>
  )
}