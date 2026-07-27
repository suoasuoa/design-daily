# 点赞 / Pass 偏好系统

## 目标

让团队每天对选品做轻量反馈，并把结果用于下一轮搜索、审核和排序。反馈不会替代原有品类、真实性、创新和链接质量门槛。

## 用户流程

1. 每张卡片可以选择“赞”或“Pass”。
2. Pass 必须选择原因：太普通、功能弱、品类错误、利润不足、难落地、证据错误。
3. 页面显示当天已评数量，并支持查看未处理、已赞和已 Pass。
4. 所有操作均可撤销。

## 学习规则

- 同一产品：团队 Pass 多于点赞时进入精确屏蔽清单。
- 相似方向：一次 Pass 只降权，多次同原因 Pass 才持续加强负向权重。
- 点赞方向：提高相关功能、结构、场景、来源和启发类型的搜索覆盖。
- 探索保护：每轮保留约 20% 不同于历史偏好的新方向。
- 硬门槛不变：偏好不能让普通基础款、错品类、弱链接或低创新产品通过。

## 数据流

```text
GitHub Pages 卡片
  -> feedback-client.js
  -> 反馈 API（Supabase）
  -> data/feedback_events.json
  -> build_preference_profile.py
  -> data/preference_profile.json
  -> DeepSeek 搜索计划 / 候选预审 / 品类终审
```

浏览器在反馈 API 尚未配置或暂时离线时，会把事件保存在本机待同步队列，不丢失用户操作。

## 反馈事件

```json
{
  "event_id": "uuid",
  "workspace": "design-daily",
  "actor_id": "user-id",
  "product_id": "stable-product-id",
  "action": "like",
  "reason": "",
  "context": {
    "tab": "daily",
    "daily_group": "daily-2026-07-27"
  },
  "item_snapshot": {
    "title": "product title",
    "category": "氛围灯",
    "source_family": "媒体案例",
    "axes": ["结构启发"]
  },
  "created_at": "2026-07-27T08:00:00Z"
}
```

## 上线步骤

1. Supabase 使用 `supabase/feedback_schema.sql` 创建反馈表、匿名写入策略和限流。
2. 网页通过 Publishable Key 直接写入，访客无需登录，反馈内容不可匿名读取。
3. GitHub Actions 使用 `SUPABASE_URL` 和 `SUPABASE_SECRET_KEY` 同步反馈事件。
4. 采集开始前运行 `sync_feedback.py` 和 `build_preference_profile.py`。
5. 小范围试用一周，观察 Pass 原因与点赞方向，再调整相似度权重。

当前功能分支为 `feature/preference-feedback`。稳定回滚点为 `stable-before-feedback-2026-07-27`。
