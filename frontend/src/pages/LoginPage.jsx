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


export default function LoginPage() {
  const {
    user,
    login,
  } = useAuth()

  const navigate =
    useNavigate()

  const [email, setEmail] =
    useState('')

  const [password, setPassword] =
    useState('')

  const [error, setError] =
    useState('')

  const [loading, setLoading] =
    useState(false)


  if (user) {
    return (
      <Navigate
        to={
          user.role === 'TECHNICIAN'
            ? '/technik'
            : '/customer'
        }
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
          email,
          password
        )

      if (
        loggedInUser.role
        === 'TECHNICIAN'
      ) {
        navigate(
          '/technik',
          {
            replace: true,
          }
        )

      } else {
        navigate(
          '/customer',
          {
            replace: true,
          }
        )
      }

    } catch (err) {
      console.error(err)

      setError(
        err.message
        || 'Login failed'
      )

    } finally {
      setLoading(false)
    }
  }


  return (
    <div
      style={{
        minHeight: '100vh',
        display: 'flex',
        alignItems: 'center',
        justifyContent:
          'center',
        background: '#f4f6f8',
        padding: '24px',
      }}
    >

      <section
        className="panel"
        style={{
          width: '100%',
          maxWidth: '430px',
        }}
      >

        <div
          style={{
            marginBottom: '28px',
          }}
        >
          <h1>
            CARE-INSPECTOR
          </h1>

          <p>
            Industrial Printer
            Monitoring
          </p>
        </div>


        {error && (
          <div className="error-banner">
            {error}
          </div>
        )}


        <form
          onSubmit={
            handleSubmit
          }
        >

          <div
            className="filter-group"
            style={{
              marginBottom: '18px',
            }}
          >
            <label>
              Email
            </label>

            <input
              type="email"
              value={email}
              required
              autoComplete="username"
              onChange={
                event =>
                  setEmail(
                    event.target.value
                  )
              }
            />
          </div>


          <div
            className="filter-group"
            style={{
              marginBottom: '24px',
            }}
          >
            <label>
              Password
            </label>

            <input
              type="password"
              value={password}
              required
              autoComplete={
                'current-password'
              }
              onChange={
                event =>
                  setPassword(
                    event.target.value
                  )
              }
            />
          </div>


          <button
            className="secondary-button"
            type="submit"
            disabled={loading}
            style={{
              width: '100%',
            }}
          >
            {
              loading
                ? 'Signing in...'
                : 'Sign in'
            }
          </button>

        </form>

      </section>

    </div>
  )
}
