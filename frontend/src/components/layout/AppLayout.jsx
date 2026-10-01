import {
  Outlet,
} from 'react-router-dom'

import Sidebar from './Sidebar'


export default function AppLayout() {
  return (
    <div className="app-shell">

      <Sidebar />

      <div className="app-content">

        <header className="app-topbar">

          <div>
            <strong>
              Care-Inspector
            </strong>

            <span>
              Printer Monitoring System
            </span>
          </div>

          <div className="app-environment">
            Local Development
          </div>

        </header>

        <main className="app-main">
          <Outlet />
        </main>

      </div>

    </div>
  )
}
