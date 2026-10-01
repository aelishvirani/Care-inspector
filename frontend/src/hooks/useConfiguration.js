import {
  useEffect,
  useState,
} from 'react'

import {
  getConfiguration,
  updateConfiguration,
} from '../services/configurationService'


export function useConfiguration() {
  const [
    configuration,
    setConfiguration,
  ] = useState(null)

  const [loading, setLoading] =
    useState(true)

  const [saving, setSaving] =
    useState(false)

  const [error, setError] =
    useState(null)

  const [saved, setSaved] =
    useState(false)


  async function load() {
    try {
      const data =
        await getConfiguration()

      setConfiguration(data)
      setError(null)

    } catch (err) {
      console.error(err)

      setError(
        'Unable to load configuration'
      )

    } finally {
      setLoading(false)
    }
  }


  async function save() {
    try {
      setSaving(true)
      setSaved(false)

      await updateConfiguration(
        configuration
      )

      setSaved(true)
      setError(null)

    } catch (err) {
      console.error(err)

      setError(
        'Unable to save configuration'
      )

    } finally {
      setSaving(false)
    }
  }


  useEffect(() => {
    load()
  }, [])


  return {
    configuration,
    setConfiguration,
    loading,
    saving,
    error,
    saved,
    save,
  }
}
