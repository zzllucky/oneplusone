# Research: 004-sound-effects（学习音效反馈）

**Date**: 2026-09-30 | **Spec**: [spec.md](./spec.md)

> 目标：把规范里"用什么技术、怎么放、怎么播"的实现级决策定下来（规范只写了 what/why）。

## R-001 音源怎么来：构建期预生成 mp3，而不是运行时合成

- **Decision**：用一次性脚本调用项目已有的 TTS 引擎（edge-tts）把 18 条英文短句**预先合成成 mp3 文件**，随代码一起进仓库与构建产物；运行时只做"播放文件"，不合成。
- **Rationale**：
  - 离线可用（FR-022）、不向第三方请求（FR-022 / SC-010）——运行时合成必然要访问 TTS 服务
  - 点击到出声 ≤150ms（SC-004）——运行时合成要等网络往返
  - 音色稳定可控，"高昂激情"只需在生成时调一次参数，不依赖用户设备的语音合成能力
- **Alternatives considered**：
  1. **运行时调后端 TTS**：增加请求、有延迟、断网即失效 → 否决
  2. **浏览器语音合成（speechSynthesis）**：音色随设备/浏览器漂移，iOS 限制多，且词库朗读已有此降级路径 → 否决（仅在音源缺失时作为兜底，见 R-013）
  3. **第三方音效素材站 / 游戏语音包**：版权与合规风险 → 否决（FR-020 明令禁止）
- **探测结论（2026-09-30 实跑）**：`edge-tts` + `en-US-GuyNeural`、`rate=+15%`、`pitch=+8Hz` 合成 `Fire in the hole!` 成功，产物 **10.9 KB**；按 18 条估算总计约 150–200 KB，在预算内（R-012）

## R-002 音源放哪：`frontend/public/sounds/`，随构建产物走

- **Decision**：mp3 放在 `frontend/public/sounds/`，Vite 构建时原样复制到 `dist/sounds/`；后端静态托管 `dist`，Docker 镜像与 `deploy.tgz` 均自动包含，无需改 Dockerfile 与打包命令。
- **Rationale**：文件名稳定可读（便于逐条替换台词，FR-028）；不需要 import，运行时按路径直接取；不进 JS bundle，不占首屏（SC-009）。
- **Alternatives considered**：
  1. `src/assets/` + import：产物带 hash 文件名，替换台词要改代码 → 否决
  2. 放后端 `/static`：要改静态目录与部署配置 → 否决（更复杂）

## R-003 怎么播：单例播放器 + 覆盖播放，与发音播放器分离

- **Decision**：音效使用**一个独立的 `HTMLAudioElement` 单例**；每次播放先 `pause()` → 换 `src` → `play()`，即"后播覆盖先播"。
- **Rationale**：自然满足 FR-018（快速连答不排队、不叠加）；单例避免多实例被浏览器并发策略截断。
- **Alternatives considered**：
  1. **Web Audio API**：可做音量包络与精确调度，但需解码/缓存管理，对"播一个短文件"是过度设计 → 否决（constitution V 简洁 / YAGNI）
  2. **多实例并发**：直接违反不叠加要求 → 否决

## R-004 发音优先怎么实现：播放前查询发音播放器状态

- **Decision**：`useAudioWarmup.ts` 已有全局共享的发音播放器；新增一个导出用于查询"是否正在发音"，音效播放前若为真则**跳过本次**（FR-026：不打断、不补播）。
- **Rationale**：改动最小、职责清晰；不需要在音效模块里反向依赖发音组件。

## R-005 自动播放限制：复用既有预热 + 默认关闭

- **Decision**：沿用现有 `registerAudioWarmup()`（首次 pointerdown/touchstart/keydown 预热解码链路）；音效**默认关闭**，用户开启开关这一动作本身就是用户手势，之后所有播放都在手势链之后的页面生命周期内，天然满足浏览器策略。未交互时静默跳过（FR-016）。

## R-006 偏好存哪：localStorage，不进账号

