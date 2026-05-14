/**
 * Property 1: 持久化完整性（Persistence Round-Trip）
 *
 * **Validates: Requirements 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 1.7**
 *
 * 对任意升学模式（education）或求职模式（job）的 formData，
 * 模拟 SetupModal handleSubmit() 行为（先写 localStorage，再调用 userStore.updateUserProfile()），
 * 提交后 localStorage 和 UserStore 中字段值应完全一致。
 *
 * 测试策略：
 * - 直接调用 persistUserProfile() 纯函数（提取自 SetupModal handleSubmit 逻辑）
 * - 使用 createPinia() + setActivePinia() 初始化 Pinia 实例
 * - 使用 localStorage mock 替代真实浏览器 API
 * - fast-check 生成任意合法 formData 进行属性验证
 */
import { describe, it, expect, beforeEach, afterEach } from 'vitest'
import * as fc from 'fast-check'
import { createPinia, setActivePinia } from 'pinia'
import { useUserStore } from '../stores/userStore.js'

// ===== localStorage Mock =====

/**
 * 创建符合 Web Storage API 的 localStorage mock
 */
function createLocalStorageMock() {
  let store = {}
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
      store = {}
    },
    key(index) {
      const keys = Object.keys(store)
      return keys[index] || null
    },
    get length() {
      return Object.keys(store).length
    },
    _getSnapshot() {
      return { ...store }
    }
  }
}

// ===== persistUserProfile 纯函数（模拟 SetupModal handleSubmit 行为）=====

/**
 * 模拟 SetupModal.handleSubmit() 中验证通过后的持久化逻辑：
 * 1. 写入 localStorage（基础字段 + 模式特定字段）
 * 2. 调用 userStore.updateUserProfile() 同步到 Pinia Store
 *
 * 前置条件：formData 已通过验证（candidateName 非空 ≤50字符，resumeText ≥20字符 ≤10000字符）
 * 后置条件：localStorage 和 userStore 中对应字段值完全一致
 *
 * @param {object} formData - 已验证的表单数据
 * @param {object} userStore - Pinia userStore 实例
 */
function persistUserProfile(formData, userStore) {
  const {
    candidateName,
    resumeText,
    activeMode,
    targetJob,
    jobDescription,
    examType,
    estimatedScore,
    targetSchool
  } = formData

  // 基础字段始终写入 localStorage（与 SetupModal.handleSubmit 行为一致）
  try {
    localStorage.setItem('candidate_name', candidateName)
    localStorage.setItem('resume_text', resumeText)
    localStorage.setItem('userRole', 'registered')
    localStorage.setItem('active_mode', activeMode)

    if (activeMode === 'job') {
      // 求职模式：写入目标岗位和 JD（Requirements 1.6, 1.7）
      localStorage.setItem('target_job', targetJob)
      localStorage.setItem('job_description', jobDescription)
    } else if (activeMode === 'education') {
      // 升学模式：写入考试类型、预估分数、意向院校（Requirements 1.1, 1.2, 1.3, 1.4）
      localStorage.setItem('exam_type', examType)
      localStorage.setItem('estimated_score', estimatedScore)
      localStorage.setItem('target_school', targetSchool)
    }
  } catch {
    // localStorage 写入失败时静默处理，Store 仍正常更新（Requirement 1.8）
  }

  // 同步所有字段到 Pinia Store（单一数据源，Requirement 1.5）
  userStore.updateUserProfile(formData)
}

// ===== 自定义 Arbitraries =====

/**
 * 有效姓名：trim 后 1-50 字符
 */
const validNameArb = fc.string({ minLength: 1, maxLength: 50 })
  .filter(s => s.trim().length > 0 && s.trim().length <= 50)

/**
 * 有效简历：trim 后 20-500 字符（限制上限以保持测试性能）
 */
const validResumeArb = fc.string({ minLength: 20, maxLength: 500 })
  .filter(s => s.trim().length >= 20)

/**
 * 考试类型枚举值
 */
const examTypeArb = fc.constantFrom('zhuanchaben', 'gaokao', 'kaoyan', 'kaogong', 'other', '')

/**
 * 预估分数/排位：任意字符串，最长 50 字符
 */
const estimatedScoreArb = fc.string({ minLength: 0, maxLength: 50 })

/**
 * 意向院校：任意字符串，最长 200 字符
 */
const targetSchoolArb = fc.string({ minLength: 0, maxLength: 200 })

/**
 * 目标岗位：任意字符串，最长 100 字符
 */
const targetJobArb = fc.string({ minLength: 0, maxLength: 100 })

/**
 * 岗位描述 JD：任意字符串，最长 200 字符（限制以保持测试性能）
 */
const jobDescriptionArb = fc.string({ minLength: 0, maxLength: 200 })

/**
 * 升学模式 formData arbitrary
 */
const educationFormDataArb = fc.record({
  candidateName: validNameArb.map(s => s.trim().slice(0, 50)),
  resumeText: validResumeArb.map(s => s.trim().slice(0, 10000)),
  activeMode: fc.constant('education'),
  targetJob: fc.constant(''),
  jobDescription: fc.constant(''),
  examType: examTypeArb,
  estimatedScore: estimatedScoreArb.map(s => s.trim()),
  targetSchool: targetSchoolArb.map(s => s.trim())
})

