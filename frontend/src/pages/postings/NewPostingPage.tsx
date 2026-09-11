import { useNavigate } from 'react-router-dom'
import { postings } from '../../api/client'
import { PostingForm } from '../../components/PostingForm'
import type { JobPostingInput } from '../../types'

export function NewPostingPage() {
  const navigate = useNavigate()

  async function handleSubmit(values: JobPostingInput) {
    const created = await postings.create(values)
    navigate(`/postings/${created.id}`)
  }

  return (
    <div className="mx-auto max-w-2xl">
      <h1 className="mb-1 text-xl font-semibold text-slate-900">Submit a job posting</h1>
      <p className="mb-6 text-sm text-slate-500">
        Your posting is analyzed automatically as soon as you submit it. Most postings are
        approved or rejected within seconds; anything ambiguous goes to a human moderator.
      </p>
      <PostingForm onSubmit={handleSubmit} submitLabel="Submit for review" />
    </div>
  )
}
