import {
  NavLink,
} from 'react-router-dom'


const navigation = [
  {
    label: 'Overview',
    path: '/overview',
  },
  {
    label: 'Printers',
    path: '/printers',
  },
  {
    label: 'Alerts',
    path: '/alerts',
  },
  {
    label: 'History',
    path: '/history',
  },
  {
    label: 'Configuration',
    path: '/configuration',
  },
]


export default function Sidebar() {
  return (
    <aside className="sidebar">

      <div className="sidebar-brand">
        <div className="sidebar-brand-title">
          CARE-INSPECTOR
        </div>

        <div className="sidebar-brand-subtitle">
          Industrial Monitoring
        </div>
      </div>


      <nav className="sidebar-nav">

        {navigation.map((item) => (

          <NavLink
            key={item.path}
            to={item.path}
            className={({ isActive }) =>
              isActive
                ? 'sidebar-link active'
                : 'sidebar-link'
            }
          >
            {item.label}
          </NavLink>

        ))}

      </nav>


      <div className="sidebar-footer">
        MFG Monitoring Platform
      </div>

    </aside>
  )
}
