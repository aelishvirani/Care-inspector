import {
  createContext,
  useContext,
  useEffect,
  useState,
} from 'react'

import {
  apiGet,
  apiPost,
} from '../api/client'


const AuthContext = createContext(null)


export function AuthProvider({
  children,
}) {
  const [user, setUser] =
    useState(null)

  const [loading, setLoading] =
    useState(true)


  async function loadCurrentUser() {
    const token =
      localStorage.getItem(
        'care_inspector_token'
      )

    if (!token) {
      setUser(null)
      setLoading(false)
      return
    }

    try {
      const currentUser =
        await apiGet('/auth/me')

      setUser(currentUser)

    } catch (error) {
      console.error(error)

      localStorage.removeItem(
        'care_inspector_token'
      )

      localStorage.removeItem(
        'care_inspector_user'
      )

      setUser(null)

    } finally {
      setLoading(false)
    }
  }


  useEffect(() => {
    loadCurrentUser()
  }, [])


  async function login(
    email,
    password
  ) {
    const result =
      await apiPost(
        '/auth/login',
        {
          email,
          password,
        },
        false
      )

    localStorage.setItem(
      'care_inspector_token',
      result.access_token
    )

    localStorage.setItem(
      'care_inspector_user',
      JSON.stringify(
        result.user
      )
    )

    setUser(result.user)

    return result.user
  }


  async function logout() {
    try {
      await apiPost(
        '/auth/logout',
        {}
      )
    } catch (error) {
      console.error(
        'Logout request failed',
        error
      )
    } finally {
      localStorage.removeItem(
        'care_inspector_token'
      )

      localStorage.removeItem(
        'care_inspector_user'
      )

      setUser(null)
    }
  }


  return (
    <AuthContext.Provider
      value={{
        user,
        loading,
        login,
        logout,
      }}
    >
      {children}
    </AuthContext.Provider>
  )
}


export function useAuth() {
  const context =
    useContext(AuthContext)

  if (!context) {
    throw new Error(
      'useAuth must be used inside AuthProvider'
    )
  }

  return context
}
