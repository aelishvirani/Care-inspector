// UUIDs are protocol identifiers, not device names or passwords.
// A future Raspberry Pi BLE agent must expose these exact UUIDs.
export const CARE_INSPECTOR_SERVICE = 'a18d7b10-f0e7-4d5e-8c1b-86e418d85001'
export const PI_IDENTITY_CHARACTERISTIC = 'a18d7b11-f0e7-4d5e-8c1b-86e418d85001'

const decoder = new TextDecoder()

/**
 * Read a bounded, non-secret identity preview from a Pi BLE GATT service.
 *
 * NOTE: A GATT UUID/JSON response proves *compatibility*, not authenticity.
 * Cloud pairing still requires cryptographic challenge/response.
 */
export async function readPiIdentity(device) {
  if (!device?.gatt) throw new Error('Device does not expose Bluetooth GATT')
  let server
  try {
    server = await device.gatt.connect()
    const service = await server.getPrimaryService(CARE_INSPECTOR_SERVICE)
    const characteristic = await service.getCharacteristic(PI_IDENTITY_CHARACTERISTIC)
    const value = await characteristic.readValue()
    if (value.byteLength > 512) throw new Error('Identity response too large')

    const raw = decoder.decode(value)
    const identity = JSON.parse(raw)
    if (!identity || typeof identity !== 'object' || Array.isArray(identity)) {
      throw new Error('Invalid Pi identity payload')
    }
    const valid = key => typeof identity[key] === 'string' && identity[key].length <= 128
    if (!valid('hardware_id') || !/^[a-zA-Z0-9:_-]{8,128}$/.test(identity.hardware_id)) {
      throw new Error('Invalid Pi hardware identifier')
    }
    if (!valid('model') || !valid('hostname')) {
      throw new Error('Missing Pi model or hostname')
    }
    return {
      hardwareId: identity.hardware_id,
      model: identity.model,
      hostname: identity.hostname,
      macAddress: valid('mac_address') ? identity.mac_address : '',
      protocolVersion: valid('protocol_version') ? identity.protocol_version : 'unknown',
    }
  } finally {
    // End the temporary identity-read connection, even if the read fails.
    if (device.gatt?.connected) device.gatt.disconnect()
  }
}
