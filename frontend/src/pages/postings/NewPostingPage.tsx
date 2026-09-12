import { useNavigate } from 'react-router-dom'
import { postings } from '../../api/client'
import { PostingForm } from '../../components/PostingForm'
import type { JobPostingInput } from '../../types'
import '../../styles/modulus.css'

export function NewPostingPage() {
  const navigate = useNavigate()

  async function handleSubmit(values: JobPostingInput) {
    const created = await postings.create(values)
    navigate(`/postings/${created.id}`)
  }

  return (
    <div>
      <div style={{ marginBottom: 24 }}>
        <h1 style={{ fontSize: '1.5rem', fontWeight: 700 }}>Submit a job posting</h1>
        <p className="m-page-sub">
          Your posting is analyzed automatically as soon as you submit it. Most postings are
          approved or rejected within seconds; anything ambiguous goes to a human moderator.
        </p>
      </div>
      <PostingForm onSubmit={handleSubmit} submitLabel="Submit for review" />
    </div>
  )
}
