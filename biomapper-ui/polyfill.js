// Polyfill for crypto.getRandomValues
if (typeof crypto === 'undefined' || !crypto.getRandomValues) {
  console.warn('Polyfilling crypto.getRandomValues');
  
  // Create a basic crypto object with getRandomValues if it doesn't exist
  global.crypto = global.crypto || {};
  
  // Simple polyfill for getRandomValues
  global.crypto.getRandomValues = function(array) {
    for (let i = 0; i < array.length; i++) {
      array[i] = Math.floor(Math.random() * 256);
    }
    return array;
  };
}
