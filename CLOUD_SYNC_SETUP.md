# 云端同步测试版

这是待 GitHub Actions 联网验证的修改版，不代表已解决 Firestore 拒绝访问。

## 更新方法

将本包文件按原路径替换到 IvanChan1129/gakumas-calendar-ics 的 main 分支。
不要删除 calendar.ics、casts、split_casts.py、requirements.txt 或其他原文件。
GitHub 隐藏目录必须是 .github/workflows/，不要把整个压缩包直接上传。

然后打开仓库 Settings → Pages，将 Build and deployment → Source 改为 GitHub Actions。
这是本版显式发布日历所需的设置。原有订阅网址不变。
进入 Actions → Refresh ICS subscription → Run workflow → main。
首次启动后可以关机，执行在 GitHub 服务器上。后续约每三小时自动运行，定时任务可能延迟。

## 如何判断结果

只有 Fetch、Split、Publish 都成功才算更新完成。
Stage 1 报错：正常网页首次读取就失败，需要检查云端访问条件，不能靠放宽 GitHub 权限解决。
Stage 1 成功但 Stage 2 报错：日志会标出失败月份。
Website module export changed：网站前端导出发生变化，需调整读取代码。
Configure/Publish 失败：检查 Pages Source 是否选择 GitHub Actions。
抓取失败时不会提交或发布新的日历。最后成功发布的版本保持可用。

本版将旧的 Split ICS by voice actor 手动入口改为调用完整刷新流程，取消旧的独立定时分类，防止发布过期源文件。

## 修改内容与限制

不再改写网站 JavaScript；等待网页自身服务器读取成功后，复用原模块的日程状态。
从上个月开始逐月查询未来18个月，包含网页初始窗口；并非无限远的全部日程。
沿用现有导出日历的文档ID作为 UID，减少事件身份变化。
抓取、分类、保存源文件、Pages发布放在一条工作流中，不依赖机器人提交触发其他工作流。
旧声优清单随源文件提交保留。读取为空、权限错误或数量大幅下降时停止。
仍依赖原站前端模块名称及日志；网站改版可能需要维护。
Google Calendar 的订阅刷新时间由 Google 决定，不等于任务执行间隔。

本地6项转换/分类测试通过。本环境下载Chromium失败，尚未完成联网抓取或GitHub部署测试。
