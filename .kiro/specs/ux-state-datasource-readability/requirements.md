# Requirements Document

## Introduction

本功能重构（ux-state-datasource-readability）聚焦三大核心问题的系统性解决：

1. **SetupModal 升学模式状态持久化修复**：修复升学模式下 examType、estimatedScore、targetSchool 字段未正确写入 localStorage 的缺陷，并升级侧边栏以动态展示用户模式信息。
2. **Dashboard 数据面板解耦**：将雷达图"数据面板设置"入口与个人信息配置（SetupModal）彻底解耦，引入独立的 DataSourceModal 组件，支持从历史评估记录中切换雷达图数据源。
3. **全局 UI 可读性升级**：将全局最小字号从 9px–11px 提升至 12px（text-xs），并修复深色背景上灰色文字对比度不足的无障碍问题。

整体架构遵循 Pinia Store 作为单一数据源（Single Source of Truth）的原则，localStorage 仅作为持久化层，所有 UI 渲染均从 Store 读取。

## Glossary

- **SetupModal**: 个人信息配置弹窗，用于收集用户姓名、简历、模式偏好及模式相关字段。
- **DataSourceModal**: 新增的独立数据源切换弹窗，用于从历史评估记录中选择雷达图展示数据。
- **UserStore**: Pinia 状态管理 Store（`userStore.js`），作为前端唯一数据源，驱动所有 UI 响应式渲染。
- **LocalStorage**: 浏览器本地持久化层，仅用于跨会话恢复 UserStore 状态。
- **Sidebar**: Dashboard 左侧边栏中的全局资产区域，展示用户模式信息。
- **CyberRadarChart**: 雷达图组件，从 UserStore.radarData 读取数据并渲染。
- **HistoryRecord**: 后端 `/api/history` 返回的历史评估记录，含 `scores` 字段（雷达图评分 JSON）。
- **ValidScores**: 指 `scores` 字段解析后至少包含 1 个维度值大于 0 的记录。
- **activeMode**: 用户当前模式，枚举值为 `'job'`（求职）或 `'education'`（升学）。
- **examType**: 升学模式下的考试类型，枚举值为 `'zhuanchaben'`、`'gaokao'`、`'kaoyan'`、`'kaogong'`、`'other'`。
- **radarData**: UserStore 中的雷达图数据结构，包含 6 个维度的 indicators 和对应 values 数组。
- **Dashboard**: 应用主页面，包含雷达图、功能入口、聊天区域及侧边栏。

## Requirements

### Requirement 1: SetupModal 升学模式字段持久化

**User Story:** As a user in education mode, I want my exam type, estimated score, and target school to be saved when I complete setup, so that my information is preserved across page refreshes.

#### Acceptance Criteria

1. WHEN a user submits SetupModal with activeMode set to 'education', THE SetupModal SHALL write the examType value to localStorage under the key 'exam_type'.
2. WHEN a user submits SetupModal with activeMode set to 'education', THE SetupModal SHALL write the estimatedScore value to localStorage under the key 'estimated_score'.
3. WHEN a user submits SetupModal with activeMode set to 'education', THE SetupModal SHALL write the targetSchool value to localStorage under the key 'target_school'.
4. WHEN a user submits SetupModal with activeMode set to 'education', THE SetupModal SHALL write the value 'education' to localStorage under the key 'active_mode'.
5. WHEN a user submits SetupModal in any mode, THE SetupModal SHALL call userStore.updateUserProfile() with all form fields including mode-specific fields.
6. WHEN a user submits SetupModal with activeMode set to 'job', THE SetupModal SHALL write the targetJob value to localStorage under the key 'target_job'.
7. WHEN a user submits SetupModal with activeMode set to 'job', THE SetupModal SHALL write the jobDescription value to localStorage under the key 'job_description'.
8. IF localStorage write fails due to storage quota or privacy mode, THEN THE SetupModal SHALL continue to update UserStore in memory without throwing an exception.

---

