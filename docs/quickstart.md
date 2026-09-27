# 快速开始

## 1. 运行测试

```powershell
python -m unittest discover -s tests -v
```

## 2. 初始化本地私有数据

```powershell
python -m dating_agent --data-dir private init
```

## 3. 匹配后才建代号个案

```powershell
python -m dating_agent --data-dir private new-case --alias Q001
```

代号只能使用字母、数字、下划线和连字符，不写昵称或姓名。

## 4. 记录去标识摘要

```powershell
python -m dating_agent --data-dir private log --case Q001 --type message_exchange --summary "双方都围绕共同兴趣分享并提问" --reciprocity 4 --comfort 4 --boundary-respect 5
```

不要写原话、手机号、微信、邮箱、网址或长编号。

## 5. 手工推进阶段

```powershell
python -m dating_agent --data-dir private advance --case Q001 --to conversing
python -m dating_agent --data-dir private advance --case Q001 --to date_planned --mutual-yes --public-plan
python -m dating_agent --data-dir private log --case Q001 --type date_completed --summary "在公开场所完成约 80 分钟见面，双方各自返程" --reciprocity 4 --comfort 4 --boundary-respect 5 --reliability 4
python -m dating_agent --data-dir private advance --case Q001 --to dating
```

排他和关系阶段需要显式确认：

```powershell
python -m dating_agent --data-dir private advance --case Q001 --to exclusive --explicit-mutual
```

工具不会自动推进。

## 6. 查看建议和聚合指标

先记录每日或每周的聚合漏斗：

```powershell
python -m dating_agent --data-dir private funnel-log --date 2026-09-27 --profiles-reviewed 20 --likes-sent 8 --notes-sent 2 --matches 5 --first-replies 4 --substantive-chats 3 --invitations-sent 2 --first-dates-completed 1 --mutual-second-date-yes 1 --minutes-spent 180
```

漏斗只记聚合数量，不写人名或个人资料。然后查看滚动转化和每 10 小时双向二约：

```powershell
python -m dating_agent --data-dir private review --case Q001
python -m dating_agent --data-dir private metrics
```

## 7. 暂停或关闭

```powershell
python -m dating_agent --data-dir private pause --case Q001
python -m dating_agent --data-dir private close --case Q001 --reason incompatible
```

关闭原因是流程分类，不是对人的评价。