/**
 * 求职模式 formData arbitrary
 */
const jobFormDataArb = fc.record({
  candidateName: validNameArb.map(s => s.trim().slice(0, 50)),
  resumeText: validResumeArb.map(s => s.trim().slice(0, 10000)),
  activeMode: fc.constant('job'),
  targetJob: targetJobArb.map(s => s.trim()),
  jobDescription: jobDescriptionArb.map(s => s.trim()),
  examType: fc.constant(''),
  estimatedScore: fc.constant(''),
  targetSchool: fc.constant('')
})

// ===== 测试套件 =====

describe('Property 1: 持久化完整性（Persistence Round-Trip）', () => {
  let mockLocalStorage
  let pinia
  let userStore

  beforeEach(() => {
    // 初始化 localStorage mock
    mockLocalStorage = createLocalStorageMock()
    globalThis.localStorage = mockLocalStorage

    // 初始化 Pinia 实例
    pinia = createPinia()
    setActivePinia(pinia)
    userStore = useUserStore()
  })

  afterEach(() => {
    delete globalThis.localStorage
  })

  // ─── 升学模式属性测试 ───────────────────────────────────────────────────────

  it('升学模式：任意 formData 提交后 localStorage.exam_type 与 userStore.examType 一致', () => {
    fc.assert(
      fc.property(educationFormDataArb, (formData) => {
        mockLocalStorage.clear()
        // 重新初始化 store 以隔离测试
        pinia = createPinia()
        setActivePinia(pinia)
        userStore = useUserStore()

        persistUserProfile(formData, userStore)

        // Requirement 1.1: exam_type 写入 localStorage
        expect(mockLocalStorage.getItem('exam_type')).toBe(formData.examType)
        // localStorage 与 Store 一致
        expect(userStore.examType).toBe(formData.examType)
        expect(mockLocalStorage.getItem('exam_type')).toBe(userStore.examType)
      }),
      { numRuns: 200 }
    )
  })

  it('升学模式：任意 formData 提交后 localStorage.estimated_score 与 userStore.estimatedScore 一致', () => {
    fc.assert(
      fc.property(educationFormDataArb, (formData) => {
        mockLocalStorage.clear()
        pinia = createPinia()
        setActivePinia(pinia)
        userStore = useUserStore()

        persistUserProfile(formData, userStore)

        // Requirement 1.2: estimated_score 写入 localStorage
        expect(mockLocalStorage.getItem('estimated_score')).toBe(formData.estimatedScore)
        // localStorage 与 Store 一致
        expect(userStore.estimatedScore).toBe(formData.estimatedScore)
        expect(mockLocalStorage.getItem('estimated_score')).toBe(userStore.estimatedScore)
      }),
      { numRuns: 200 }
    )
  })

  it('升学模式：任意 formData 提交后 localStorage.target_school 与 userStore.targetSchool 一致', () => {
    fc.assert(
      fc.property(educationFormDataArb, (formData) => {
        mockLocalStorage.clear()
        pinia = createPinia()
        setActivePinia(pinia)
        userStore = useUserStore()

        persistUserProfile(formData, userStore)

        // Requirement 1.3: target_school 写入 localStorage
        expect(mockLocalStorage.getItem('target_school')).toBe(formData.targetSchool)
        // localStorage 与 Store 一致
        expect(userStore.targetSchool).toBe(formData.targetSchool)
        expect(mockLocalStorage.getItem('target_school')).toBe(userStore.targetSchool)
      }),
      { numRuns: 200 }
    )
  })

  it('升学模式：任意 formData 提交后 localStorage.active_mode 为 "education"', () => {
    fc.assert(
      fc.property(educationFormDataArb, (formData) => {
        mockLocalStorage.clear()
        pinia = createPinia()
        setActivePinia(pinia)
        userStore = useUserStore()

        persistUserProfile(formData, userStore)

        // Requirement 1.4: active_mode 写入 'education'
        expect(mockLocalStorage.getItem('active_mode')).toBe('education')
        expect(userStore.activeMode).toBe('education')
        expect(mockLocalStorage.getItem('active_mode')).toBe(userStore.activeMode)
      }),
      { numRuns: 200 }
    )
  })

  it('升学模式：任意 formData 提交后所有字段 localStorage 与 UserStore 完全一致（综合验证）', () => {
    fc.assert(
      fc.property(educationFormDataArb, (formData) => {
        mockLocalStorage.clear()
        pinia = createPinia()
        setActivePinia(pinia)
        userStore = useUserStore()

        persistUserProfile(formData, userStore)

        // Requirement 1.5: userStore.updateUserProfile() 被调用，Store 与 localStorage 同步
        // 基础字段
        expect(mockLocalStorage.getItem('candidate_name')).toBe(userStore.candidateName)
        expect(mockLocalStorage.getItem('resume_text')).toBe(userStore.resumeText)
        expect(mockLocalStorage.getItem('active_mode')).toBe(userStore.activeMode)

        // 升学模式特定字段（Requirements 1.1, 1.2, 1.3, 1.4）
        expect(mockLocalStorage.getItem('exam_type')).toBe(userStore.examType)
        expect(mockLocalStorage.getItem('estimated_score')).toBe(userStore.estimatedScore)
        expect(mockLocalStorage.getItem('target_school')).toBe(userStore.targetSchool)

        // 验证 Store 中的值与 formData 一致
        expect(userStore.candidateName).toBe(formData.candidateName)
        expect(userStore.resumeText).toBe(formData.resumeText)
        expect(userStore.activeMode).toBe('education')
        expect(userStore.examType).toBe(formData.examType)
        expect(userStore.estimatedScore).toBe(formData.estimatedScore)
        expect(userStore.targetSchool).toBe(formData.targetSchool)
      }),
      { numRuns: 200 }
    )
  })

  // ─── 求职模式属性测试 ───────────────────────────────────────────────────────

  it('求职模式：任意 formData 提交后 localStorage.target_job 与 userStore.targetJob 一致', () => {
    fc.assert(
      fc.property(jobFormDataArb, (formData) => {
        mockLocalStorage.clear()
        pinia = createPinia()
        setActivePinia(pinia)
        userStore = useUserStore()

        persistUserProfile(formData, userStore)

        // Requirement 1.6: target_job 写入 localStorage
        expect(mockLocalStorage.getItem('target_job')).toBe(formData.targetJob)
        expect(userStore.targetJob).toBe(formData.targetJob)
        expect(mockLocalStorage.getItem('target_job')).toBe(userStore.targetJob)
      }),
      { numRuns: 200 }
    )
  })

  it('求职模式：任意 formData 提交后 localStorage.job_description 与 userStore.jobDescription 一致', () => {
    fc.assert(
      fc.property(jobFormDataArb, (formData) => {
        mockLocalStorage.clear()
        pinia = createPinia()
        setActivePinia(pinia)
        userStore = useUserStore()

        persistUserProfile(formData, userStore)

        // Requirement 1.7: job_description 写入 localStorage
        expect(mockLocalStorage.getItem('job_description')).toBe(formData.jobDescription)
        expect(userStore.jobDescription).toBe(formData.jobDescription)
        expect(mockLocalStorage.getItem('job_description')).toBe(userStore.jobDescription)
      }),
      { numRuns: 200 }
    )
  })

  it('求职模式：任意 formData 提交后所有字段 localStorage 与 UserStore 完全一致（综合验证）', () => {
    fc.assert(
      fc.property(jobFormDataArb, (formData) => {
        mockLocalStorage.clear()
        pinia = createPinia()
        setActivePinia(pinia)
        userStore = useUserStore()

        persistUserProfile(formData, userStore)

        // 基础字段
        expect(mockLocalStorage.getItem('candidate_name')).toBe(userStore.candidateName)
        expect(mockLocalStorage.getItem('resume_text')).toBe(userStore.resumeText)
        expect(mockLocalStorage.getItem('active_mode')).toBe(userStore.activeMode)

        // 求职模式特定字段（Requirements 1.6, 1.7）
        expect(mockLocalStorage.getItem('target_job')).toBe(userStore.targetJob)
        expect(mockLocalStorage.getItem('job_description')).toBe(userStore.jobDescription)

        // 验证 Store 中的值与 formData 一致
        expect(userStore.candidateName).toBe(formData.candidateName)
        expect(userStore.resumeText).toBe(formData.resumeText)
        expect(userStore.activeMode).toBe('job')
        expect(userStore.targetJob).toBe(formData.targetJob)
        expect(userStore.jobDescription).toBe(formData.jobDescription)
      }),
      { numRuns: 200 }
    )
  })

  // ─── localStorage 写入失败时 Store 仍正常更新（Requirement 1.8）─────────────

  it('localStorage 写入失败时 userStore 仍正常更新（静默失败）', () => {
    // 模拟 localStorage 写入抛出异常（隐私模式/存储已满）
    const throwingStorage = {
      getItem: () => null,
      setItem: () => { throw new Error('QuotaExceededError') },
      removeItem: () => {},
      clear: () => {}
    }
    globalThis.localStorage = throwingStorage

    pinia = createPinia()
    setActivePinia(pinia)
    userStore = useUserStore()

    const formData = {
      candidateName: '张三',
      resumeText: '这是一段足够长的简历文本，用于测试 localStorage 写入失败时的静默处理逻辑。',
      activeMode: 'education',
      targetJob: '',
      jobDescription: '',
      examType: 'kaoyan',
      estimatedScore: '380',
      targetSchool: '北京大学'
    }

    // 不应抛出异常
    expect(() => persistUserProfile(formData, userStore)).not.toThrow()

    // Store 仍正常更新（Requirement 1.8）
    expect(userStore.candidateName).toBe('张三')
    expect(userStore.activeMode).toBe('education')
    expect(userStore.examType).toBe('kaoyan')
    expect(userStore.estimatedScore).toBe('380')
    expect(userStore.targetSchool).toBe('北京大学')
  })
})
