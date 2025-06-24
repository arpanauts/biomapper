// Custom polyfill for crypto.getRandomValues
// This is a fallback implementation that's not cryptographically secure
// but will allow the application to run for demonstration purposes

if (typeof window !== 'undefined' && !window.crypto) {
  console.warn('Polyfilling window.crypto');
  window.crypto = {};
}

if (typeof window !== 'undefined' && !window.crypto.getRandomValues) {
  console.warn('Polyfilling window.crypto.getRandomValues');
  
  window.crypto.getRandomValues = function(array) {
    for (let i = 0; i < array.length; i++) {
      array[i] = Math.floor(Math.random() * 256);
    }
    return array;
  };
}

export default {};
