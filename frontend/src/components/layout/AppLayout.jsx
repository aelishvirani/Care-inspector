import {
  useEffect,
  useMemo,
  useState,
} from 'react'

import {
  Outlet,
  useNavigate,
} from 'react-router-dom'

import Sidebar from './Sidebar'

import {
  useAuth,
} from '../../auth/AuthContext'

import {
  apiGet,
} from '../../api/client'


export default function AppLayout() {
  const {
    user,
    logout,
  } = useAuth()

  const navigate =
    useNavigate()

  const [
    search,
    setSearch,
  ] = useState('')

  const [
    printers,
    setPrinters,
  ] = useState([])


  useEffect(() => {
    if (
      user?.role
      !== 'TECHNICIAN'
    ) {
      return
    }

    apiGet(
      '/secure/devices'
    )
      .then(setPrinters)
      .catch(
        error =>
          console.error(
            error
          )
      )
  }, [user])


  const searchResults =
    useMemo(
      () => {
        const term =
          search
            .trim()
            .toLowerCase()

        if (!term) {
          return []
        }

        return printers
          .filter(
            printer =>
              [
                printer.display_name,
                printer.device_id,
                printer.model_name,
                printer.serial_number,
                printer.location,
              ]
                .filter(Boolean)
                .some(
                  value =>
                    String(value)
                      .toLowerCase()
                      .includes(term)
                )
          )
          .slice(0, 6)
      },
      [
        printers,
        search,
      ]
    )


  function handleLogout() {
    logout()

    navigate(
      '/login',
      {
        replace: true,
      }
    )
  }


  function openPrinter(
    printer
  ) {
    setSearch('')

    navigate(
      `/printers/${encodeURIComponent(
        printer.device_id
      )}`
    )
  }


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
              {
                user?.role
                  === 'TECHNICIAN'
                  ? 'Technik / Service Panel'
                  : 'Customer Monitoring'
              }
            </span>
          </div>


          {
            user?.role
              === 'TECHNICIAN'
            && (
              <div
                style={{
                  position:
                    'relative',
                  width: '360px',
                  maxWidth: '35vw',
                }}
              >

                <input
                  type="search"
                  placeholder={
                    'Search printer, serial, model, location...'
                  }
                  value={search}
                  onChange={
                    event =>
                      setSearch(
                        event.target.value
                      )
                  }
                  style={{
                    width: '100%',
                    padding:
                      '9px 12px',
                    border:
                      '1px solid #ccd6db',
                  }}
                />


                {
                  search
                  && (
                    <div
                      style={{
                        position:
                          'absolute',
                        top: '45px',
                        left: 0,
                        right: 0,
                        zIndex: 1000,
                        background:
                          'white',
                        border:
                          '1px solid #dce3e7',
                      }}
                    >

                      {
                        searchResults.length
                          === 0
                        ? (
                          <div
                            style={{
                              padding:
                                '14px',
                            }}
                          >
                            No results
                          </div>
                        )
                        : searchResults.map(
                          printer => (

                            <button
                              key={
                                printer.device_id
                              }
                              type="button"
                              onClick={() =>
                                openPrinter(
                                  printer
                                )
                              }
                              style={{
                                width:
                                  '100%',
                                border: 0,
                                borderBottom:
                                  '1px solid #edf0f2',
                                background:
                                  'white',
                                padding:
                                  '12px',
                                textAlign:
                                  'left',
                                cursor:
                                  'pointer',
                              }}
                            >

                              <strong>
                                {
                                  printer.display_name
                                  || printer.device_id
                                }
                              </strong>

                              <div
                                style={{
                                  marginTop:
                                    '3px',
                                  fontSize:
                                    '11px',
                                  color:
                                    '#79858e',
                                }}
                              >
                                {
                                  printer.model_name
                                  || 'Unknown model'
                                }
                                {' · '}
                                {
                                  printer.serial_number
                                  || 'No serial'
                                }
                              </div>

                            </button>

                          )
                        )
                      }

                    </div>
                  )
                }

              </div>
            )
          }


          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '16px',
            }}
          >

            <div>
              <strong>
                {user?.email}
              </strong>

              <div
                style={{
                  fontSize: '12px',
                }}
              >
                {user?.role}
              </div>
            </div>


            <button
              className="secondary-button"
              onClick={
                handleLogout
              }
            >
              Logout
            </button>

          </div>

        </header>


        <main className="app-main">
          <Outlet />
        </main>

      </div>

    </div>
  )
}
