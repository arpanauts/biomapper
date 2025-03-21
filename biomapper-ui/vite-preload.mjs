// Polyfill Node crypto for browser environment
import { webcrypto } from 'node:crypto'
globalThis.crypto = {
  getRandomValues: (array) => {
    webcrypto.getRandomValues(array)
    return array
  }
}

console.log("✅ Crypto polyfill loaded successfully")
