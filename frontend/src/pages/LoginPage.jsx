import {
  useState,
} from 'react'

import {
  Navigate,
  useNavigate,
} from 'react-router-dom'

import {
  useAuth,
} from '../auth/AuthContext'

import MfgLogo from '../components/branding/MfgLogo'

import '../styles/login.css'


function roleHome(user) {
  if (user?.role === 'ADMIN') {
    return '/admin'
  }

  if (user?.role === 'TECHNICIAN') {
    return '/technik'
  }

  return '/customer'
}


export default function LoginPage() {
  const {
    user,
    login,
  } = useAuth()

  const navigate =
    useNavigate()

  const [
    email,
    setEmail,
  ] = useState('')

  const [
    password,
    setPassword,
  ] = useState('')

  const [
    error,
    setError,
  ] = useState('')

  const [
    loading,
    setLoading,
  ] = useState(false)


  if (user) {
    return (
      <Navigate
        to={roleHome(user)}
        replace
      />
    )
  }


  async function handleSubmit(
    event
  ) {
    event.preventDefault()

    setLoading(true)
    setError('')

    try {
      const loggedInUser =
        await login(
          email.trim(),
          password
        )

      navigate(
        roleHome(
          loggedInUser
        ),
        {
          replace: true,
        }
      )

    } catch (err) {
      setError(
        err.message
        || 'Login failed'
      )

    } finally {
      setLoading(false)
    }
  }


  return (
    <div className="login-page">

      <div className="login-shell">

        <section className="login-brand-panel">

          <div className="login-company-logo-wrap">

            <MfgLogo
              className="login-company-logo"
            />

          </div>


          <div className="login-product-copy">

            <span className="login-eyebrow">
              Industrial Monitoring Platform
            </span>

            <h1>
              Care-Inspector
            </h1>

            <p>
              Central monitoring for
              industrial printers,
              alerts and service
              operations.
            </p>

          </div>


          <div className="login-brand-footer">
            MFG Technik &amp; Service
          </div>

        </section>


        <section className="login-form-panel">

          <div className="login-form-content">

            <div className="login-mobile-logo">
              <MfgLogo
                className="login-company-logo"
              />
            </div>


            <div className="login-heading">

              <span>
                CARE-INSPECTOR
              </span>

              <h2>
                Welcome back
              </h2>

              <p>
                Sign in to access your
                monitoring dashboard.
              </p>

            </div>


            {error && (
              <div className="login-error">
                <strong>
                  Sign in failed
                </strong>

                <span>
                  {error}
                </span>
              </div>
            )}


            <form
              className="login-form"
              onSubmit={handleSubmit}
            >

              <label
                className="login-field"
              >
                <span>
                  Email address
                </span>

                <input
                  type="email"
                  value={email}
                  required
                  autoFocus
                  autoComplete="username"
                  placeholder="name@company.com"
                  onChange={
                    event =>
                      setEmail(
                        event.target.value
                      )
                  }
                />
              </label>


              <label
                className="login-field"
              >
                <span>
                  Password
                </span>

                <input
                  type="password"
                  value={password}
                  required
                  autoComplete="current-password"
                  placeholder="Enter your password"
                  onChange={
                    event =>
                      setPassword(
                        event.target.value
                      )
                  }
                />
              </label>


              <button
                className="login-submit"
                type="submit"
                disabled={loading}
              >
                {
                  loading
                    ? 'Signing in...'
                    : 'Sign in'
                }
              </button>

            </form>


            <div className="login-security-note">

              <span className="login-security-dot" />

              Authorized access only.
              Activities may be recorded
              in the system audit log.

            </div>

          </div>


          <div className="login-version">
            Care-Inspector
            {' · '}
            MFG Technik &amp; Service
          </div>

        </section>

      </div>

    </div>
  )
}
