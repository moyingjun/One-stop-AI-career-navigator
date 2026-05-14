# Requirements Document

## Introduction

本文档定义了"核心业务组件扩容与交互体验(UX)闭环重构"的功能需求。该重构围绕"做减法"的产品理念，解决系统中功能冗余和体验断层问题：废弃冗余的 SavedChats 页面，将收藏功能合并为 HistoryArchive 内的状态过滤器；扩展 SetupModal 支持求职/升学双模式；实现 Dashboard 雷达图动态数据绑定；修复 Agent 对话恢复闭环。

## Glossary

- **Dashboard**: 系统主面板页面，包含聊天区域、雷达图和快捷入口
- **HistoryArchive**: 历史档案页面，展示所有 AI 交互记录并支持过滤
- **SetupModal**: 用户画像采集弹窗，用于收集姓名、简历及模式相关字段
- **SavedChats**: 已废弃的独立收藏页面，功能已合并至 HistoryArchive
- **Segmented_Control**: 分段切换器 UI 组件，用于状态过滤切换
- **userStore**: Pinia 全局状态管理 Store，管理用户画像和雷达图数据
- **radarData**: 雷达图数据结构，包含 6 个维度指标和对应分值
- **chat_history**: 历史记录中存储的对话消息 JSON 数组
- **is_saved**: 历史记录的收藏标记字段（0 或 1）
- **Vue_Router**: Vue.js 路由管理器，处理页面导航和重定向

## Requirements

### Requirement 1: 废弃冗余页面与入口（做减法）

**User Story:** As a 用户, I want 系统移除冗余的"保存的对话"独立页面, so that 我的认知负担降低，收藏功能统一在历史档案中使用。

#### Acceptance Criteria

1. WHEN Dashboard 左侧菜单渲染完成, THE Dashboard SHALL 不显示"保存的对话"菜单入口项
2. WHEN 重构完成后, THE 系统 SHALL 确保 `SavedChats.vue` 文件已从项目中彻底删除
3. WHEN 用户访问旧路由 `/saved-chats`, THE Vue_Router SHALL 自动重定向到 `/history-archive`
4. WHEN 检查路由配置, THE Vue_Router SHALL 不包含 `SavedChats` 组件的导入和独立路由定义，仅保留重定向规则

### Requirement 2: HistoryArchive 状态过滤 UI 重构

**User Story:** As a 用户, I want 在历史档案页面通过状态切换器快速筛选收藏记录, so that 我无需跳转到独立页面即可查看已收藏的对话。

#### Acceptance Criteria

1. WHEN 用户进入历史档案页面且页面加载完成, THE HistoryArchive SHALL 在顶部显示 Segmented_Control，包含"全部记录"和"🌟 仅看收藏"两个选项，默认选中"全部记录"
2. WHEN 用户点击"🌟 仅看收藏"切换器, THE HistoryArchive SHALL 仅显示 `is_saved` 为 true 的记录，且卡片过渡过程有平滑动画
3. WHEN 用户在"仅看收藏"状态下点击"全部记录", THE HistoryArchive SHALL 恢复显示所有记录，卡片补齐有平滑动画
4. WHILE "仅看收藏"选项被选中, THE Segmented_Control SHALL 使用 Purple 主色调及 Cyberpunk Glow 发光特效
5. WHEN 用户组合使用收藏过滤、类型过滤和搜索过滤, THE HistoryArchive SHALL 以 AND 逻辑叠加所有过滤条件，结果为满足所有条件的记录子集
6. WHEN 过滤后无匹配记录, THE HistoryArchive SHALL 显示空状态提示信息

### Requirement 3: SetupModal 多维扩容（Tabbed UI）

**User Story:** As a 用户, I want 在设置弹窗中选择求职或升学模式并填写对应字段, so that 系统能根据我的具体场景提供更精准的 AI 指导。

#### Acceptance Criteria

