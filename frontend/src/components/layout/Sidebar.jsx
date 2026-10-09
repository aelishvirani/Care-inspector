import {
  NavLink,
} from 'react-router-dom'

import {
  useAuth,
} from '../../auth/AuthContext'

import MfgLogo from '../branding/MfgLogo'


const adminNavigation = [
  { label: 'Admin Dashboard', path: '/admin' },
  { label: 'Users', path: '/admin/users' },
  { label: 'Customers', path: '/customers' },
  { label: 'All Printers', path: '/printers' },
  { label: 'Unassigned Devices', path: '/unassigned' },
  { label: 'Alerts', path: '/alerts' },
  { label: 'History', path: '/history' },
  { label: 'Audit Log', path: '/admin/audit-log' },
  { label: 'System Health', path: '/admin/system-health' },
  { label: 'Configuration', path: '/configuration' },
]


const technicianNavigation = [
  { label: 'Technik Dashboard', path: '/technik' },
  { label: 'Overview', path: '/overview' },
  { label: 'Customers', path: '/customers' },
  { label: 'All Printers', path: '/printers' },
  { label: 'Unassigned Devices', path: '/unassigned' },
  { label: 'Alerts', path: '/alerts' },
  { label: 'History', path: '/history' },
  { label: 'Configuration', path: '/configuration' },
]


const customerNavigation = [
  { label: 'Dashboard', path: '/customer' },
  { label: 'My Printers', path: '/printers' },
  { label: 'Alerts', path: '/alerts' },
  { label: 'History', path: '/history' },
]


export default function Sidebar() {
  const {
    user,
  } = useAuth()

  let navigation =
    customerNavigation

  if (user?.role === 'ADMIN') {
    navigation =
      adminNavigation
  } else if (
    user?.role === 'TECHNICIAN'
  ) {
    navigation =
      technicianNavigation
  }


  return (
    <aside className="sidebar">

      <div className="sidebar-brand">

        <div className="sidebar-company-logo-wrap">
          <MfgLogo
            className="sidebar-company-logo"
          />
        </div>

        <div className="sidebar-product-brand">

          <div className="sidebar-brand-title">
            CARE-INSPECTOR
          </div>

          <div className="sidebar-brand-subtitle">
            Industrial Monitoring
          </div>

        </div>

      </div>


      <nav className="sidebar-nav">

        {
          navigation.map(
            item => (
              <NavLink
                key={item.path}
                to={item.path}
                className={
                  ({ isActive }) =>
                    isActive
                      ? 'sidebar-link active'
                      : 'sidebar-link'
                }
              >
                {item.label}
              </NavLink>
            )
          )
        }

      </nav>


      <div className="sidebar-footer">

        <span className="sidebar-footer-company">
          MFG Technik &amp; Service
        </span>

        <span>
          {
            user?.role === 'ADMIN'
              ? 'System Administration'
              : user?.role === 'TECHNICIAN'
                ? 'Technik / Service'
                : 'Customer Portal'
          }
        </span>

      </div>

    </aside>
  )
}
