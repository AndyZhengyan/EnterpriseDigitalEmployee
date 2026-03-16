# Highway Rescue Demo（前端救援应用）

该目录是独立于后台管理 Portal 的前端演示应用，模拟“高速事故 -> 无人机/无人狗协同救援”流程。

## 技术选型
- **Vue 3（ESM 直连）**：提供组件化状态管理与更稳定的交互组织，避免纯 HTML 脚本膨胀
- **Leaflet + OpenStreetMap**：承载地理态势与设备标绘
- **Cyber HUD 视觉层**：以 Gotham 风格为参考，构建偏游戏化的作战大屏
## 页面入口（GitHub Pages）
- `index.html`：站点导航页（统一入口）
- `adminconsole/index.html`：AdminConsole 管理页面
- `demo/index.html`：高速事故救援 Demo 页面
- 兼容入口：`admin-config.html` 与 `highway-demo.html` 会自动重定向到新目录

## 功能
- Mock 事故事件触发
- 侦查无人机、消防无人机、救援无人狗联动
- 地图态势展示（OpenStreetMap + Leaflet）
- 设备状态、事件日志、任务态势实时刷新
- **双模式运行**：
  - 本地 API 模式（连接 `server.py`）
  - 浏览器内置 Mock 模式（适配 GitHub Pages）

## 本地运行（API 模式）
```bash
cd apps/highway-rescue-demo
python3 server.py
```

浏览器访问：
- http://localhost:8000/（导航页）
- http://localhost:8000/demo/（高速事故 Demo）
- http://localhost:8000/adminconsole/（AdminConsole）

## GitHub Pages 部署
本仓库已提供自动部署工作流：
- `.github/workflows/deploy-highway-demo-pages.yml`

启用方式：
1. 在 GitHub 仓库 Settings -> Pages 中将 Source 设为 **GitHub Actions**。
2. 合并包含该工作流的分支。
3. 手动触发 workflow（或推送 `apps/highway-rescue-demo/static/` 变更）后自动发布。

> 在 GitHub Pages 环境下，`highway-demo.html` 会自动切换到“浏览器 Mock 模式”，无需后端服务即可演示完整流程。

## API（Mock，server.py 提供）
- `GET /api/health`：健康检查
- `GET /api/state`：当前全量态势
- `POST /api/incidents/mock`：触发事故事件
- `POST /api/reset`：重置场景
