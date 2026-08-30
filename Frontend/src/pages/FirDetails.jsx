import { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { ArrowLeft, FileText } from 'lucide-react'
import AuthenticatedLayout from '../components/layout/AuthenticatedLayout.jsx'
import StatusBadge from '../components/common/StatusBadge.jsx'
import LoadingSpinner from '../components/common/LoadingSpinner.jsx'
import * as firService from '../services/firService.js'

export default function FirDetails() {
  const { id } = useParams()
  const navigate = useNavigate()
  const [fir, setFir] = useState(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    setIsLoading(true)
    firService
      .getFirById(id)
      .then(setFir)
      .catch(() => setError('FIR record not found.'))
      .finally(() => setIsLoading(false))
  }, [id])

  return (
    <AuthenticatedLayout title="FIR Details">
      <button
        onClick={() => navigate('/firs')}
        className="mb-4 flex items-center gap-1 text-sm text-primary hover:underline"
      >
        <ArrowLeft size={14} /> Back to FIR List
      </button>

      {isLoading && <LoadingSpinner label="Loading FIR..." />}
      {error && <p className="text-sm text-danger">{error}</p>}

      {fir && (
        <div className="mx-auto max-w-4xl divide-y divide-border rounded-md border border-border bg-white">
          <div className="flex flex-wrap items-center justify-between gap-2 px-6 py-4">
            <div>
              <h1 className="text-lg font-bold text-navy">{fir.id}</h1>
              <p className="text-sm text-text-secondary">FIR Number: {fir.firNumber}</p>
            </div>
            <StatusBadge status={fir.status} />
          </div>

          <Block title="Police Station Details">
            <Row label="Police Station" value={fir.policeStation?.name} />
            <Row label="District" value={fir.policeStation?.district} />
            <Row label="State" value={fir.policeStation?.state} />
            <Row label="Registration Date" value={fir.registrationDate} />
            <Row label="Registration Time" value={fir.registrationTime} />
          </Block>

          <Block title="Complainant Details">
            <Row label="Full Name" value={fir.complainant?.fullName} />
            <Row label="Father's / Husband's Name" value={fir.complainant?.guardianName} />
            <Row label="Address" value={fir.complainant?.address} />
            <Row label="Phone" value={fir.complainant?.phone} />
            <Row label="Email" value={fir.complainant?.email} />
          </Block>

          <Block title="Place of Occurrence">
            <Row label="Place" value={fir.occurrence?.place} />
            <Row label="Address" value={fir.occurrence?.address} />
            <Row label="District" value={fir.occurrence?.district} />
            <Row label="State" value={fir.occurrence?.state} />
            <Row label="Distance from PS" value={fir.occurrence?.distanceFromPS} />
            <Row label="Direction from PS" value={fir.occurrence?.directionFromPS} />
          </Block>

          <Block title="Date and Time of Occurrence">
            <Row label="Date" value={fir.dateHour?.dateOfOccurrence} />
            <Row label="Time" value={fir.dateHour?.timeOfOccurrence} />
            <Row label="Approximate" value={fir.dateHour?.approxTime ? 'Yes' : 'No'} />
          </Block>

          <Block title="Offence Details">
            <Row label="Nature of Offence" value={fir.offence?.natureOfOffence} />
            <Row label="Crime Category" value={fir.offence?.crimeCategory} />
            <Row label="Legal Section" value={fir.offence?.legalSection} />
            <Row label="Summary" value={fir.offence?.briefSummary} />
          </Block>

          {fir.propertyInvolved && fir.properties?.length > 0 && (
            <Block title="Property Details">
              {fir.properties.map((p, i) => (
                <div key={i} className="mb-2 rounded-md bg-bg p-3 text-sm last:mb-0">
                  <Row label="Type" value={p.type} />
                  <Row label="Description" value={p.description} />
                  <Row label="Estimated Value" value={p.value} />
                  <Row label="Serial Number" value={p.serialNumber} />
                </div>
              ))}
            </Block>
          )}

          {fir.accused?.length > 0 && (
            <Block title="Accused Details">
              {fir.accused.map((a, i) => (
                <div key={i} className="mb-2 rounded-md bg-bg p-3 text-sm last:mb-0">
                  {a.type === 'known' ? (
                    <>
                      <Row label="Name" value={a.fullName} />
                      <Row label="Alias" value={a.alias} />
                      <Row label="Criminal ID" value={a.criminalId} />
                      <Row label="Address" value={a.address} />
                    </>
                  ) : (
                    <>
                      <Row label="Description" value={a.physicalDescription} />
                      <Row label="Estimated Age" value={a.estimatedAge} />
                      <Row label="Identifying Marks" value={a.identifyingMarks} />
                    </>
                  )}
                </div>
              ))}
            </Block>
          )}

          {fir.witnesses?.length > 0 && (
            <Block title="Witness Details">
              {fir.witnesses.map((w, i) => (
                <div key={i} className="mb-2 rounded-md bg-bg p-3 text-sm last:mb-0">
                  <Row label="Name" value={w.fullName} />
                  <Row label="Phone" value={w.phone} />
                  <Row label="Statement" value={w.statementSummary} />
                </div>
              ))}
            </Block>
          )}

          <Block title="Complaint / Facts of Incident">
            <p className="text-sm text-text-primary">{fir.factsOfIncident}</p>
          </Block>

          <Block title="Uploaded Document">
            {fir.uploadedDocument ? (
              <div className="flex items-center gap-2 text-sm text-text-primary">
                <FileText size={16} className="text-primary" />
                {fir.uploadedDocument.name}
              </div>
            ) : (
              <p className="text-sm text-text-secondary">No document uploaded.</p>
            )}
          </Block>
        </div>
      )}
    </AuthenticatedLayout>
  )
}

function Block({ title, children }) {
  return (
    <div className="px-6 py-4">
      <h3 className="mb-2 text-sm font-semibold text-navy">{title.toUpperCase()}</h3>
      <div className="grid grid-cols-1 gap-x-6 gap-y-1 sm:grid-cols-2">{children}</div>
    </div>
  )
}

function Row({ label, value }) {
  if (!value) return null
  return (
    <div className="flex justify-between border-b border-border/50 py-1 text-sm sm:justify-start sm:gap-2">
      <span className="text-text-secondary">{label}:</span>
      <span className="text-text-primary">{value}</span>
    </div>
  )
}