### Requirement 2: SetupModal 字段预填充

**User Story:** As a returning user, I want the setup form to be pre-filled with my previously saved information, so that I don't have to re-enter data I've already provided.

#### Acceptance Criteria

1. WHEN SetupModal is opened, THE SetupModal SHALL read all fields from localStorage and pre-populate the form inputs with the stored values.
2. WHEN SetupModal is opened and localStorage contains 'active_mode' equal to 'education', THE SetupModal SHALL display the education mode tab as active and pre-fill examType, estimatedScore, and targetSchool fields.
3. WHEN SetupModal is opened and localStorage contains 'active_mode' equal to 'job', THE SetupModal SHALL display the job mode tab as active and pre-fill targetJob and jobDescription fields.
4. IF a localStorage key is absent or empty, THEN THE SetupModal SHALL display the corresponding field as empty without error.

---

### Requirement 3: UserStore 作为单一数据源

**User Story:** As a developer, I want all UI components to read state from UserStore rather than directly from localStorage, so that the application has a single source of truth and reactive updates work correctly.

#### Acceptance Criteria

1. THE UserStore SHALL expose the fields candidateName, resumeText, activeMode, targetJob, jobDescription, examType, estimatedScore, targetSchool, radarData, and activeDataSourceId as reactive state.
2. WHEN the application initializes, THE UserStore SHALL load all persisted fields from localStorage to restore the previous session state.
3. THE Sidebar SHALL read activeMode, examType, estimatedScore, targetJob, and resumeText exclusively from UserStore computed properties, not directly from localStorage.
4. THE CyberRadarChart SHALL read radarData exclusively from UserStore.radarData.
5. WHEN UserStore state changes, THE Sidebar SHALL reactively update its displayed content without requiring a page refresh.

---

### Requirement 4: Sidebar 用户模式信息展示

**User Story:** As a user, I want the sidebar to display my current mode and relevant profile information, so that I can quickly see my setup status at a glance.

#### Acceptance Criteria

1. WHILE userStore.activeMode equals 'education', THE Sidebar SHALL display the exam type as a highlighted label badge in the first line of the user info area.
2. WHILE userStore.activeMode equals 'education', THE Sidebar SHALL display the estimatedScore value in the second line of the user info area with the label "分数/排位:".
3. WHILE userStore.activeMode equals 'job', THE Sidebar SHALL display the targetJob value in the user info area.
4. WHILE userStore.activeMode equals 'job' and resumeText is non-empty, THE Sidebar SHALL display a ready status indicator in the user info area.
5. THE Sidebar SHALL map the examType key to a human-readable Chinese label using the mapping: 'zhuanchaben'→'专插本', 'gaokao'→'普通高考', 'kaoyan'→'考研', 'kaogong'→'考公', 'other'→'其他'.
6. IF examType is empty or unrecognized, THEN THE Sidebar SHALL display '未设置' as the exam type label.

---

### Requirement 5: DataSourceModal 新组件

**User Story:** As a user, I want a dedicated modal for switching the radar chart data source, so that I can choose which assessment record to display without affecting my personal profile settings.

#### Acceptance Criteria

1. THE DataSourceModal SHALL accept a `visible` Boolean prop and a `historyRecords` Array prop.
2. THE DataSourceModal SHALL emit a 'close' event when the user dismisses the modal.
3. THE DataSourceModal SHALL emit a 'select' event with the selected HistoryRecord object when the user chooses a data source.
4. WHEN DataSourceModal is rendered, THE DataSourceModal SHALL display only HistoryRecords that have ValidScores (at least one dimension value greater than 0).
5. WHEN DataSourceModal displays a record, THE DataSourceModal SHALL show the record's category label, creation timestamp, and a summary of the user input.
6. WHEN a user selects a record in DataSourceModal, THE DataSourceModal SHALL call userStore.updateRadarData() with the record's parsed scores before emitting 'select'.
7. WHEN a user selects a record in DataSourceModal, THE DataSourceModal SHALL update userStore.activeDataSourceId to the selected record's id.
8. IF no ValidScores records exist in historyRecords, THEN THE DataSourceModal SHALL display an empty state message indicating no data sources are available.
9. IF the scores field of a HistoryRecord is a JSON string, THEN THE DataSourceModal SHALL parse it before processing; IF parsing fails, THEN THE DataSourceModal SHALL exclude that record from the displayed list.

