export default function Header({
  backendOnline,
}) {
  return (
    <header className="topbar">

      <div>
        <div className="brand">
          CARE-INSPECTOR
        </div>

        <div className="brand-subtitle">
          Industrial Printer Monitoring
        </div>
      </div>

      <div className="backend-status">
        Backend

        <span
          className={
            backendOnline
              ? 'connection-dot online'
              : 'connection-dot offline'
          }
        />
      </div>

    </header>
  )
}
