// @vitest-environment jsdom
/**
 * Property test for streamInterviewChat — Property 5: Ping blocks never trigger onChunk
 *
 * Validates: Requirements 4.5
 *
 * Tests that SSE streams containing `: ping\n\n` heartbeat comments and
 * `event: ping\ndata: {}\n\n` ping events never cause onChunk to be called,
 * even when mixed with valid message blocks.
 *
 * **Validates: Requirements 4.5**
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import fc from 'fast-check'

// ---------------------------------------------------------------------------
// Helper: build a mock ReadableStream from a raw SSE string
// ---------------------------------------------------------------------------

/**
 * 将 SSE 字符串编码为 Uint8Array 并包装成 ReadableStream，
 * 模拟浏览器 fetch 返回的 response.body。
 *
 * @param {string} sseText - 完整的 SSE 文本内容
 * @returns {ReadableStream}
 */
function buildMockReadableStream(sseText) {
  const encoder = new TextEncoder()
  const bytes = encoder.encode(sseText)
  return new ReadableStream({
    start(controller) {
      controller.enqueue(bytes)
      controller.close()
    }
  })
}

/**
 * 将 SSE 字符串按任意字节边界切割成多个 chunk，
 * 用于测试 TextDecoder({ stream: true }) 的 CJK 安全性。
 *
 * @param {string} sseText - 完整的 SSE 文本内容
 * @param {number[]} splitPoints - 切割点（字节偏移量数组，已排序）
 * @returns {ReadableStream}
 */
function buildChunkedReadableStream(sseText, splitPoints) {
  const encoder = new TextEncoder()
  const bytes = encoder.encode(sseText)
  return new ReadableStream({
    start(controller) {
      let prev = 0
      for (const point of splitPoints) {
        if (point > prev && point < bytes.length) {
          controller.enqueue(bytes.slice(prev, point))
          prev = point
        }
      }
      if (prev < bytes.length) {
        controller.enqueue(bytes.slice(prev))
      }
      controller.close()
    }
  })
}

// ---------------------------------------------------------------------------
// Helper: create a mock fetch that returns the given ReadableStream
// ---------------------------------------------------------------------------

/**
 * 创建一个模拟 fetch，返回包含给定 ReadableStream 的 Response 对象。
 *
 * @param {ReadableStream} stream
 * @returns {Function} mock fetch function
 */
function createMockFetch(stream) {
  return vi.fn().mockResolvedValue({
    ok: true,
    status: 200,
    body: stream
  })
}

// ---------------------------------------------------------------------------
// SSE block builders
// ---------------------------------------------------------------------------

/** 心跳注释行（以 ': ' 开头） */
const HEARTBEAT_PING = ': ping\n\n'

/** event: ping 块 */
const EVENT_PING = 'event: ping\ndata: {}\n\n'

/**
 * 构建一个合法的 event: message 块。
 *
 * @param {string} content - 消息内容
 * @returns {string}
 */
function buildMessageBlock(content) {
  return `event: message\ndata: ${JSON.stringify({ content })}\n\n`
}

/** 流结束块 */
const DONE_BLOCK = 'event: done\ndata: {}\n\n'

// ---------------------------------------------------------------------------
// Import the function under test
// ---------------------------------------------------------------------------

// llm_service.js 顶层读取 window.location.hostname，需要在 jsdom 环境下运行。
// vitest 的 environmentMatchGlobs 已将 src/**/__tests__/** 映射到 jsdom。
let streamInterviewChat

beforeEach(async () => {
  // 动态导入以确保每次测试都获得干净的模块状态
  const mod = await import('../llm_service.js')
  streamInterviewChat = mod.streamInterviewChat
})

