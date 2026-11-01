# 学マス · 按声优拆分 ICS 日历

此项目**不会抓取 Firestore**。它只读取已有的 `calendar.ics`，从每个事件 `DESCRIPTION` 的 `出演者: ...` 中识别声优，并输出到 `casts/` 子目录。因此不会再次触发先前的 Firebase App Check 问题，也不需要开着电脑。

## 需要上传到原有仓库

仓库：`IvanChan1129/gakumas-calendar-ics`

将压缩包内两个路径上传到 **仓库根目录**，保留目录结构：

- `split_casts.py`
- `.github/workflows/split-casts.yml`

**不要删除或覆盖原来的 `calendar.ics`！** 原文件必须在 `main` 分支根目录下。

> 注意：`.github` 是隐藏文件夹。上传后，GitHub 应显示 `.github/workflows/split-casts.yml`，而不是把 `.github` 放进其他文件夹。

## 首次运行

1. 进入 GitHub 仓库 → `Actions`。
2. 选择 `Split ICS by voice actor` → `Run workflow`。
3. 成功后，会自动提交 `casts/index.html`、`casts/index.json` 和每位声优的 `.ics`。
4. 打开列表页： https://ivanchan1129.github.io/gakumas-calendar-ics/casts/
5. 点击对应声优的「订阅 ICS」，复制 URL，在 Google Calendar 的「其他日历 → 通过网址添加」中使用。

如果工作流因权限失败：仓库 `Settings → Actions → General → Workflow permissions` 选择 `Read and write permissions`，然后重新运行。`split-casts.yml` 自身也声明 `contents: write`。

## 更新规则

- 只要往 GitHub 仓库 **上传新版本 `calendar.ics`**，本工作流就会触发并重新拆分。
- GitHub Actions 也会每天（日本时间约 01:13）从**已上传的 `calendar.ics`** 重新分类，移除过期事项；此任务**不会自动获取原网站新活动**。GitHub 定时任务可能延迟，公开仓库长期不活动时可能被暂停。
- 多位声优出演的节目会同时出现在对应的多个 ICS。
- 没有出演者标签的事项不会被归给任何声优。生日事项如果没有出演者，也不会出现在独立日历中。
- 输出日历筛选今天及未来的事项（日本时间）；包含跨越今天的活动。
- 某声优暂时没有今天及未来的事项时，工具会根据旧 `casts/index.json` 保留同名声优的**空 ICS**，确保已订阅的 URL 不会变成 404。
- `casts/` 目录由程序生成，请不要在里面手动放其它文件。
- 不包含任何 GitHub Token，不需要用户上传 HAR、Cookie 或数据库凭证。

## 本地可选测试

```bash
python split_casts.py --input calendar.ics --output-dir casts
```

仅使用 Python 标准库。源日历的 `DESCRIPTION` 应包含如下格式：

```text
DESCRIPTION:出演者: 花岩香奈、伊藤舞音\n出典: https://gakusei-cheer-portal.web.app/calendar
```

完成后可以打开 `casts/index.html` 查看名单及活动数量。
