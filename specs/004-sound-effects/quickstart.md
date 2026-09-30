# Quickstart: 004-sound-effects（学习音效反馈）

**Date**: 2026-09-30 | **Spec**: [spec.md](./spec.md) | **Plan**: [plan.md](./plan.md) | **Contract**: [contracts/sound-assets.md](./contracts/sound-assets.md)

## 0. 前置

- 后端 venv 已装 `edge-tts`（发音功能已在用），**生成音源时需要联网**（仅生成期）
- 前端依赖已安装（`frontend/node_modules`）
- 起服务：后端 `:8000`、前端 `npm run dev`（`:5173`），或直接用构建产物 `docker compose up --build`

## 1. 生成音源（一次性）

```bash
cd backend
.venv/Scripts/python.exe scripts/generate_sound_assets.py          # 默认音色/语速
# 可选：--voice en-US-GuyNeural --rate +15% --pitch +8Hz
```

预期：`frontend/public/sounds/` 下出现 18 个 mp3 + `manifest.json`，终端打印每条时长与体积。

## 2. 自动化验证

```bash
cd frontend
npm test          # vitest：映射/连对/偏好/播放行为 + 音源资产契约
npm run typecheck # vue-tsc
npm run build     # 构建，确认 dist/sounds/ 含 18 个 mp3
```

## 3. 人工验收（浏览器，音效主观项必须人耳确认）

| # | 场景 | 预期 |
|---|---|---|
| 1 | 首次进入应用，不做任何设置 | **全程无声**（默认关闭） |
| 2 | 设置页打开音效开关 | 开关即时生效，音量默认 70 |
| 3 | 依次进入 首页 / 学习 / 测验 / 错题 / 总结 | 各听到一句对应台词，无串台 |
| 4 | 进入专项练习页（`/review`、`/archive`） | **进入时无声** |
| 5 | 点"开始测验" / "开始专项练习" | 听到 `Come get some!` |
| 6 | 连答对 1→10 题 | 依次 `First blood` … `Deca kill` |
| 7 | 连对第 11、12 题 | 均听到 `Good job` |
| 8 | 中途答错 | 听到 `Storm the front.`，再答对回到 `First blood` |
| 9 | 点"开始"重新一轮 | 答对第一题回到 `First blood` |
| 10 | 快速连点作答 | 不叠加成噪声，最后一次听到的与实际连对数一致 |
| 11 | 正在播放单词发音时答题 | 发音不被打断；本次音效静默跳过 |
| 12 | 刷新页面 / 重开浏览器 | 开关与音量保持上次选择 |
| 13 | 断网（离线）后答题与切页 | 音效照常播放 |
| 14 | 关闭音效后走完整流程 | **0 次发声**，功能不受影响 |
| 15 | 网络面板（音效关闭时） | 无任何 `/sounds/` 请求；开启后才加载 |
| 16 | 首屏对比 | 开启音效前后，首屏可交互时间增加不超过 1 秒 |

## 4. 常见排查

| 现象 | 检查 |
|---|---|
| 全程没声音 | 设置页开关是否开启；浏览器是否静音；是否发生过用户点击（自动播放限制） |
| 只有部分事件有声音 | `manifest.json` 与该事件的 mp3 是否存在且非空（跑 `npm test` 的资产契约） |
| 声音断断续续被吞 | 确认已复用音频预热（首次手势后播放）；检查是否有其他标签页占用输出 |
| 台词想换 | 改映射表文本 → 重跑生成脚本 → 重跑 `npm test`（契约会校验一致性） |

## 5. 部署

音源随 `frontend/dist/sounds/` 一起打包：

- Docker：`docker compose up -d --build`（镜像已含 `frontend/dist`）
- 云服务器：按 002 的打包命令，`frontend/dist` 已在 `deploy.tgz` 内，无需改命令

## 6. 回归提醒

本功能**不改后端、不动数据库**：若验收时发现学习/测验/总结（001/002/003）异常，与本功能无关，先回滚 `.mp3` 与前端改动再定位。
