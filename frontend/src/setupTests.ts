import "@testing-library/jest-dom/vitest";

// vitest's jsdom integration misses `localStorage` (a getter on jsdom's
// Window prototype) and falls through to Node's own global, which warns and
// stays unusable. An in-memory stand-in closes that gap for tests; real
// browsers are unaffected. The accent picker is the one user of it.
class MemoryStorage implements Storage {
  private store = new Map<string, string>();
  get length() {
    return this.store.size;
  }
  clear() {
    this.store.clear();
  }
  getItem(key: string) {
    return this.store.has(key) ? (this.store.get(key) as string) : null;
  }
  key(index: number) {
    return Array.from(this.store.keys())[index] ?? null;
  }
  removeItem(key: string) {
    this.store.delete(key);
  }
  setItem(key: string, value: string) {
    this.store.set(key, String(value));
  }
}

function installLocalStorageShimIfNeeded() {
  try {
    if (typeof globalThis.localStorage !== "undefined" && globalThis.localStorage !== null) {
      globalThis.localStorage.setItem("__probe__", "1");
      globalThis.localStorage.removeItem("__probe__");
      return;
    }
  } catch {
    // Falls through to install the shim below.
  }
  Object.defineProperty(globalThis, "localStorage", {
    value: new MemoryStorage(),
    configurable: true,
    writable: true,
  });
}
installLocalStorageShimIfNeeded();
