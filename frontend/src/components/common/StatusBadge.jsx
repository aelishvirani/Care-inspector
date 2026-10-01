export default function StatusBadge({
  online,
}) {
  return (
    <span
      className={
        online
          ? 'status-badge online'
          : 'status-badge offline'
      }
    >
      <span className="status-dot" />

      {online ? 'Online' : 'Offline'}
    </span>
  )
}
