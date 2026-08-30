import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useForm, useFieldArray, Controller } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { Plus, Trash2 } from 'lucide-react'
import AuthenticatedLayout from '../components/layout/AuthenticatedLayout.jsx'
import Input from '../components/common/Input.jsx'
import Button from '../components/common/Button.jsx'
import FileUpload from '../components/fir/FileUpload.jsx'
import OcrScanPanel from '../components/fir/OcrScanPanel.jsx'
import { crimeCategories } from '../data/firData.js'
import * as firService from '../services/firService.js'

const schema = z.object({
  policeStation: z.string().min(1, 'Required'),
  district: z.string().min(1, 'Required'),
  state: z.string().min(1, 'Required'),
  firNumber: z.string().min(1, 'Required'),
  registrationDate: z.string().min(1, 'Required'),
  registrationTime: z.string().min(1, 'Required'),

  complainantFullName: z.string().min(1, 'Required'),
  guardianName: z.string().optional(),
  complainantAddress: z.string().min(1, 'Required'),
  complainantPhone: z.string().min(10, 'Enter a valid phone number'),
  complainantEmail: z.string().email('Invalid email').optional().or(z.literal('')),
  age: z.string().optional(),
  gender: z.string().optional(),

  occurrencePlace: z.string().min(1, 'Required'),
  occurrenceAddress: z.string().optional(),
  occurrenceDistrict: z.string().optional(),
  occurrenceState: z.string().optional(),
  distanceFromPS: z.string().optional(),
  directionFromPS: z.string().optional(),

  dateOfOccurrence: z.string().min(1, 'Required'),
  timeOfOccurrence: z.string().min(1, 'Required'),
  approxTime: z.boolean().optional(),

  natureOfOffence: z.string().min(1, 'Required'),
  crimeCategory: z.string().min(1, 'Required'),
  legalSection: z.string().optional(),
  briefSummary: z.string().optional(),

  propertyInvolved: z.boolean().optional(),
  properties: z.array(
    z.object({
      type: z.string().optional(),
      description: z.string().optional(),
      value: z.string().optional(),
      serialNumber: z.string().optional(),
    }),
  ),

  accused: z.array(
    z.object({
      type: z.enum(['known', 'unknown']),
      fullName: z.string().optional(),
      alias: z.string().optional(),
      age: z.string().optional(),
      gender: z.string().optional(),
      address: z.string().optional(),
      phone: z.string().optional(),
      criminalId: z.string().optional(),
      physicalDescription: z.string().optional(),
      estimatedAge: z.string().optional(),
      identifyingMarks: z.string().optional(),
      otherDetails: z.string().optional(),
    }),
  ),

  witnesses: z.array(
    z.object({
      fullName: z.string().optional(),
      address: z.string().optional(),
      phone: z.string().optional(),
      statementSummary: z.string().optional(),
    }),
  ),

  factsOfIncident: z.string().min(20, 'Please provide at least 20 characters'),
})

const emptyProperty = { type: '', description: '', value: '', serialNumber: '' }
const emptyKnownAccused = { type: 'known', fullName: '', alias: '', age: '', gender: '', address: '', phone: '', criminalId: '' }
const emptyWitness = { fullName: '', address: '', phone: '', statementSummary: '' }

