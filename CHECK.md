# ✅ Design Daily - 数据更新检查清单

## 每次修改品牌数据后

### 步骤 1：验证 brand_pool.json
```bash
python3 -c "
import json
with open('brand_pool.json') as f:
    pool = json.load(f)
print(f'总数: {len(pool)}')
sources = set(x['source'] for x in pool)
print(f'来源: {len(sources)} 个')
cats = set(x['category'] for x in pool)
print(f'品类: {len(cats)} 个')

# 检查 iF 链接格式
if_items = [x for x in pool if 'ifdesign.com' in x.get('url','')]
bad = 0
for x in if_items:
    parts = x['url'].rstrip('/').split('/')
    last = parts[-1]
    second_last = parts[-2]
    if not (last.isdigit() and len(last) >= 5 and not second_last.isdigit()):
        bad += 1
        print(f'  ❌ {x[\"title\"][:35]} → {x[\"url\"]}')
print(f'iF 链接: 正确={len(if_items)-bad}, 错误={bad}')
"
```

### 步骤 2：重新生成 data.js
```bash
cd /tmp/design-daily && python3 generate.py
```

### 步骤 3：确认 data.js 格式正确
```bash
head -c 80 /tmp/design-daily/data.js
# 必须输出: const digestData = {"date": ..., "items": [...}
# ❌ 不是: const DIGEST_DATA = [...]  (变量名大写 + 数组格式)
```

### 步骤 4：提交两个文件
```bash
cd /tmp/design-daily
git add brand_pool.json data.js
git commit -m "描述变更"
git push
```

### 步骤 5：验证线上部署
```bash
# 确认 data.js 部署成功
curl -s https://suoasuoa.github.io/design-daily/data.js | head -c 80
# 确认 iF 链接可用
curl -s -o /dev/null -w "%{http_code}" \
  https://ifdesign.com/en/winner-ranking/project/zhaozhou-bridge/735114
```

## 📌 历史踩坑记录

### 2026-05-05 — iF URL 格式修复

**问题：** iF 设计奖链接 404

**修复：**
- `brand_pool.json` 中的 iF URL 格式从 `entry_id/offset` 改为 `slug/entry_id`
  - ❌ `https://ifdesign.com/en/winner-ranking/project/735114/0`
  - ✅ `https://ifdesign.com/en/winner-ranking/project/zhaozhou-bridge/735114`
  其中 slug = title 小写+空格转连字符，entry_id 从旧 git commit 的历史 URL 提取

**翻车：** 修了 `brand_pool.json` 但没提交 `data.js` → 线上还是旧数据

### 2026-05-05 — data.js 格式错误

**问题：** 链接还是 404，整站数据都不正常

**根因：** 之前修复时手写脚本覆盖了 `data.js`，写成了错误格式：
- ❌ `const DIGEST_DATA = [数组]; export { DIGEST_DATA };`
- ✅ `const digestData = {"items": [...]}`

前端 index.html 检测的是 `typeof digestData !== 'undefined' && digestData.items`

**教训：** 永远用 `python3 generate.py` 生成 `data.js`，不要手写。生成后检查前 80 字符。

### 2026-05-05 — data.js 写到了子目录

**问题：** 之前 `data.js` 写到了 `data/data.js` 子目录，根目录没更新

**根因：** 有些脚本的 `output_path` 是 `"data/data.js"`，但 GitHub Pages 加载的是根 `data.js`

**教训：** `generate.py` 写的是根目录的 `data.js`，其他脚本别乱改路径。
