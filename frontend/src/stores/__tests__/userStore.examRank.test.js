/**
 * Property test for userStore examRank persistence
 *
 * Validates: Requirements 2.2, 2.3
 *
 * Property 8 (partial): For any string value passed as payload.examRank,
 * calling updateUserProfile({ examRank: value }) followed by loadFromStorage()
 * restores the same value in this.examRank.
 *
 * The store uses localStorage for persistence. Because vitest runs in the
 * 'node' environment (no browser globals), we install a minimal in-memory
 * localStorage mock before each test and restore the original after.
 */

import { describe, it, expect, beforeEach, afterEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useUserStore } from '../userStore.js'

// ---------------------------------------------------------------------------
// In-memory localStorage mock
// ---------------------------------------------------------------------------
function createLocalStorageMock() {
  const store = {}
  return {
    getItem(key) {
      return Object.prototype.hasOwnProperty.call(store, key) ? store[key] : null
    },
    setItem(key, value) {
      store[key] = String(value)
    },
    removeItem(key) {
      delete store[key]
    },
    clear() {
      Object.keys(store).forEach((k) => delete store[k])
    },
    get length() {
      return Object.keys(store).length
    },
    key(index) {
      return Object.keys(store)[index] ?? null
    }
  }
}

let originalLocalStorage
let mockStorage

beforeEach(() => {
  // Install mock
  mockStorage = createLocalStorageMock()
  originalLocalStorage = globalThis.localStorage
  globalThis.localStorage = mockStorage

  // Fresh Pinia instance for each test — prevents state leaking between tests
  setActivePinia(createPinia())
})

afterEach(() => {
  // Restore original (undefined in node env, but restore anyway for safety)
  globalThis.localStorage = originalLocalStorage
})

// ---------------------------------------------------------------------------
// Helper: round-trip through updateUserProfile → loadFromStorage
// ---------------------------------------------------------------------------
function roundTrip(examRankValue) {
  const store = useUserStore()
  store.updateUserProfile({ examRank: examRankValue })

  // Simulate a fresh page load by resetting in-memory state then reloading
  store.$reset()
  store.loadFromStorage()

  return store.examRank
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe('userStore — examRank persistence property', () => {
  /**
   * Property: non-empty string values survive a full persist → reload cycle.
   * Validates: Requirements 2.2, 2.3
   */
  describe('non-empty string values persist correctly', () => {
    const nonEmptyStrings = [
      'top 10%',
      '前1000名',
      '12345',
      'rank-A',
      '  leading spaces  ',
      '特殊字符!@#$%',
      'a',
      '0',
      'false',   // the string "false" is truthy — must be preserved as-is
      'null',    // the string "null" is truthy — must be preserved as-is
    ]

    nonEmptyStrings.forEach((value) => {
      it(`persists "${value}" unchanged`, () => {
        expect(roundTrip(value)).toBe(value)
      })
    })
  })

  /**
   * Property: empty string '' persists as ''.
   * Validates: Requirements 2.3, 2.4
   */
  it("empty string '' persists as ''", () => {
    expect(roundTrip('')).toBe('')
  })

  /**
   * Property: null results in '' after reload.
   * Validates: Requirement 2.4
   */
  it('null results in empty string after reload', () => {
    expect(roundTrip(null)).toBe('')
  })

  /**
   * Property: undefined results in '' after reload.
   * Validates: Requirement 2.4
   */
  it('undefined results in empty string after reload', () => {
    expect(roundTrip(undefined)).toBe('')
  })

  /**
   * Property: missing key in payload results in '' after reload.
   * Validates: Requirement 2.4
   */
  it('missing examRank key in payload results in empty string after reload', () => {
    const store = useUserStore()
    // Payload has no examRank key at all
    store.updateUserProfile({ candidateName: 'Alice' })
    store.$reset()
    store.loadFromStorage()
    expect(store.examRank).toBe('')
  })

  /**
   * Property: state is immediately updated in memory (before reload).
   * Validates: Requirement 2.3
   */
  it('in-memory state is updated immediately after updateUserProfile', () => {
    const store = useUserStore()
    store.updateUserProfile({ examRank: '前500名' })
    // No $reset — check in-memory value directly
    expect(store.examRank).toBe('前500名')
  })

  /**
   * Property: in-memory state is '' immediately when null/undefined passed.
   * Validates: Requirement 2.4
   */
  it('in-memory state is empty string immediately when null passed', () => {
    const store = useUserStore()
    store.updateUserProfile({ examRank: null })
    expect(store.examRank).toBe('')
  })

  /**
   * Property: localStorage key 'exam_rank' is written with the correct value.
   * Validates: Requirement 2.3
   */
  it("writes 'exam_rank' key to localStorage with the correct value", () => {
    const store = useUserStore()
    store.updateUserProfile({ examRank: 'top 5%' })
    expect(mockStorage.getItem('exam_rank')).toBe('top 5%')
  })

  /**
   * Property: localStorage key 'exam_rank' is written as '' for falsy inputs.
   * Validates: Requirement 2.4
   */
  it("writes '' to localStorage 'exam_rank' when null is passed", () => {
    const store = useUserStore()
    store.updateUserProfile({ examRank: null })
    expect(mockStorage.getItem('exam_rank')).toBe('')
  })

  /**
   * Property: loadFromStorage falls back to '' when 'exam_rank' key is absent.
   * Validates: Requirement 2.2
   */
  it("loadFromStorage returns '' when 'exam_rank' key is absent from localStorage", () => {
    const store = useUserStore()
    // Do NOT call updateUserProfile — key is never written
    store.loadFromStorage()
    expect(store.examRank).toBe('')
  })

  /**
   * Property: updateUserProfile does not throw when localStorage is unavailable.
   * Validates: Requirement 2.3 (silent failure on write error)
   */
  it('does not throw when localStorage.setItem throws (silent failure)', () => {
    // Override setItem to simulate a full storage / private-mode error
    mockStorage.setItem = () => { throw new DOMException('QuotaExceededError') }

    const store = useUserStore()
    expect(() => store.updateUserProfile({ examRank: 'some rank' })).not.toThrow()
    // In-memory state must still be updated despite the write failure
    expect(store.examRank).toBe('some rank')
  })
})