afterEach(() => {
  vi.unstubAllGlobals()
})

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe('streamInterviewChat — Property 5: ping blocks never trigger onChunk', () => {

  /**
   * Test 1: 仅包含 `: ping\n\n` 心跳注释的流 — onChunk 不应被调用
   */
  it('Test 1: stream with only heartbeat comment pings — onChunk never called', async () => {
    // 构造仅含心跳注释的 SSE 流
    const sseText = HEARTBEAT_PING.repeat(5) + DONE_BLOCK
    const mockFetch = createMockFetch(buildMockReadableStream(sseText))
    vi.stubGlobal('fetch', mockFetch)

    const onChunk = vi.fn()
    const onError = vi.fn()

    await streamInterviewChat('/interview/chat', {}, onChunk, onError)

    expect(onChunk).not.toHaveBeenCalled()
    expect(onError).not.toHaveBeenCalled()
  })

  /**
   * Test 2: 仅包含 `event: ping\ndata: {}\n\n` ping 事件的流 — onChunk 不应被调用
   */
  it('Test 2: stream with only event:ping blocks — onChunk never called', async () => {
    const sseText = EVENT_PING.repeat(5) + DONE_BLOCK
    const mockFetch = createMockFetch(buildMockReadableStream(sseText))
    vi.stubGlobal('fetch', mockFetch)

    const onChunk = vi.fn()
    const onError = vi.fn()

    await streamInterviewChat('/interview/chat', {}, onChunk, onError)

    expect(onChunk).not.toHaveBeenCalled()
    expect(onError).not.toHaveBeenCalled()
  })

  /**
   * Test 3: ping 块与合法 message 块混合 — onChunk 仅对 message 块调用
   */
  it('Test 3: ping blocks mixed with message blocks — onChunk called only for messages', async () => {
    const messageContents = ['Hello', '你好', 'World']
    const sseText =
      HEARTBEAT_PING +
      buildMessageBlock(messageContents[0]) +
      EVENT_PING +
      buildMessageBlock(messageContents[1]) +
      HEARTBEAT_PING +
      EVENT_PING +
      buildMessageBlock(messageContents[2]) +
      DONE_BLOCK

    const mockFetch = createMockFetch(buildMockReadableStream(sseText))
    vi.stubGlobal('fetch', mockFetch)

    const onChunk = vi.fn()
    const onError = vi.fn()

    await streamInterviewChat('/interview/chat', {}, onChunk, onError)

    // onChunk 应恰好被调用 3 次，且参数与 message 内容一致
    expect(onChunk).toHaveBeenCalledTimes(3)
    expect(onChunk).toHaveBeenNthCalledWith(1, messageContents[0])
    expect(onChunk).toHaveBeenNthCalledWith(2, messageContents[1])
    expect(onChunk).toHaveBeenNthCalledWith(3, messageContents[2])
    expect(onError).not.toHaveBeenCalled()
  })

  /**
   * Test 4: message 块之前有多个 ping 块 — onChunk 恰好调用一次
   */
  it('Test 4: multiple ping blocks before a message block — onChunk called exactly once', async () => {
    const content = '面试开始'
    const sseText =
      HEARTBEAT_PING +
      EVENT_PING +
      HEARTBEAT_PING +
      EVENT_PING +
      buildMessageBlock(content) +
      DONE_BLOCK

    const mockFetch = createMockFetch(buildMockReadableStream(sseText))
    vi.stubGlobal('fetch', mockFetch)

    const onChunk = vi.fn()
    const onError = vi.fn()

    await streamInterviewChat('/interview/chat', {}, onChunk, onError)

    expect(onChunk).toHaveBeenCalledTimes(1)
    expect(onChunk).toHaveBeenCalledWith(content)
    expect(onError).not.toHaveBeenCalled()
  })

  /**
   * Test 5: message 块之后有 ping 块 — onChunk 恰好调用一次
   */
  it('Test 5: ping blocks after a message block — onChunk called exactly once', async () => {
    const content = '请介绍一下你自己'
    const sseText =
      buildMessageBlock(content) +
      HEARTBEAT_PING +
      EVENT_PING +
      HEARTBEAT_PING +
      DONE_BLOCK

    const mockFetch = createMockFetch(buildMockReadableStream(sseText))
    vi.stubGlobal('fetch', mockFetch)

    const onChunk = vi.fn()
    const onError = vi.fn()

    await streamInterviewChat('/interview/chat', {}, onChunk, onError)

    expect(onChunk).toHaveBeenCalledTimes(1)
    expect(onChunk).toHaveBeenCalledWith(content)
    expect(onError).not.toHaveBeenCalled()
  })

  // -------------------------------------------------------------------------
  // Property-based tests using fast-check
  // -------------------------------------------------------------------------

  /**
   * Property 5a: 对任意数量的心跳注释 ping，onChunk 永远不被调用
   *
   * **Validates: Requirements 4.5**
   */
  it('Property 5a: arbitrary heartbeat comment pings never trigger onChunk', async () => {
    await fc.assert(
      fc.asyncProperty(
        // 生成 1–10 个心跳注释块
        fc.integer({ min: 1, max: 10 }),
        async (pingCount) => {
          const sseText = HEARTBEAT_PING.repeat(pingCount) + DONE_BLOCK
          const mockFetch = createMockFetch(buildMockReadableStream(sseText))
          vi.stubGlobal('fetch', mockFetch)

          const onChunk = vi.fn()
          const onError = vi.fn()

          await streamInterviewChat('/interview/chat', {}, onChunk, onError)

          expect(onChunk).not.toHaveBeenCalled()
        }
      ),
      { numRuns: 20 }
    )
  })

  /**
   * Property 5b: 对任意数量的 event:ping 块，onChunk 永远不被调用
   *
   * **Validates: Requirements 4.5**
   */
  it('Property 5b: arbitrary event:ping blocks never trigger onChunk', async () => {
    await fc.assert(
      fc.asyncProperty(
        fc.integer({ min: 1, max: 10 }),
        async (pingCount) => {
          const sseText = EVENT_PING.repeat(pingCount) + DONE_BLOCK
          const mockFetch = createMockFetch(buildMockReadableStream(sseText))
          vi.stubGlobal('fetch', mockFetch)

          const onChunk = vi.fn()
          const onError = vi.fn()

          await streamInterviewChat('/interview/chat', {}, onChunk, onError)

          expect(onChunk).not.toHaveBeenCalled()
        }
      ),
      { numRuns: 20 }
    )
  })

  /**
   * Property 5c: 在任意 ping 块与 message 块的混合流中，
   * onChunk 的调用次数恰好等于 message 块的数量，
   * 且每次调用的参数与对应 message 块的 content 一致。
   *
   * **Validates: Requirements 4.5**
   */
  it('Property 5c: mixed ping and message stream — onChunk count equals message count', async () => {
    // 生成合法的 ASCII + CJK 内容字符串（避免空字符串，因为空 content 不触发 onChunk）
    const nonEmptyContent = fc.oneof(
      fc.string({ minLength: 1, maxLength: 30 }).filter(s => s.trim().length > 0),
      fc.constantFrom('你好', '面试开始', '请介绍自己', 'Hello', 'OK', '继续')
    )

    // 生成 ping 类型：0 = 心跳注释，1 = event:ping
    const pingBlock = fc.integer({ min: 0, max: 1 }).map(t =>
      t === 0 ? HEARTBEAT_PING : EVENT_PING
    )

    await fc.assert(
      fc.asyncProperty(
        // 生成 0–5 个 message 内容
        fc.array(nonEmptyContent, { minLength: 0, maxLength: 5 }),
        // 生成 0–5 个 ping 块（穿插在 message 块之间）
        fc.array(pingBlock, { minLength: 0, maxLength: 5 }),
        async (messageContents, pingBlocks) => {
          // 将 ping 块与 message 块交错排列，构造混合流
          const allBlocks = []
          const maxLen = Math.max(messageContents.length, pingBlocks.length)
          for (let i = 0; i < maxLen; i++) {
            if (i < pingBlocks.length) allBlocks.push(pingBlocks[i])
            if (i < messageContents.length) allBlocks.push(buildMessageBlock(messageContents[i]))
          }
          allBlocks.push(DONE_BLOCK)

          const sseText = allBlocks.join('')
          const mockFetch = createMockFetch(buildMockReadableStream(sseText))
          vi.stubGlobal('fetch', mockFetch)

          const onChunk = vi.fn()
          const onError = vi.fn()

          await streamInterviewChat('/interview/chat', {}, onChunk, onError)

          // onChunk 调用次数应等于 message 块数量
          expect(onChunk).toHaveBeenCalledTimes(messageContents.length)

          // 每次调用的参数应与对应 message 内容一致
          messageContents.forEach((content, idx) => {
            expect(onChunk).toHaveBeenNthCalledWith(idx + 1, content)
          })

          // onError 不应被调用
          expect(onError).not.toHaveBeenCalled()
        }
      ),
      { numRuns: 50 }
    )
  })
})
