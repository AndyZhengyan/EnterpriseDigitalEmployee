# 提交前代码同步与冲突处理流程

> 目标：在提交前先拉取最新代码，避免集成冲突。

## 1. 拉取最新代码
```bash
git fetch origin
git pull --rebase origin <your-branch>
```

## 2. 发生冲突时处理
1. 使用 `git status` 查看冲突文件。
2. 打开冲突文件，处理 `<<<<<<<`, `=======`, `>>>>>>>` 标记。
3. 处理完成后执行：
```bash
git add <resolved-files>
git rebase --continue
```
4. 若需要放弃本次 rebase：
```bash
git rebase --abort
```

## 3. 重新验证并提交
```bash
git status
# 运行测试/检查
# git commit -m "..."
```

## 4. 推送
```bash
git push origin <your-branch>
```

---

## 当前仓库说明
当前本地仓库未配置 `origin` 远程与 tracking 分支时，`git pull --rebase` 会失败。
请先配置远程仓库并设置 upstream 后再执行上述流程。
