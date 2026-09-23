# Codex Reset 日历

将 [codex-reset.com](https://codex-reset.com/) 的已确认
Codex Reset 和未来预测转换成可订阅的 iCalendar。

## 数据来源

使用两个公开接口：

```text
/api/timeline?locale=zh&group=reset&limit=50
/api/forecast?locale=zh&tz=Asia/Shanghai
```

两个接口均使用中文数据。

## 日历事件

### 已确认 Reset

来自 Timeline。

只有同时满足：

```text
group = reset
announcement_state = announced
```

才认为是真正已经确认的 Reset。

日历标题：

```text
Codex Reset
```

### Reset 预测

来自 Forecast。

预测事件标题：

```text
[预测] Codex Reset
```

`[预测]` 表示该事件尚未得到 Timeline 确认，
并不代表 Reset 一定会发生。

程序不会仅根据“24 小时概率”或“48 小时概率”
自行推测一个具体时间。

只有 Forecast 中存在具体的预测目标时间或窗口时间时，
才会生成预测日历事件。

## 自动更新

GitHub Actions 每小时运行一次：

```text
Codex Reset API
       ↓
   generate.py
       ↓
docs/calendar.ics
       ↓
  GitHub Pages
       ↓
 Apple Calendar
```

如果生成的 ICS 没有变化，不会产生新的 Git commit。

## GitHub Pages

仓库上传完成后进入：

```text
Settings
→ Pages
→ Build and deployment
→ Deploy from a branch
```

选择：

```text
Branch: main
Folder: /docs
```

发布完成后访问：

```text
https://<username>.github.io/<repository>/
```

页面中的“添加到日历”按钮会自动生成正确的
`webcal://` 订阅地址，不需要修改用户名。

也可以直接订阅：

```text
https://<username>.github.io/<repository>/calendar.ics
```

## 手动更新

GitHub：

```text
Actions
→ Update calendar
→ Run workflow
```

也可以在本地执行：

```bash
python generate.py
```

项目只使用 Python 标准库，不需要安装第三方依赖。

## Attribution

Data: [codex-reset.com](https://codex-reset.com/)

本项目不是 OpenAI 或 codex-reset.com 的官方项目。
