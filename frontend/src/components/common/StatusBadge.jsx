import {
  printerStatus,
} from '../../utils/printerStatus'


export default function StatusBadge({
  printer,
  online,
  status,
}) {
  const effectivePrinter =
    printer
    || {
      online,
      status,
    }

  const info =
    printerStatus(
      effectivePrinter
    )

  return (
    <span
      className={
        `fleet-status ${info.className}`
      }
    >
      {info.label}
    </span>
  )
}
