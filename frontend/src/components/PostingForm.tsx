import { useState } from 'react'
import type { FormEvent } from 'react'
import { ApiError } from '../api/client'
import type { EmploymentType, JobPostingInput } from '../types'
import '../styles/modulus.css'

const EMPLOYMENT_TYPES: { value: EmploymentType; label: string }[] = [
  { value: 'FULL_TIME', label: 'Full-time' },
  { value: 'PART_TIME', label: 'Part-time' },
  { value: 'CONTRACT', label: 'Contract' },
  { value: 'INTERNSHIP', label: 'Internship' },
  { value: 'TEMPORARY', label: 'Temporary' },
]

const EMPTY: JobPostingInput = {
  company_name: '',
  title: '',
  description: '',
  location: '',
  employment_type: 'FULL_TIME',
  salary_min: null,
  salary_max: null,
  currency: 'USD',
  salary_disclosed: false,
  apply_url: '',
  contact_email: '',
}

type FieldErrors = Record<string, string[]>

function isFieldErrors(body: unknown): body is FieldErrors {
  return typeof body === 'object' && body !== null && !('detail' in body)
}

export function PostingForm({
  initialValues,
  onSubmit,
  submitLabel,
}: {
  initialValues?: Partial<JobPostingInput>
  onSubmit: (values: JobPostingInput) => Promise<void>
  submitLabel: string
}) {
  const [values, setValues] = useState<JobPostingInput>({ ...EMPTY, ...initialValues })
  const [errors, setErrors] = useState<FieldErrors>({})
  const [submitting, setSubmitting] = useState(false)
  const [formError, setFormError] = useState<string | null>(null)

  function update<K extends keyof JobPostingInput>(key: K, value: JobPostingInput[K]) {
    setValues((prev) => ({ ...prev, [key]: value }))
  }

  async function handleSubmit(event: FormEvent) {
    event.preventDefault()
    setSubmitting(true)
    setErrors({})
    setFormError(null)
    try {
      await onSubmit(values)
    } catch (err) {
      if (err instanceof ApiError && isFieldErrors(err.body)) {
        setErrors(err.body)
      } else if (err instanceof Error) {
        setFormError(err.message)
      } else {
        setFormError('Something went wrong. Please try again.')
      }
    } finally {
      setSubmitting(false)
    }
  }

  function fieldError(name: string) {
    return errors[name]?.[0]
  }

  return (
    <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
      {formError && <div className="m-error-banner">{formError}</div>}

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
        <Field label="Company name" error={fieldError('company_name')}>
          <input required value={values.company_name} onChange={(e) => update('company_name', e.target.value)} />
        </Field>
        <Field label="Job title" error={fieldError('title')}>
          <input required value={values.title} onChange={(e) => update('title', e.target.value)} />
        </Field>
      </div>

      <Field label="Description" error={fieldError('description')}>
        <textarea
          required
          rows={6}
          value={values.description}
          onChange={(e) => update('description', e.target.value)}
        />
      </Field>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
        <Field label="Location" error={fieldError('location')}>
          <input value={values.location} onChange={(e) => update('location', e.target.value)} />
        </Field>
        <Field label="Employment type" error={fieldError('employment_type')}>
          <select
            value={values.employment_type}
            onChange={(e) => update('employment_type', e.target.value as EmploymentType)}
          >
            {EMPLOYMENT_TYPES.map((t) => (
              <option key={t.value} value={t.value}>
                {t.label}
              </option>
            ))}
          </select>
        </Field>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 16 }}>
        <Field label="Minimum salary" error={fieldError('salary_min')}>
          <input
            type="number"
            value={values.salary_min ?? ''}
            onChange={(e) => update('salary_min', e.target.value ? Number(e.target.value) : null)}
          />
        </Field>
        <Field label="Maximum salary" error={fieldError('salary_max')}>
          <input
            type="number"
            value={values.salary_max ?? ''}
            onChange={(e) => update('salary_max', e.target.value ? Number(e.target.value) : null)}
          />
        </Field>
        <Field label="Currency" error={fieldError('currency')}>
          <input value={values.currency} onChange={(e) => update('currency', e.target.value)} />
        </Field>
      </div>

      <label className="m-checkbox-field">
        <input
          type="checkbox"
          checked={values.salary_disclosed}
          onChange={(e) => update('salary_disclosed', e.target.checked)}
        />
        I'm disclosing compensation for this role
      </label>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
        <Field label="Apply URL" error={fieldError('apply_url')}>
          <input type="url" value={values.apply_url} onChange={(e) => update('apply_url', e.target.value)} />
        </Field>
        <Field label="Contact email" error={fieldError('contact_email')}>
          <input type="email" value={values.contact_email} onChange={(e) => update('contact_email', e.target.value)} />
        </Field>
      </div>

      <button type="submit" disabled={submitting} className="m-btn m-btn-solid" style={{ alignSelf: 'flex-start' }}>
        {submitting ? 'Submitting…' : submitLabel}
      </button>
    </form>
  )
}

function Field({
  label,
  error,
  children,
}: {
  label: string
  error?: string
  children: React.ReactNode
}) {
  return (
    <label className="m-field">
      <span className="m-field-label">{label}</span>
      {children}
      {error && <span className="m-field-error">{error}</span>}
    </label>
  )
}