1. WHEN 用户打开 SetupModal 弹窗且渲染完成, THE SetupModal SHALL 在姓名和简历输入区域下方显示"求职模式"和"升学模式"两个 Tab，默认选中"求职模式"
2. WHILE "求职模式"Tab 被选中, THE SetupModal SHALL 显示"目标岗位"输入框（最大 100 字符）和"岗位描述 JD"文本域（最大 5000 字符）
3. WHILE "升学模式"Tab 被选中, THE SetupModal SHALL 显示"考试类型"下拉选择（专插本/普通高考/考研/考公/其他）、"预估分数/排位"输入框（最大 50 字符）、"意向院校"输入框（最大 200 字符）
4. WHEN 用户在一个 Tab 填写数据后切换到另一个 Tab, THE SetupModal SHALL 保留原 Tab 已填写的数据不被清除
5. WHEN 用户点击"完成设置"且公共字段验证通过, THE SetupModal SHALL 将所有已填写字段写入 localStorage 和 Pinia userStore
6. WHEN SetupModal 渲染完成, THE SetupModal SHALL 严格采用现有的暗黑赛博朋克加毛玻璃风格
7. IF 用户未填写姓名或简历不足 20 字符, THEN THE SetupModal SHALL 显示对应字段的错误提示且不执行数据保存

### Requirement 4: Dashboard 雷达图动态化

**User Story:** As a 用户, I want Dashboard 雷达图展示我的真实评估数据, so that 我能直观了解自己各维度的能力水平。

#### Acceptance Criteria

1. WHEN 用户首次登录或无任何评估历史记录且 Dashboard 加载完成, THE Dashboard SHALL 将雷达图各项指标值设为 0，呈现空状态视觉
2. WHEN 用户已有简历诊断评估记录且 Dashboard 加载完成, THE Dashboard SHALL 从 Pinia userStore 中读取最新评估结果的 scores 字段动态渲染雷达图
3. THE userStore SHALL 确保 radarData.values 数组长度恒为 6，每项值在 0 到 100 范围内
4. WHEN 重构完成后, THE Dashboard SHALL 将 Bento 面板右上角原"历史档案"链接更名或移除，消除与左侧菜单"历史记录"的功能重叠
5. IF 雷达图数据加载 API 请求失败, THEN THE Dashboard SHALL 保持当前 radarData 状态不变且将错误静默记录到 console

### Requirement 5: Agent 对话恢复闭环

**User Story:** As a 用户, I want 从历史档案中点击 Agent 对话记录即可恢复对话上下文继续聊天, so that 我无需重新描述问题即可延续之前的对话。

#### Acceptance Criteria

1. WHEN 用户点击 category 为 `agent_*` 或 `general_chat` 的记录卡片, THE HistoryArchive SHALL 路由跳转到 `/dashboard?chat_id={record.id}`
2. WHEN Dashboard 接收到路由参数 `chat_id`, THE Dashboard SHALL 自动调用 API 获取该记录的 `chat_history` 字段并将解析后的消息数组赋值给 chatMessages
3. WHEN `chat_history` 为有效的 JSON 数组且解析完成, THE Dashboard SHALL 确保 chatMessages 中每条消息的 role 仅为 user 或 ai，content 为非空字符串
4. IF `chat_history` 为空数组或解析失败, THEN THE Dashboard SHALL 从 `user_input` 和 `ai_result` 字段构建最小上下文（至少包含 1 到 2 条消息）
5. WHEN 对话上下文恢复完成且用户发送新消息, THE Dashboard SHALL 携带已恢复的历史上下文一并发送给后端 Agent API 实现无缝续接
6. WHEN 用户在任何过滤状态下点击 Agent 对话卡片, THE HistoryArchive SHALL 正常触发对话恢复流程，行为一致
7. IF `chat_id` 对应的记录不存在（API 返回 404）, THEN THE Dashboard SHALL 将 chatMessages 置为空数组，用户看到空聊天界面并可正常开始新对话
