import {
  Navigate,
  useLocation,
} from 'react-router-dom'

import {
  useAuth,
} from '../../auth/AuthContext'


function homeForRole(
  role
) {
  if (role === 'ADMIN') {
    return '/admin'
  }

  if (role === 'TECHNICIAN') {
    return '/technik'
  }

  return '/customer'
}


export default function ProtectedRoute({
  children,
  roles,
}) {
  const {
    user,
    loading,
  } = useAuth()

  const location =
    useLocation()


  if (loading) {
    return (
      <div className="loading-panel">
        Loading Care-Inspector...
      </div>
    )
  }


  if (!user) {
    return (
      <Navigate
        to="/login"
        replace
        state={{
          from: location,
        }}
      />
    )
  }


  if (
    roles
    && !roles.includes(
      user.role
    )
  ) {
    return (
      <Navigate
        to={
          homeForRole(
            user.role
          )
        }
        replace
      />
    )
  }


  return children
}