---

### Requirement 6: Dashboard 数据面板入口解耦

**User Story:** As a user, I want the "数据面板设置 >" button to open the data source modal instead of the personal info modal, so that configuring the radar chart is independent from editing my profile.

#### Acceptance Criteria

1. WHEN a user clicks the "数据面板设置 >" button in Dashboard, THE Dashboard SHALL set showDataSourceModal to true.
2. WHEN a user clicks the "数据面板设置 >" button in Dashboard, THE Dashboard SHALL NOT set showSetupModal to true.
3. WHEN DataSourceModal emits a 'select' event, THE Dashboard SHALL set showDataSourceModal to false.
4. WHEN DataSourceModal emits a 'close' event, THE Dashboard SHALL set showDataSourceModal to false.
5. THE Dashboard SHALL pass the historyRecords array to DataSourceModal via the historyRecords prop.

---

### Requirement 7: Dashboard 自动加载最新数据源

**User Story:** As a user, I want the radar chart to automatically display my latest assessment data when I open the Dashboard, so that I see up-to-date information without manual configuration.

#### Acceptance Criteria

1. WHEN Dashboard mounts, THE Dashboard SHALL fetch the most recent HistoryRecord with ValidScores from the backend API endpoint `/api/history`.
2. WHEN Dashboard receives a valid HistoryRecord with ValidScores on mount, THE Dashboard SHALL call userStore.updateRadarData() with the record's scores.
3. WHEN Dashboard receives a valid HistoryRecord with ValidScores on mount, THE Dashboard SHALL set userStore.activeDataSourceId to the record's id.
4. IF no HistoryRecord with ValidScores exists, THEN THE Dashboard SHALL call userStore.resetRadarData() to set all radarData values to 0.
5. IF the history API request fails on mount, THEN THE Dashboard SHALL leave the current radarData state unchanged without displaying an error to the user.

---

### Requirement 8: 有效数据源筛选算法

**User Story:** As a developer, I want a reliable function to determine whether a history record contains valid radar chart scores, so that invalid or empty records are never shown as selectable data sources.

#### Acceptance Criteria

1. THE hasValidScores function SHALL return true when the record's scores field is an object with at least one key whose numeric value is greater than 0.
2. THE hasValidScores function SHALL return false when the record's scores field is null or undefined.
3. THE hasValidScores function SHALL return false when the record's scores field is an empty object.
4. WHEN the record's scores field is a JSON string, THE hasValidScores function SHALL parse it before evaluation; IF parsing fails, THE hasValidScores function SHALL return false.
5. THE hasValidScores function SHALL return false when all dimension values in scores are 0 or non-numeric.
6. THE filterValidDataSources function SHALL return a subset of the input records array where every element satisfies hasValidScores.
7. THE filterValidDataSources function SHALL NOT modify the original input records array.

---

### Requirement 9: UserStore.updateRadarData 值域约束

**User Story:** As a developer, I want radar chart values to always be clamped to the valid range [0, 100], so that the chart never renders with out-of-range data regardless of what the backend returns.

#### Acceptance Criteria

1. WHEN userStore.updateRadarData is called with a scores object, THE UserStore SHALL map each recognized dimension key to its corresponding index in the radarData.values array.
2. WHEN userStore.updateRadarData processes a dimension value, THE UserStore SHALL clamp the value to the range [0, 100] using Math.max(0, Math.min(100, value)).
3. WHEN userStore.updateRadarData encounters an unrecognized dimension key, THE UserStore SHALL leave the corresponding radarData.values entry as 0.
4. WHEN userStore.updateRadarData is called, THE UserStore SHALL NOT modify radarData.indicators.
5. THE UserStore SHALL recognize the following dimension keys: '技术能力', '沟通表达', '项目经验', '学习能力', '团队协作', '职业规划'.
6. WHEN userStore.resetRadarData is called, THE UserStore SHALL set all 6 values in radarData.values to 0.

