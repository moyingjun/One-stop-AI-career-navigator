/**
 * Property 4: No CJK character splitting across chunk boundaries
 * Validates: Requirements 4.9
 *
 * Tests that TextDecoder({ stream: true }) correctly reassembles CJK (Chinese/Japanese/Korean)
 * multi-byte UTF-8 characters when the byte stream is split at arbitrary boundaries.
 *
 * CJK characters in UTF-8 are encoded as 3 bytes each. When a network chunk boundary
 * falls in the middle of a character's byte sequence, a naive decoder would produce
 * corrupted output (replacement characters U+FFFD). The { stream: true } option
 * tells TextDecoder to buffer incomplete sequences across decode() calls.
 */

import { describe, it, expect } from 'vitest'
import fc from 'fast-check'

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/**
 * Decode a Uint8Array byte sequence in multiple chunks using a single
 * TextDecoder instance with { stream: true }, simulating how streamInterviewChat
 * processes the ReadableStream from fetch().
 *
 * @param {Uint8Array} bytes - Full encoded byte sequence
 * @param {number[]} splitPoints - Byte indices at which to split the buffer
 * @returns {string} Concatenated decoded output
 */
function decodeInChunks(bytes, splitPoints) {
  // One decoder per "stream call" — mirrors the implementation in llm_service.js
  const decoder = new TextDecoder('utf-8')
  let result = ''

  // Build chunk boundaries: [0, ...splitPoints (sorted, deduplicated), bytes.length]
  const validSplits = [...new Set(splitPoints.filter(p => p > 0 && p < bytes.length))].sort((a, b) => a - b)
  const boundaries = [0, ...validSplits, bytes.length]

  for (let i = 0; i < boundaries.length - 1; i++) {
    const chunk = bytes.slice(boundaries[i], boundaries[i + 1])
    // { stream: true } tells the decoder to hold incomplete multi-byte sequences
    // in its internal buffer rather than emitting a replacement character
    result += decoder.decode(chunk, { stream: true })
  }

  // Final flush: call decode() without { stream: true } to flush any buffered bytes
  result += decoder.decode()

  return result
}

// ---------------------------------------------------------------------------
// Test 1 — Property-based: arbitrary Chinese strings, arbitrary split points
// ---------------------------------------------------------------------------

