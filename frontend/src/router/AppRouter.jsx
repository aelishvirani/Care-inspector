import {
  BrowserRouter,
  Navigate,
  Route,
  Routes,
} from 'react-router-dom'

import {
  AuthProvider,
  useAuth,
} from '../auth/AuthContext'

import ProtectedRoute
  from '../components/auth/ProtectedRoute'

import AppLayout
  from '../components/layout/AppLayout'

import LoginPage
  from '../pages/LoginPage'

import CustomerDashboardPage
  from '../pages/CustomerDashboardPage'

import TechnicianDashboardPage
  from '../pages/TechnicianDashboardPage'

import AdminDashboardPage
  from '../pages/AdminDashboardPage'

import AdminUsersPage
  from '../pages/AdminUsersPage'

import AuditLogPage
  from '../pages/AuditLogPage'

import SystemHealthPage
  from '../pages/SystemHealthPage'

import OverviewPage
  from '../pages/OverviewPage'

import PrintersPage
  from '../pages/PrintersPage'

import PrinterDetailPage
  from '../pages/PrinterDetailPage'

import AlertsPage
  from '../pages/AlertsPage'

import HistoryPage
  from '../pages/HistoryPage'

import ConfigurationPage
  from '../pages/ConfigurationPage'

import UnassignedDevicesPage
  from '../pages/UnassignedDevicesPage'

import CustomersPage
  from '../pages/CustomersPage'

import CustomerDetailPage
  from '../pages/CustomerDetailPage'


function HomeRedirect() {
  const {
    user,
    loading,
  } = useAuth()

  if (loading) {
    return (
      <div className="loading-panel">
        Loading...
      </div>
    )
  }

  if (!user) {
    return (
      <Navigate
        to="/login"
        replace
      />
    )
  }

  if (user.role === 'ADMIN') {
    return (
      <Navigate
        to="/admin"
        replace
      />
    )
  }

  if (user.role === 'TECHNICIAN') {
    return (
      <Navigate
        to="/technik"
        replace
      />
    )
  }

  return (
    <Navigate
      to="/customer"
      replace
    />
  )
}


function RouterContent() {
  return (
    <Routes>

      <Route
        path="/login"
        element={
          <LoginPage />
        }
      />

      <Route
        path="/"
        element={
          <HomeRedirect />
        }
      />


      <Route
        element={
          <ProtectedRoute>
            <AppLayout />
          </ProtectedRoute>
        }
      >

        <Route
          path="/customer"
          element={
            <ProtectedRoute
              roles={[
                'CUSTOMER',
              ]}
            >
              <CustomerDashboardPage />
            </ProtectedRoute>
          }
        />


        <Route
          path="/technik"
          element={
            <ProtectedRoute
              roles={[
                'TECHNICIAN',
              ]}
            >
              <TechnicianDashboardPage />
            </ProtectedRoute>
          }
        />


        <Route
          path="/admin"
          element={
            <ProtectedRoute
              roles={[
                'ADMIN',
              ]}
            >
              <AdminDashboardPage />
            </ProtectedRoute>
          }
        />


        <Route
          path="/admin/users"
          element={
            <ProtectedRoute
              roles={[
                'ADMIN',
              ]}
            >
              <AdminUsersPage />
            </ProtectedRoute>
          }
        />


        <Route
          path="/admin/audit-log"
          element={
            <ProtectedRoute
              roles={[
                'ADMIN',
              ]}
            >
              <AuditLogPage />
            </ProtectedRoute>
          }
        />


        <Route
          path="/admin/system-health"
          element={
            <ProtectedRoute
              roles={[
                'ADMIN',
              ]}
            >
              <SystemHealthPage />
            </ProtectedRoute>
          }
        />


        <Route
          path="/overview"
          element={
            <ProtectedRoute
              roles={[
                'TECHNICIAN',
                'ADMIN',
              ]}
            >
              <OverviewPage />
            </ProtectedRoute>
          }
        />


        <Route
          path="/printers"
          element={
            <ProtectedRoute
              roles={[
                'CUSTOMER',
                'TECHNICIAN',
                'ADMIN',
              ]}
            >
              <PrintersPage />
            </ProtectedRoute>
          }
        />


        <Route
          path="/printers/:deviceId"
          element={
            <ProtectedRoute
              roles={[
                'CUSTOMER',
                'TECHNICIAN',
                'ADMIN',
              ]}
            >
              <PrinterDetailPage />
            </ProtectedRoute>
          }
        />


        <Route
          path="/alerts"
          element={
            <ProtectedRoute
              roles={[
                'CUSTOMER',
                'TECHNICIAN',
                'ADMIN',
              ]}
            >
              <AlertsPage />
            </ProtectedRoute>
          }
        />


        <Route
          path="/history"
          element={
            <ProtectedRoute
              roles={[
                'CUSTOMER',
                'TECHNICIAN',
                'ADMIN',
              ]}
            >
              <HistoryPage />
            </ProtectedRoute>
          }
        />


        <Route
          path="/customers"
          element={
            <ProtectedRoute
              roles={[
                'TECHNICIAN',
                'ADMIN',
              ]}
            >
              <CustomersPage />
            </ProtectedRoute>
          }
        />


        <Route
          path="/customers/:customerId"
          element={
            <ProtectedRoute
              roles={[
                'TECHNICIAN',
                'ADMIN',
              ]}
            >
              <CustomerDetailPage />
            </ProtectedRoute>
          }
        />


        <Route
          path="/unassigned"
          element={
            <ProtectedRoute
              roles={[
                'TECHNICIAN',
                'ADMIN',
              ]}
            >
              <UnassignedDevicesPage />
            </ProtectedRoute>
          }
        />


        <Route
          path="/configuration"
          element={
            <ProtectedRoute
              roles={[
                'TECHNICIAN',
                'ADMIN',
              ]}
            >
              <ConfigurationPage />
            </ProtectedRoute>
          }
        />

      </Route>


      <Route
        path="*"
        element={
          <HomeRedirect />
        }
      />

    </Routes>
  )
}


export default function AppRouter() {
  return (
    <BrowserRouter>

      <AuthProvider>
        <RouterContent />
      </AuthProvider>

    </BrowserRouter>
  )
}
