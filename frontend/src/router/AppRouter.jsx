import {
  BrowserRouter,
  Navigate,
  Route,
  Routes,
} from 'react-router-dom'

import PrinterDetailPage
  from '../pages/PrinterDetailPage'

import AppLayout from '../components/layout/AppLayout'
import OverviewPage from '../pages/OverviewPage'
import PrintersPage from '../pages/PrintersPage'
import AlertsPage from '../pages/AlertsPage'
import HistoryPage from '../pages/HistoryPage'
import ConfigurationPage from '../pages/ConfigurationPage'


export default function AppRouter() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<AppLayout />}>
          <Route
            path="/"
            element={<Navigate to="/overview" replace />}
          />

          <Route
            path="/overview"
            element={<OverviewPage />}
          />

          <Route
            path="/printers"
            element={<PrintersPage />}
          />

          <Route
            path="/printers/:deviceId"
            element={<PrinterDetailPage />}
          />

          <Route
            path="/alerts"
            element={<AlertsPage />}
          />

          <Route
            path="/history"
            element={<HistoryPage />}
          />

          <Route
            path="/configuration"
            element={<ConfigurationPage />}
          />
        </Route>
      </Routes>
    </BrowserRouter>
  )
}
