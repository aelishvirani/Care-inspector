// UUIDs are protocol identifiers, not device names or passwords.
// A future Raspberry Pi BLE agent must expose these exact UUIDs.
export const CARE_INSPECTOR_SERVICE = 'a18d7b10-f0e7-4d5e-8c1b-86e418d85001'
export const PI_IDENTITY_CHARACTERISTIC = 'a18d7b11-f0e7-4d5e-8c1b-86e418d85001'

export const PI_PUBLIC_KEY_CHARACTERISTIC = 'a18d7b12-f0e7-4d5e-8c1b-86e418d85001'
export const PI_CHALLENGE_CHARACTERISTIC = 'a18d7b13-f0e7-4d5e-8c1b-86e418d85001'
export const PI_PROOF_CHARACTERISTIC = 'a18d7b14-f0e7-4d5e-8c1b-86e418d85001'

const decoder = new TextDecoder()
const encoder = new TextEncoder()

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

/**
 * Perform untrusted BLE key-possession proof with an authorized cloud API.
 * This NEVER registers or authorizes the Pi.
 *
 * All reads/writes operate through a single, temporary GATT session.
 */
export async function verifyPiKeyPossession(device, identity, apiPost) {
  if (!device?.gatt) throw new Error('Selected device does not support BLE GATT')
  if (!identity?.hardwareId || !/^[a-zA-Z0-9:_-]{8,128}$/.test(identity.hardwareId)) {
    throw new Error('Check Pi identity before verifying its key')
  }

  try {
    const server = await device.gatt.connect()
    const service = await server.getPrimaryService(CARE_INSPECTOR_SERVICE)

    const keyCharacteristic = await service.getCharacteristic(PI_PUBLIC_KEY_CHARACTERISTIC)
    const keyValue = await keyCharacteristic.readValue()
    if (keyValue.byteLength !== 44) throw new Error('Invalid Ed25519 public key size')
    const publicKey = decoder.decode(keyValue).trim()
    if (!/^[A-Za-z0-9+/]{43}=$/.test(publicKey)) {
      throw new Error('Invalid Ed25519 public key encoding')
    }

    const pairing = await apiPost('/secure/management/pi-pairing/start', {
      hardware_id: identity.hardwareId,
      public_key_b64: publicKey,
    })
    if (!pairing?.pairing_id || !pairing?.challenge_b64) {
      throw new Error('Pairing challenge response is incomplete')
    }

    const challengeCharacteristic = await service.getCharacteristic(PI_CHALLENGE_CHARACTERISTIC)
    const challengeBytes = encoder.encode(JSON.stringify({
      pairing_id: pairing.pairing_id,
      hardware_id: identity.hardwareId,
      challenge_b64: pairing.challenge_b64,
    }))
    if (challengeBytes.byteLength > 350) throw new Error('Challenge exceeds BLE limit')
    // writeValueWithResponse ensures the Pi accepted the challenge before reading.
    await challengeCharacteristic.writeValueWithResponse(challengeBytes)

    const proofCharacteristic = await service.getCharacteristic(PI_PROOF_CHARACTERISTIC)
    const proofValue = await proofCharacteristic.readValue()
    if (proofValue.byteLength !== 88) throw new Error('Invalid signature length')
    const signature = decoder.decode(proofValue).trim()
    if (!/^[A-Za-z0-9+/]{86}==$/.test(signature)) {
      throw new Error('Invalid Ed25519 signature encoding')
    }

    const result = await apiPost(
      `/secure/management/pi-pairing/${encodeURIComponent(pairing.pairing_id)}/verify`,
      { signature_b64: signature },
    )
    if (result?.status !== 'key_possession_confirmed' ||
        result?.trusted_device !== false || result?.enrolled !== false) {
      throw new Error('Unexpected pairing verification status')
    }
    return result
  } finally {
    if (device.gatt?.connected) device.gatt.disconnect()
  }
}
