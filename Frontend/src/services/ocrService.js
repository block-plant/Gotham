// Mock OCR service. Another team member will replace scanFirDocument()
// with a real call to POST /ocr/scan-fir — the Register FIR page only
// ever calls this function, so the UI needs no changes when that happens.

function mockDelay(ms = 1800) {
  return new Promise((resolve) => setTimeout(resolve, ms))
}

// TODO: Replace mock response with backend/OCR API call -> POST /ocr/scan-fir
export async function scanFirDocument(file) {
  await mockDelay()

  // Mock extracted data — shaped to match the Register FIR form fields
  // so it can be applied directly onto the form state.
  return {
    policeStation: 'Kotwali PS',
    district: 'Gorakhpur',
    state: 'Uttar Pradesh',
    firNumber: `${Math.floor(100 + Math.random() * 800)}/2026`,
    complainantFullName: 'Extracted Complainant Name',
    complainantAddress: 'Extracted address from scanned document',
    complainantPhone: '9800000000',
    occurrencePlace: 'Extracted location of occurrence',
    dateOfOccurrence: new Date().toISOString().slice(0, 10),
    timeOfOccurrence: '18:00',
    natureOfOffence: 'Theft',
    crimeCategory: 'Theft',
    factsOfIncident:
      'Facts of the incident extracted from the scanned FIR document via OCR (mock data for demonstration).',
  }
}