- **Decision**：`localStorage['word-study-sound-prefs'] = { enabled: false, volume: 70 }`，默认 `enabled=false`、`volume=70`。
- **Rationale**：FR-024 明确不得写入账号；也规避未成年人信息新增字段的合规审查（FR-018 精神）。
- **Alternatives considered**：后端设置项 → 需新增字段 + 合规审查 + 跨设备同步（规范已明确不需要）→ 否决

## R-007 连对计数放哪：音效模块内的会话级计数器

- **Decision**：计数保存在音效模块内部（模块级单例），生命周期 = 一次测验流程；`start()` 与答错都归零（FR-003 / FR-004）。
- **Rationale**：不跨测验、不跨会话、不入库，无需 Pinia store；三个测验页各自调用同一模块即可。

## R-008 页面进入语音在哪接：路由白名单 + 全局钩子

- **Decision**：在路由层集中触发（进入路由后按路径播放），白名单仅含 `/home`、`/study`、`/quiz`、`/wrong-words`、`/summary` 五个页面；`/review`、`/archive` 不在白名单（FR-011）。
- **Rationale**：一处接入、一处测试，避免 5 个页面各写一段重复代码；新增/剔除页面只改白名单。

## R-009 模块怎么切：两个文件，自包含

- **Decision**：新建自包含模块 `frontend/src/sounds/`：
  - `events.ts`：事件 ↔ 台词 ↔ 音源文件的映射表（台词替换只改这里，FR-028）
  - `soundEffects.ts`：播放（含覆盖、音量、发音优先判断）、连对计数、偏好读写
- **Rationale**：符合 constitution I（自包含、单一职责、自带测试与用途说明）。
- **Alternatives considered**：
  1. 全部塞进 `composables/useSoundEffects.ts` 一个文件：映射与播放混在一起，替换台词要动逻辑 → 否决
  2. 拆成 5 个文件（player/preferences/streak/events/index）：为整理目录而拆分 → 否决（constitution I 明确禁止）

## R-010 测试策略：前端单测 + 资产校验 + 人工听感验收

- **Decision**：
  1. **单元测试（vitest + jsdom，已有）**：映射完整性、连对计数与复位、偏好默认值与持久化、播放行为（覆盖、关闭时静音、发音中跳过）——播放用 mock 的 Audio，不真出声
  2. **资产契约测试**：读取 `manifest.json`，校验 18 个事件齐全、文件存在、单条时长 ≤2s（SC 与 FR-021）
  3. **人工验收**：浏览器实测听感与时序，见 `quickstart.md`
- **Rationale**：constitution III（测试先行）与 IV（接缝覆盖）；音效的"好不好听、及不及时"只能人工判定，不假装自动化。

## R-011 音量：0–100 滑块，默认 70

- **Decision**：设置页提供 0–100 的音量滑块（步进 10，默认 70），播放时映射为播放器音量 `volume/100`。
- **Rationale**：比离散档位更细，实现成本相同；默认 70 留出调高空间且不过吵。

## R-012 体积与性能预算

- **Decision**：单条 ≤2 秒、单文件 ≤30 KB、18 条总计 ≤300 KB；音源 `preload='none'` 且不预取，**仅在音效开启后才可能加载**，不计入首屏（SC-008 / SC-009）。
- **Rationale**：默认关闭的前提下，绝大多数用户永远不会下载音源文件，首屏零影响。

## R-013 降级：音源缺失时静默跳过

- **Decision**：播放失败（文件 404、解码失败、被浏览器拒绝）一律 `catch` 后静默跳过，仅写一条 `console.warn` 便于排查；不弹窗、不阻断流程（FR-027）。不回退到浏览器语音合成——避免音色漂移与"有的词有音效有的没音效"的不一致体验。

## R-014 无新增依赖

- **Decision**：前端零新增 npm 依赖（用原生 `HTMLAudioElement` + localStorage）；音源生成用后端**已有**的 edge-tts。符合 constitution「能用标准库解决的 MUST NOT 引入依赖」。
