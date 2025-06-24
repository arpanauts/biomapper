// Node.js polyfill for crypto using ESM syntax
import crypto from 'crypto';

// Ensure global.crypto exists with getRandomValues
global.crypto = global.crypto || {};
global.crypto.getRandomValues = function(array) {
  return crypto.randomFillSync(array);
};

export default {};
