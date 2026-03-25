// Polyfill global pour Node.js
if (typeof globalThis.File === 'undefined') {
  globalThis.File = class File {
    constructor(bits, name, options = {}) {
      this.name = name;
      this.type = options.type || '';
      this.lastModified = options.lastModified || Date.now();
      this.size = bits.reduce((acc, bit) => acc + (typeof bit === 'string' ? bit.length : bit.size || 0), 0);
    }
  };
}

if (typeof globalThis.Blob === 'undefined') {
  globalThis.Blob = class Blob {
    constructor(bits = [], options = {}) {
      this.bits = bits;
      this.type = options.type || '';
      this.size = bits.reduce((acc, bit) => acc + (typeof bit === 'string' ? bit.length : bit.size || 0), 0);
    }
  };
}
