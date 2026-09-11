type Props = {
  status: 'ok' | 'unreachable' | 'checking'
}

const STYLES: Record<Props['status'], string> = {
  ok: 'bg-emerald-100 text-emerald-800',
  unreachable: 'bg-red-100 text-red-800',
  checking: 'bg-slate-100 text-slate-600',
}

const LABELS: Record<Props['status'], string> = {
  ok: 'Backend reachable',
  unreachable: 'Backend unreachable',
  checking: 'Checking…',
}

export function StatusBadge({ status }: Props) {
  return (
    <span className={`inline-flex items-center rounded-full px-3 py-1 text-sm font-medium ${STYLES[status]}`}>
      {LABELS[status]}
    </span>
  )
}
