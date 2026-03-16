# Highway Rescue Demo（前端救援应用）

该目录是独立于后台管理 Portal 的前端演示应用，模拟“高速事故 -> 无人机/无人狗协同救援”流程。

## 功能
- Mock 事故事件触发
- 侦查无人机、消防无人机、救援无人狗联动
- 地图态势展示（OpenStreetMap + Leaflet）
- 设备状态、事件日志、任务态势实时刷新

## 本地运行
```bash
cd apps/highway-rescue-demo
python3 server.py
```

浏览器访问：
- http://localhost:8000

## API（Mock）
- `GET /api/health`：健康检查
- `GET /api/state`：当前全量态势
- `POST /api/incidents/mock`：触发事故事件
- `POST /api/reset`：重置场景