---

### Requirement 10: Store-localStorage 双向同步

**User Story:** As a user, I want my profile and mode settings to be fully restored after a page refresh, so that I don't lose my configuration between sessions.

#### Acceptance Criteria

1. WHEN the application initializes, THE UserStore SHALL call a loadFromStorage method that reads all persisted keys from localStorage and populates the corresponding state fields.
2. WHEN userStore.updateUserProfile is called, THE UserStore SHALL synchronize all updated fields to localStorage immediately.
3. WHEN a user refreshes the page after completing SetupModal in education mode, THE Sidebar SHALL display the same examType label, estimatedScore, and targetSchool that were entered before the refresh.
4. WHEN a user refreshes the page after completing SetupModal in job mode, THE Sidebar SHALL display the same targetJob and resume status that were present before the refresh.
5. IF localStorage is unavailable during initialization, THEN THE UserStore SHALL initialize all fields to their default empty values without throwing an exception.

---

### Requirement 11: 全局字号下限升级

**User Story:** As a user, I want all text in the application to be at least 12px, so that I can read the interface comfortably without straining my eyes.

#### Acceptance Criteria

1. THE Dashboard SHALL NOT contain any Tailwind class text-[9px], text-[10px], or text-[11px].
2. THE SetupModal SHALL NOT contain any Tailwind class text-[9px], text-[10px], or text-[11px].
3. THE DataSourceModal SHALL NOT contain any Tailwind class text-[9px], text-[10px], or text-[11px].
4. THE Sidebar SHALL NOT contain any Tailwind class text-[9px], text-[10px], or text-[11px].
5. THE Dashboard and all related components SHALL use a minimum font size of text-xs (12px) for all visible text elements.
6. WHEN font size classes are upgraded, THE Dashboard SHALL maintain its cyberpunk dark glassmorphism visual aesthetic without layout overflow or text truncation issues.

---

### Requirement 12: 深色背景文字对比度合规

**User Story:** As a user, I want all readable text on dark backgrounds to have sufficient contrast, so that the interface is accessible and legible for all users.

#### Acceptance Criteria

1. THE Dashboard SHALL NOT use text-gray-600, text-gray-700, text-gray-800, or text-gray-900 for readable text content on dark backgrounds (bg-[#020205] or equivalent dark surfaces).
2. THE SetupModal SHALL NOT use text-gray-600 or darker gray classes for readable text content on dark backgrounds.
3. THE DataSourceModal SHALL NOT use text-gray-600 or darker gray classes for readable text content on dark backgrounds.
4. THE Sidebar SHALL NOT use text-gray-600 or darker gray classes for readable text content on dark backgrounds.
5. WHERE text serves a purely decorative or secondary purpose on dark backgrounds, THE component SHALL use text-gray-500 as the darkest permissible gray.
6. WHERE text serves as primary readable content on dark backgrounds, THE component SHALL use text-gray-400 or lighter.

---

### Requirement 13: DataSourceModal 错误处理

**User Story:** As a user, I want the data source modal to handle API failures gracefully, so that a network error doesn't break the interface or leave me with a broken state.

#### Acceptance Criteria

1. IF the `/api/history` request fails when DataSourceModal loads, THEN THE DataSourceModal SHALL display an empty state indicating no data sources are available.
2. IF a HistoryRecord's scores field cannot be parsed as JSON, THEN THE DataSourceModal SHALL silently exclude that record from the displayed list without showing an error.
3. WHEN DataSourceModal is in an empty state due to no valid records, THE DataSourceModal SHALL remain closeable via the close button or backdrop click.