export default function RegisterFir() {
  const navigate = useNavigate()
  const [uploadedFile, setUploadedFile] = useState(null)
  const [submitError, setSubmitError] = useState('')

  const {
    register,
    control,
    handleSubmit,
    setValue,
    watch,
    formState: { errors, isSubmitting },
  } = useForm({
    resolver: zodResolver(schema),
    defaultValues: {
      registrationDate: new Date().toISOString().slice(0, 10),
      registrationTime: new Date().toTimeString().slice(0, 5),
      propertyInvolved: false,
      properties: [],
      accused: [{ ...emptyKnownAccused }],
      witnesses: [],
      factsOfIncident: '',
    },
  })

  const propertyInvolved = watch('propertyInvolved')
  const factsText = watch('factsOfIncident')

  const propertiesArray = useFieldArray({ control, name: 'properties' })
  const accusedArray = useFieldArray({ control, name: 'accused' })
  const witnessesArray = useFieldArray({ control, name: 'witnesses' })

  function applyExtracted(extracted) {
    setValue('policeStation', extracted.policeStation)
    setValue('firNumber', extracted.firNumber)
    setValue('complainantFullName', extracted.complainantFullName)
    setValue('complainantAddress', extracted.complainantAddress)
    setValue('complainantPhone', extracted.complainantPhone)
    setValue('occurrencePlace', extracted.occurrencePlace)
    setValue('dateOfOccurrence', extracted.dateOfOccurrence)
    setValue('timeOfOccurrence', extracted.timeOfOccurrence)
    setValue('natureOfOffence', extracted.natureOfOffence)
    setValue('crimeCategory', extracted.crimeCategory)
    setValue('factsOfIncident', extracted.factsOfIncident)
  }

  async function onSubmit(data) {
    setSubmitError('')
    try {
      const payload = {
        firNumber: data.firNumber,
        registrationDate: data.registrationDate,
        registrationTime: data.registrationTime,
        policeStation: { name: data.policeStation, district: data.district, state: data.state },
        complainant: {
          fullName: data.complainantFullName,
          guardianName: data.guardianName,
          address: data.complainantAddress,
          phone: data.complainantPhone,
          email: data.complainantEmail,
          age: data.age,
          gender: data.gender,
        },
        occurrence: {
          place: data.occurrencePlace,
          address: data.occurrenceAddress,
          district: data.occurrenceDistrict,
          state: data.occurrenceState,
          distanceFromPS: data.distanceFromPS,
          directionFromPS: data.directionFromPS,
        },
        dateHour: {
          dateOfOccurrence: data.dateOfOccurrence,
          timeOfOccurrence: data.timeOfOccurrence,
          approxTime: !!data.approxTime,
        },
        offence: {
          natureOfOffence: data.natureOfOffence,
          crimeCategory: data.crimeCategory,
          legalSection: data.legalSection,
          briefSummary: data.briefSummary,
        },
        propertyInvolved: !!data.propertyInvolved,
        properties: data.propertyInvolved ? data.properties : [],
        accused: data.accused,
        witnesses: data.witnesses,
        factsOfIncident: data.factsOfIncident,
        uploadedDocument: uploadedFile
          ? { name: uploadedFile.name, type: uploadedFile.type, size: uploadedFile.size }
          : null,
      }

      const created = await firService.createFir(payload)
      navigate(`/firs/${created.id}`)
    } catch (err) {
      setSubmitError('Could not save the FIR. Please try again.')
    }
  }

  return (
    <AuthenticatedLayout title="Register FIR">
      <div className="mx-auto max-w-4xl rounded-md border border-border bg-white">
        {/* HEADER */}
        <div className="border-b border-border px-6 py-5 text-center">
          <h1 className="text-lg font-bold text-navy">GOTHAM</h1>
          <p className="text-sm font-semibold text-text-primary">FIRST INFORMATION REPORT</p>
          <p className="text-xs text-text-secondary">FIR Registration Form</p>
        </div>

        <form onSubmit={handleSubmit(onSubmit)} className="divide-y divide-border">
          {/* SECTION 1 */}
          <Section number="1" title="Police Station Details">
            <Grid>
              <Input label="Police Station" error={errors.policeStation?.message} {...register('policeStation')} />
              <Input label="District" error={errors.district?.message} {...register('district')} />
              <Input label="State" error={errors.state?.message} {...register('state')} />
              <Input label="FIR Number" error={errors.firNumber?.message} {...register('firNumber')} />
              <Input label="FIR Registration Date" type="date" error={errors.registrationDate?.message} {...register('registrationDate')} />
              <Input label="FIR Registration Time" type="time" error={errors.registrationTime?.message} {...register('registrationTime')} />
            </Grid>
          </Section>

          {/* SECTION 2 */}
          <Section number="2" title="Personal Details of Complainant / Informant">
            <Grid>
              <Input label="Full Name" error={errors.complainantFullName?.message} {...register('complainantFullName')} />
              <Input label="Father's / Husband's Name" {...register('guardianName')} />
              <Input label="Address" error={errors.complainantAddress?.message} {...register('complainantAddress')} />
              <Input label="Phone Number" error={errors.complainantPhone?.message} {...register('complainantPhone')} />
              <Input label="Email Address" error={errors.complainantEmail?.message} {...register('complainantEmail')} />
              <Input label="Age (optional)" {...register('age')} />
              <Input label="Gender (optional)" {...register('gender')} />
            </Grid>
          </Section>

          {/* SECTION 3 */}
          <Section number="3" title="Place of Occurrence">
            <Grid>
              <Input label="Place / Location of Occurrence" error={errors.occurrencePlace?.message} {...register('occurrencePlace')} />
              <Input label="Complete Address" {...register('occurrenceAddress')} />
              <Input label="District" {...register('occurrenceDistrict')} />
              <Input label="State" {...register('occurrenceState')} />
              <Input label="Distance from Police Station" {...register('distanceFromPS')} />
              <Input label="Direction from Police Station" {...register('directionFromPS')} />
            </Grid>
          </Section>

          {/* SECTION 4 */}
          <Section number="4" title="Date and Hour of Occurrence">
            <Grid>
              <Input label="Date of Occurrence" type="date" error={errors.dateOfOccurrence?.message} {...register('dateOfOccurrence')} />
              <Input label="Time of Occurrence" type="time" error={errors.timeOfOccurrence?.message} {...register('timeOfOccurrence')} />
            </Grid>
            <label className="mt-2 flex items-center gap-2 text-sm text-text-secondary">
              <input type="checkbox" {...register('approxTime')} /> Approximate Time
            </label>
          </Section>

          {/* SECTION 5 */}
          <Section number="5" title="Offence Details">
            <Grid>
              <Input label="Nature of Offence" error={errors.natureOfOffence?.message} {...register('natureOfOffence')} />
              <div className="flex flex-col gap-1">
                <label className="text-sm font-medium text-text-primary">Crime Category</label>
                <select
                  className="rounded-md border border-border px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-primary/40"
                  {...register('crimeCategory')}
                >
                  <option value="">Select category</option>
                  {crimeCategories.map((c) => (
                    <option key={c} value={c}>{c}</option>
                  ))}
                </select>
                {errors.crimeCategory && (
                  <span className="text-xs text-danger">{errors.crimeCategory.message}</span>
                )}
              </div>
              <Input label="Applicable Legal Section" {...register('legalSection')} />
            </Grid>
            <div className="mt-3">
              <label className="text-sm font-medium text-text-primary">Brief Offence Summary</label>
              <textarea
                rows={2}
                className="mt-1 w-full rounded-md border border-border px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-primary/40"
                {...register('briefSummary')}
              />
            </div>
          </Section>

          {/* SECTION 6 */}
          <Section number="6" title="Particulars of Property">
            <label className="flex items-center gap-2 text-sm text-text-primary">
              <input type="checkbox" {...register('propertyInvolved')} />
              Property involved in this offence
            </label>

            {propertyInvolved && (
              <div className="mt-3 flex flex-col gap-3">
                {propertiesArray.fields.map((field, index) => (
                  <div key={field.id} className="rounded-md border border-border p-3">
                    <Grid>
                      <Input label="Property Type" {...register(`properties.${index}.type`)} />
                      <Input label="Description" {...register(`properties.${index}.description`)} />
                      <Input label="Estimated Value" {...register(`properties.${index}.value`)} />
                      <Input label="Identification / Serial Number" {...register(`properties.${index}.serialNumber`)} />
                    </Grid>
                    <button
                      type="button"
                      onClick={() => propertiesArray.remove(index)}
                      className="mt-2 flex items-center gap-1 text-xs text-danger"
                    >
                      <Trash2 size={14} /> Remove Property
                    </button>
                  </div>
                ))}
                <Button
                  type="button"
                  variant="secondary"
                  className="w-fit"
                  onClick={() => propertiesArray.append(emptyProperty)}
                >
                  <Plus size={16} /> Add Another Property
                </Button>
              </div>
            )}
          </Section>

          {/* SECTION 7 */}
          <Section number="7" title="Description of Accused">
            <div className="flex flex-col gap-3">
              {accusedArray.fields.map((field, index) => {
                const type = watch(`accused.${index}.type`)
                return (
                  <div key={field.id} className="rounded-md border border-border p-3">
                    <div className="mb-2 flex items-center gap-4 text-sm">
                      <label className="flex items-center gap-1">
                        <input
                          type="radio"
                          value="known"
                          {...register(`accused.${index}.type`)}
                        />
                        Known Accused
                      </label>
                      <label className="flex items-center gap-1">
                        <input
                          type="radio"
                          value="unknown"
                          {...register(`accused.${index}.type`)}
                        />
                        Unknown Accused
                      </label>
                    </div>

                    {type === 'known' ? (
                      <Grid>
                        <Input label="Full Name" {...register(`accused.${index}.fullName`)} />
                        <Input label="Alias" {...register(`accused.${index}.alias`)} />
                        <Input label="Age" {...register(`accused.${index}.age`)} />
                        <Input label="Gender" {...register(`accused.${index}.gender`)} />
                        <Input label="Address" {...register(`accused.${index}.address`)} />
                        <Input label="Phone Number" {...register(`accused.${index}.phone`)} />
                        <Input label="Criminal ID (if available)" {...register(`accused.${index}.criminalId`)} />
                      </Grid>
                    ) : (
                      <Grid>
                        <Input label="Physical Description" {...register(`accused.${index}.physicalDescription`)} />
                        <Input label="Estimated Age" {...register(`accused.${index}.estimatedAge`)} />
                        <Input label="Gender" {...register(`accused.${index}.gender`)} />
                        <Input label="Identifying Marks" {...register(`accused.${index}.identifyingMarks`)} />
                        <Input label="Other Details" {...register(`accused.${index}.otherDetails`)} />
                      </Grid>
                    )}

                    {accusedArray.fields.length > 1 && (
                      <button
                        type="button"
                        onClick={() => accusedArray.remove(index)}
                        className="mt-2 flex items-center gap-1 text-xs text-danger"
                      >
                        <Trash2 size={14} /> Remove Accused
                      </button>
                    )}
                  </div>
                )
              })}
              <Button
                type="button"
                variant="secondary"
                className="w-fit"
                onClick={() => accusedArray.append({ ...emptyKnownAccused })}
              >
                <Plus size={16} /> Add Another Accused
              </Button>
            </div>
          </Section>

          {/* SECTION 8 */}
          <Section number="8" title="Details of Witnesses">
            <div className="flex flex-col gap-3">
              {witnessesArray.fields.map((field, index) => (
                <div key={field.id} className="rounded-md border border-border p-3">
                  <Grid>
                    <Input label="Full Name" {...register(`witnesses.${index}.fullName`)} />
                    <Input label="Address" {...register(`witnesses.${index}.address`)} />
                    <Input label="Phone Number" {...register(`witnesses.${index}.phone`)} />
                  </Grid>
                  <div className="mt-2">
                    <label className="text-sm font-medium text-text-primary">Statement Summary</label>
                    <textarea
                      rows={2}
                      className="mt-1 w-full rounded-md border border-border px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-primary/40"
                      {...register(`witnesses.${index}.statementSummary`)}
                    />
                  </div>
                  <button
                    type="button"
                    onClick={() => witnessesArray.remove(index)}
                    className="mt-2 flex items-center gap-1 text-xs text-danger"
                  >
                    <Trash2 size={14} /> Remove Witness
                  </button>
                </div>
              ))}
              <Button
                type="button"
                variant="secondary"
                className="w-fit"
                onClick={() => witnessesArray.append(emptyWitness)}
              >
                <Plus size={16} /> Add Witness
              </Button>
            </div>
          </Section>

          {/* SECTION 9 */}
          <Section number="9" title="Complaint / Facts of Incident">
            <label className="text-sm font-medium text-text-primary">
              Briefly State the Facts Regarding the Incident
            </label>
            <p className="mb-1 text-xs text-text-secondary">
              Provide an accurate and chronological description of the incident.
            </p>
            <textarea
              rows={5}
              className="w-full rounded-md border border-border px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-primary/40"
              {...register('factsOfIncident')}
            />
            <div className="mt-1 flex items-center justify-between text-xs text-text-secondary">
              <span>{errors.factsOfIncident?.message}</span>
              <span>{(factsText || '').length} characters</span>
            </div>
          </Section>

          {/* SECTION 10 */}
          <Section number="10" title="FIR Document Upload">
            <FileUpload
              file={uploadedFile}
              onFileSelect={setUploadedFile}
              onFileRemove={() => setUploadedFile(null)}
            />
            <OcrScanPanel file={uploadedFile} onApply={applyExtracted} />
          </Section>

          {/* SUBMIT */}
          <div className="flex items-center justify-end gap-3 px-6 py-5">
            {submitError && <span className="text-sm text-danger">{submitError}</span>}
            <Button type="submit" isLoading={isSubmitting}>
              {isSubmitting ? 'Saving FIR...' : 'Save FIR'}
            </Button>
          </div>
        </form>
      </div>
    </AuthenticatedLayout>
  )
}

function Section({ number, title, children }) {
  return (
    <div className="px-6 py-5">
      <h3 className="mb-3 text-sm font-semibold text-navy">
        SECTION {number} — {title.toUpperCase()}
      </h3>
      {children}
    </div>
  )
}

function Grid({ children }) {
  return <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">{children}</div>
}