describe('Property 4: No CJK character splitting across chunk boundaries', () => {
  it('Test 1: arbitrary Chinese strings reassemble correctly at any byte split point', () => {
    /**
     * **Validates: Requirements 4.9**
     *
     * Property: for any non-empty Chinese string S and any set of byte-level split
     * points, decoding the UTF-8 bytes of S in those chunks with a single
     * TextDecoder({ stream: true }) instance produces exactly S.
     */
    fc.assert(
      fc.property(
        // Generate non-empty strings from the CJK Unified Ideographs block (U+4E00–U+9FFF)
        fc.string({
          unit: fc.mapToConstant({
            num: 0x9FFF - 0x4E00 + 1,
            build: i => String.fromCodePoint(0x4E00 + i)
          }),
          minLength: 1,
          maxLength: 30
        }),
        // Generate 1–5 arbitrary split points within the byte range
        fc.array(fc.nat({ max: 200 }), { minLength: 1, maxLength: 5 }),
        (chineseStr, rawSplitPoints) => {
          const encoder = new TextEncoder()
          const bytes = encoder.encode(chineseStr)

          // Clamp split points to valid byte range
          const splitPoints = rawSplitPoints.map(p => p % (bytes.length + 1))

          const decoded = decodeInChunks(bytes, splitPoints)
          return decoded === chineseStr
        }
      ),
      { numRuns: 200 }
    )
  })

  // ---------------------------------------------------------------------------
  // Test 2 — Deterministic: 3-byte CJK character split after byte 1 and byte 2
  // ---------------------------------------------------------------------------

  it('Test 2: 3-byte CJK character split after byte 1 or byte 2 decodes without corruption', () => {
    /**
     * **Validates: Requirements 4.9**
     *
     * A single CJK character (e.g. '中', U+4E2D) encodes to exactly 3 bytes in UTF-8:
     *   0xE4 0xB8 0xAD
     * Splitting after byte 1 or byte 2 must not produce replacement characters.
     */
    const testCases = [
      { char: '中', description: 'U+4E2D' },
      { char: '文', description: 'U+6587' },
      { char: '字', description: 'U+5B57' },
      { char: '你', description: 'U+4F60' },
      { char: '好', description: 'U+597D' },
    ]

    const encoder = new TextEncoder()

    for (const { char, description } of testCases) {
      const bytes = encoder.encode(char)
      expect(bytes.length, `${char} (${description}) should be 3 bytes`).toBe(3)

      // Split after byte 1 (inside the multi-byte sequence)
      const splitAfter1 = decodeInChunks(bytes, [1])
      expect(splitAfter1, `${char} split after byte 1`).toBe(char)
      expect(splitAfter1, `no replacement char when split after byte 1`).not.toContain('\uFFFD')

      // Split after byte 2 (inside the multi-byte sequence)
      const splitAfter2 = decodeInChunks(bytes, [2])
      expect(splitAfter2, `${char} split after byte 2`).toBe(char)
      expect(splitAfter2, `no replacement char when split after byte 2`).not.toContain('\uFFFD')

      // Split after both byte 1 and byte 2 (each byte in its own chunk)
      const splitEveryByte = decodeInChunks(bytes, [1, 2])
      expect(splitEveryByte, `${char} split at every byte boundary`).toBe(char)
      expect(splitEveryByte, `no replacement char when split at every byte`).not.toContain('\uFFFD')
    }
  })

  // ---------------------------------------------------------------------------
  // Test 3 — Mixed ASCII and CJK characters
  // ---------------------------------------------------------------------------

  it('Test 3: mixed ASCII and CJK strings reassemble correctly at arbitrary byte splits', () => {
    /**
     * **Validates: Requirements 4.9**
     *
     * Real SSE payloads often mix ASCII punctuation/spaces with CJK content.
     * This test verifies that mixed strings are also handled correctly.
     */
    const mixedStrings = [
      'Hello 你好 World',
      '面试官: 请介绍一下你自己',
      'AI回复: 好的，我来介绍...',
      '分数: 85/100 (优秀)',
      'resume_text: 张三，软件工程师',
      '问题1: 你的技术栈是什么？',
    ]

    const encoder = new TextEncoder()

    for (const str of mixedStrings) {
      const bytes = encoder.encode(str)

      // Test splits at every possible byte boundary
      for (let splitAt = 1; splitAt < bytes.length; splitAt++) {
        const decoded = decodeInChunks(bytes, [splitAt])
        expect(decoded, `"${str}" split at byte ${splitAt}`).toBe(str)
        expect(decoded, `no replacement char in "${str}" split at byte ${splitAt}`).not.toContain('\uFFFD')
      }
    }
  })

  // ---------------------------------------------------------------------------
  // Test 4 — Single decoder instance handles the full stream correctly
  // ---------------------------------------------------------------------------

  it('Test 4: a single TextDecoder instance (not recreated per chunk) handles streaming correctly', () => {
    /**
     * **Validates: Requirements 4.9**
     *
     * The implementation in llm_service.js creates ONE TextDecoder per streamInterviewChat
     * call and reuses it across all reader.read() iterations. This test verifies that
     * reusing the same decoder across many chunks (simulating many read() calls) works
     * correctly — the decoder's internal state carries over between decode() calls.
     *
     * Contrast: if a new TextDecoder were created per chunk (wrong approach), incomplete
     * multi-byte sequences at chunk boundaries would be lost or corrupted.
     */
    const longChineseText = '这是一段较长的中文文本，用于测试流式解码器在多次调用之间能否正确保持内部状态。' +
      '每个汉字占用三个字节，当网络分块恰好切割在字节序列中间时，解码器必须将不完整的字节缓存起来，' +
      '等待下一个分块到来后再完成解码。这正是TextDecoder的stream模式所提供的核心能力。'

    const encoder = new TextEncoder()
    const bytes = encoder.encode(longChineseText)

    // Simulate many small chunks (1–4 bytes each), as might happen on a slow network
    const decoder = new TextDecoder('utf-8')
    let result = ''
    const chunkSize = 4  // deliberately small to maximize mid-character splits

    for (let offset = 0; offset < bytes.length; offset += chunkSize) {
      const chunk = bytes.slice(offset, Math.min(offset + chunkSize, bytes.length))
      const isLast = offset + chunkSize >= bytes.length
      // Only flush (no stream:true) on the last chunk
      result += decoder.decode(chunk, { stream: !isLast })
    }

    expect(result).toBe(longChineseText)
    expect(result).not.toContain('\uFFFD')

    // Verify that creating a NEW decoder per chunk (the wrong approach) would fail
    // for at least one split point — demonstrating WHY the single-instance approach matters
    let corruptedResult = ''
    for (let offset = 0; offset < bytes.length; offset += chunkSize) {
      const chunk = bytes.slice(offset, Math.min(offset + chunkSize, bytes.length))
      // Wrong: new decoder per chunk loses buffered incomplete sequences
      const freshDecoder = new TextDecoder('utf-8')
      corruptedResult += freshDecoder.decode(chunk)  // no { stream: true }
    }

    // The corrupted result should differ from the original (replacement chars introduced)
    // Note: this assertion documents the bug that the implementation avoids
    expect(corruptedResult).not.toBe(longChineseText)
  })
})
