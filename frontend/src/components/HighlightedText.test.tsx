import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import { HighlightedText } from './HighlightedText'

describe('HighlightedText', () => {
  it('renders plain text unchanged when there are no spans', () => {
    render(<HighlightedText text="Nothing wrong here." spans={[]} />)
    expect(screen.getByText('Nothing wrong here.')).toBeInTheDocument()
    expect(document.querySelectorAll('mark')).toHaveLength(0)
  })

  it('wraps exactly the matched span in a <mark>, leaving the rest as plain text', () => {
    const text = 'Please send a $50 registration fee to proceed.'
    render(<HighlightedText text={text} spans={[{ start: 14, end: 34, severity: 'CRITICAL' }]} />)

    const mark = document.querySelector('mark')
    expect(mark).toHaveTextContent('$50 registration fee')
    expect(mark).toHaveClass('bg-red-300')
    // The untouched prefix/suffix must still be present in the rendered text.
    expect(screen.getByText(/Please send a/)).toBeInTheDocument()
    expect(screen.getByText(/to proceed\./)).toBeInTheDocument()
  })

  it('drops zero-length and inverted spans instead of rendering an empty mark', () => {
    const text = 'Clean posting text.'
    render(
      <HighlightedText
        text={text}
        spans={[
          { start: 5, end: 5 },
          { start: 10, end: 8 },
        ]}
      />,
    )
    expect(document.querySelectorAll('mark')).toHaveLength(0)
    expect(screen.getByText(text)).toBeInTheDocument()
  })

  it('sorts out-of-order spans and clamps overlapping ranges instead of duplicating text', () => {
    // Second span starts before the first one ends, and spans are passed
    // out of start order — both are real inputs the evidence data can
    // produce (rule + model flags overlapping the same phrase).
    const text = 'commission-only downline recruitment scheme'
    render(
      <HighlightedText
        text={text}
        spans={[
          { start: 16, end: 38, severity: 'HIGH', id: 2 },
          { start: 0, end: 20, severity: 'MEDIUM', id: 1 },
        ]}
      />,
    )

    const marks = document.querySelectorAll('mark')
    expect(marks).toHaveLength(2)
    // Combined, the marks' text must reconstruct the original span coverage
    // with no character duplicated between them.
    expect(marks[0].textContent).toBe(text.slice(0, 20))
    expect(marks[1].textContent).toBe(text.slice(20, 38))
  })

  it('falls back to the MEDIUM color when severity is missing', () => {
    render(<HighlightedText text="abcdef" spans={[{ start: 1, end: 3 }]} />)
    expect(document.querySelector('mark')).toHaveClass('bg-amber-200')
  })

  it('gives the active span a ring and leaves the others unringed', () => {
    render(
      <HighlightedText
        text="abcdefghij"
        spans={[
          { start: 0, end: 2, id: 1 },
          { start: 5, end: 7, id: 2 },
        ]}
        activeId={2}
      />,
    )
    const marks = document.querySelectorAll('mark')
    expect(marks[0].id).toBe('evidence-1')
    expect(marks[0]).not.toHaveClass('ring-2')
    expect(marks[1].id).toBe('evidence-2')
    expect(marks[1]).toHaveClass('ring-2')
  })
})
