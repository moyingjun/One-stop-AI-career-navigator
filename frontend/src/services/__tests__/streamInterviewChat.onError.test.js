/**
 * @vitest-environment jsdom
 *
 * Property 6: onError called at most once per stream invocation
 * Validates: Requirements 4.4
 *
 * Tests that the `errorFired` guard in streamInterviewChat() ensures
 * onError is called at most once regardless of how many error conditions
 * are encountered during a single invocation.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { streamInterviewChat } from '../llm_service.js'

// ─── helpers ────────────────────────────────────────────────────────────────

/**
 * Build a minimal ReadableStream from an array of Uint8Array chunks.
 * Each chunk is yielded in order; the stream closes after the last one.
 */
function makeReadableStream(chunks) {
  let index = 0
  return new ReadableStream({
    pull(controller) {
      if (index < chunks.length) {
        controller.enqueue(chunks[index++])
      } else {
        controller.close()
      }
    }
  })
}

/**
 * Encode a plain string to Uint8Array (UTF-8).
 */
function enc(str) {
  return new TextEncoder().encode(str)
}

/**
 * Build a mock Response object with a given status and body stream.
 */
function makeResponse(status, bodyStream) {
  return {
    ok: status >= 200 && status < 300,
    status,
    body: bodyStream ?? makeReadableStream([])
  }
}

// ─── test suite ─────────────────────────────────────────────────────────────

describe('streamInterviewChat — Property 6: onError called at most once', () => {
  beforeEach(() => {
    vi.unstubAllGlobals()
  })

  afterEach(() => {
    vi.unstubAllGlobals()
  })

  // ── Test 1 ──────────────────────────────────────────────────────────────
  it('Test 1: fetch throws a network error → onError called exactly once', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new TypeError('Failed to fetch')))

    const onChunk = vi.fn()
    const onError = vi.fn()

    await streamInterviewChat('/interview/chat', {}, onChunk, onError)

    expect(onError).toHaveBeenCalledTimes(1)
    expect(onError).toHaveBeenCalledWith('[网络连接异常，请重试]')
    expect(onChunk).not.toHaveBeenCalled()
  })

  // ── Test 2 ──────────────────────────────────────────────────────────────
  it('Test 2: fetch returns non-200 response → onError called exactly once', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(makeResponse(500, null))
    )

    const onChunk = vi.fn()
    const onError = vi.fn()

    await streamInterviewChat('/interview/chat', {}, onChunk, onError)

    expect(onError).toHaveBeenCalledTimes(1)
    expect(onError).toHaveBeenCalledWith('[网络连接异常，请重试]')
    expect(onChunk).not.toHaveBeenCalled()
  })

  // ── Test 3 ──────────────────────────────────────────────────────────────
  it('Test 3: fetch succeeds but reader.read() throws → onError called exactly once', async () => {
    // A ReadableStream whose reader throws on the first read
    const throwingStream = new ReadableStream({
      pull() {
        throw new TypeError('network error mid-stream')
      }
    })

    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(makeResponse(200, throwingStream))
    )

    const onChunk = vi.fn()
    const onError = vi.fn()

    await streamInterviewChat('/interview/chat', {}, onChunk, onError)

    expect(onError).toHaveBeenCalledTimes(1)
    expect(onError).toHaveBeenCalledWith('[网络连接异常，请重试]')
  })

  // ── Test 4 ──────────────────────────────────────────────────────────────
  it('Test 4: successful SSE stream with no errors → onError called zero times', async () => {
    // A well-formed SSE stream: one message block followed by a done block
    const sseData =
      'event: message\ndata: {"content":"hello"}\n\n' +
      'event: done\ndata: {}\n\n'

    const stream = makeReadableStream([enc(sseData)])

    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(makeResponse(200, stream))
    )

    const onChunk = vi.fn()
    const onError = vi.fn()

    await streamInterviewChat('/interview/chat', {}, onChunk, onError)

    expect(onError).toHaveBeenCalledTimes(0)
    expect(onChunk).toHaveBeenCalledWith('hello')
  })

  // ── Test 5 ──────────────────────────────────────────────────────────────
  it('Test 5: multiple error conditions in sequence → onError called at most once total', async () => {
    /**
     * Simulate a scenario where fetch itself throws AND the catch block
     * would theoretically fire multiple times. The errorFired flag must
     * prevent more than one onError call.
     *
     * We achieve this by making fetch throw synchronously so the outer
     * try/catch fires, and we verify the guard holds even if the error
     * path is re-entered (e.g., via a second awaited rejection).
     *
     * Strategy: use a custom fetch that throws twice in sequence by
     * returning a response whose body reader throws on every read attempt.
     */
    let readCount = 0
    const multiThrowStream = new ReadableStream({
      pull() {
        readCount++
        throw new TypeError(`read error #${readCount}`)
      }
    })

    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(makeResponse(200, multiThrowStream))
    )

    const onChunk = vi.fn()
    const onError = vi.fn()

    await streamInterviewChat('/interview/chat', {}, onChunk, onError)

    // Regardless of how many internal errors occurred, onError must be ≤ 1
    expect(onError.mock.calls.length).toBeLessThanOrEqual(1)
    // And it should have been called exactly once (the first error triggers it)
    expect(onError).toHaveBeenCalledTimes(1)
    expect(onError).toHaveBeenCalledWith('[网络连接异常，请重试]')
  })
})
