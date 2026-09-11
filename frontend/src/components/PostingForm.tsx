import { useState } from 'react'
import type { FormEvent } from 'react'
import { ApiError } from '../api/client'
import type { EmploymentType, JobPostingInput } from '../types'

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
    <form onSubmit={handleSubmit} className="space-y-5">
      {formError && (
        <div className="rounded-md bg-red-50 px-4 py-3 text-sm text-red-800">{formError}</div>
      )}

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <Field label="Company name" error={fieldError('company_name')}>
          <input
            required
            className="input"
            value={values.company_name}
            onChange={(e) => update('company_name', e.target.value)}
          />
        </Field>
        <Field label="Job title" error={fieldError('title')}>
          <input
            required
            className="input"
            value={values.title}
            onChange={(e) => update('title', e.target.value)}
          />
        </Field>
      </div>

      <Field label="Description" error={fieldError('description')}>
        <textarea
          required
          rows={6}
          className="input"
          value={values.description}
          onChange={(e) => update('description', e.target.value)}
        />
      </Field>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <Field label="Location" error={fieldError('location')}>
          <input
            className="input"
            value={values.location}
            onChange={(e) => update('location', e.target.value)}
          />
        </Field>
        <Field label="Employment type" error={fieldError('employment_type')}>
          <select
            className="input"
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

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
        <Field label="Minimum salary" error={fieldError('salary_min')}>
          <input
            type="number"
            className="input"
            value={values.salary_min ?? ''}
            onChange={(e) => update('salary_min', e.target.value ? Number(e.target.value) : null)}
          />
        </Field>
        <Field label="Maximum salary" error={fieldError('salary_max')}>
          <input
            type="number"
            className="input"
            value={values.salary_max ?? ''}
            onChange={(e) => update('salary_max', e.target.value ? Number(e.target.value) : null)}
          />
        </Field>
        <Field label="Currency" error={fieldError('currency')}>
          <input
            className="input"
            value={values.currency}
            onChange={(e) => update('currency', e.target.value)}
          />
        </Field>
      </div>

      <label className="flex items-center gap-2 text-sm text-slate-700">
        <input
          type="checkbox"
          checked={values.salary_disclosed}
          onChange={(e) => update('salary_disclosed', e.target.checked)}
        />
        I'm disclosing compensation for this role
      </label>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <Field label="Apply URL" error={fieldError('apply_url')}>
          <input
            type="url"
            className="input"
            value={values.apply_url}
            onChange={(e) => update('apply_url', e.target.value)}
          />
        </Field>
        <Field label="Contact email" error={fieldError('contact_email')}>
          <input
            type="email"
            className="input"
            value={values.contact_email}
            onChange={(e) => update('contact_email', e.target.value)}
          />
        </Field>
      </div>

      <button
        type="submit"
        disabled={submitting}
        className="rounded-md bg-slate-900 px-4 py-2 text-sm font-medium text-white hover:bg-slate-700 disabled:opacity-50"
      >
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
    <label className="block text-sm">
      <span className="mb-1 block font-medium text-slate-700">{label}</span>
      {children}
      {error && <span className="mt-1 block text-xs text-red-600">{error}</span>}
    </label>
  )
}
