# 初中单词 3000：词源、PDF 下载与发音落地方案

| 文档项 | 内容 |
|---|---|
| 版本 | v1.0 |
| 日期 | 2026-11-03 |
| 适用产品 | 初中单词 3000 · 分类默写 |
| 目标 | 给出可合法落地、可替换、可验收的词库与发音方案，而不只是功能介绍 |
| 相关文档 | `docs/prd-junior-vocabulary-dictation-v0.2.md` |

## 0. 先给结论

1. **教育部没有发布一份名为“初中单词 3000”的官方 PDF。** 官方课标规定的是学习范围与词汇能力要求，具体教材词表要按教材版本和册次获取。所谓“3000 词表”通常是产品汇编、机构词书或把课标词、教材词、中考拓展词合并后的商业口径。
2. 因此不建议把网上任意一份“3000 词 PDF”直接作为正式词库。正确路线是：**官方课标/教材做范围依据 + 有许可的开源词典做基础字段 + 自己完成教材单元映射与审核 + 记录来源版本**。
3. 首版建议只做一个教材版本（如人教版），先做“核心词 + 单元同步词”，再扩展到主题和中考高频词。3000 是词汇库规模，不是一次学习任务。
4. 发音不要依赖不明来源的公开 URL。推荐：**ipa-dict 提供英美音标 → Wikimedia Commons 的 CC0/CC BY 真人录音覆盖高频词 → Piper 本地合成补齐全部词条 → 浏览器设备语音只做明确标注的降级**。
5. 金山词霸/有道可以作为“需授权 API”候选，但不能把网页播放地址或未授权公开接口直接封装成产品能力。生产环境必须后端代理，密钥不能进 Vue 前端，也不能进 Git。

## 1. 可用的官方与开放来源

### 1.1 官方范围依据

| 来源 | 地址 | 能提供什么 | 不能提供什么 | 使用建议 |
|---|---|---|---|---|
| 教育部《义务教育英语课程标准（2022年版）》 | https://www.moe.gov.cn/srcsite/A26/s8001/202204/W020220420582349487953.pdf | 课程目标、分级要求、词汇学习范围与附录参考 | 不是商业产品可直接导入的 3000 条结构化词库 | 作为范围校验与审核依据，不整本复制进产品 |
| 国家中小学智慧教育平台 · 教材 | https://basic.smartedu.cn/tchMaterial | 官方电子教材；按学段、学科、版本、年级查看 | 不承诺提供可直接批量下载的结构化词表 | 登录后按本人教材核对单元词汇；仅作个人学习参考 |
| 国家中小学智慧教育平台主站 | https://www.zxx.edu.cn/ | 课程教学、电子教材、同步课程资源 | 同上 | 可用于核对教材单元和发音教学材料 |
| 人民教育出版社 · 教材电子版 | https://www.pep.com.cn/ | 人教版官方电子教材入口 | 教材正文有版权声明，不能据此批量抓取或再分发 | 只作为教材版本核对来源；词库字段需自行重建 |

**版权底线：** 教材正文、配套词表和插图受版权保护。即使用户能打开官方电子教材，也不等于可以把整本 PDF、整份词表打包进 GitHub 公共仓库或再分发。个人学习可以做笔记和校对，公开发布要另找许可或获得授权。

### 1.2 可直接下载的 PDF / 数据地址

| 资源 | 直接地址 | 许可/说明 | 适合用途 |
|---|---|---|---|
| 教育部英语课标 PDF | https://www.moe.gov.cn/srcsite/A26/s8001/202204/W020220420582349487953.pdf | 官方公开文件；以官方页面说明为准 | 核对课标词汇范围、分级要求 |
| ECDICT 仓库 | https://github.com/skywind3000/ECDICT | 仓库声明 MIT；数据由多来源整理，需保留来源说明并抽查 | 英文词形、中文释义、音标、考试标签、词频；作为基础词典 |
| ECDICT 单文件数据 | https://github.com/skywind3000/ECDICT/blob/master/ecdict.csv | 同上；文件较大，建议下载后用脚本筛选 | 生成 `zk` 中考标签候选词池 |
| ipa-dict 仓库 | https://github.com/open-dict-data/ipa-dict | MIT | 英美 IPA 音标；不含真人音频 |
| ipa-dict 英式数据 | https://github.com/open-dict-data/ipa-dict/blob/master/data/en_UK.txt | MIT | 英式音标 |
| ipa-dict 美式数据 | https://github.com/open-dict-data/ipa-dict/blob/master/data/en_US.txt | MIT | 美式音标 |
| 人教社教材电子版入口 | https://www.pep.com.cn/ | 官方电子教材；有版权限制 | 人工核对人教版单元词汇，不作为批量数据源 |
| 国家智慧教育平台教材入口 | https://basic.smartedu.cn/tchMaterial | 官方平台；登录后查看 | 核对教材版本和单元顺序 |

### 1.3 “3000 词 PDF”候选与风险

| 候选 | 链接 | 看起来有什么 | 真实风险 | 结论 |
|---|---|---|---|---|
| `geekers123/3000EnglishWords` | https://github.com/geekers123/3000EnglishWords | 仓库内可直接打开 [最高频的3000核心词.pdf](https://github.com/geekers123/3000EnglishWords/blob/main/%E6%9C%80%E9%AB%98%E9%A2%91%E7%9A%843000%E6%A0%B8%E5%BF%83%E8%AF%8D.pdf)、[牛津3000词.pdf](https://github.com/geekers123/3000EnglishWords/blob/main/%E7%89%9B%E6%B4%A53000%E8%AF%8D.pdf)、[牛津5000词.pdf](https://github.com/geekers123/3000EnglishWords/blob/main/%E7%89%9B%E6%B4%A55000%E8%AF%8D.pdf)，仓库标 Apache-2.0 | 仓库许可证不一定覆盖 PDF 内文权利；“牛津3000”本身是出版品牌词表，不能仅凭仓库 LICENSE 认定可再分发 | 只能人工比对，不建议直接导入或再发布 |
| `mikigo/english-chinese-words` | https://github.com/mikigo/english-chinese-words | Web 背单词项目，按小学/初中/高中/中考等分册，Apache-2.0 | 代码许可与词表数据许可需要分开核验；词表可能来自第三方词书 | 可研究结构，不直接把全部数据当自有词库 |
| `lilinji/English` | https://github.com/lilinji/English | 声称 960+ 词书、教材同步、CC 许可 | “CC”未在链接摘要中明确版本与适用范围，且教材词表原始权利复杂 | 只作人工比对，使用前逐项核验许可 |
| `kajweb/dict` | https://github.com/kajweb/dict | 包含人教版初中各册、中考词等，结构化 JSON 完整 | README 说明从“X 道背单词”抓取；仓库没有明确数据许可；发音依赖公开接口 | **不作为发布词库来源**；只能个人研究，不能打包分发 |
| 各类网盘/文库“中考 3000 词 PDF” | 不提供具体盗版链接 | 常见“打印版”“默写版” | 来源、版本、错误率、授权均不可控 | 只能作为家长个人参考，不能作为产品数据源 |

> 提醒：`kajweb/dict` 的词表结构与发音字段很诱人，但“能下载”不等于“能用于产品”。如果已有本地副本，建议只做个人学习比对，不进入公开 GitHub 仓库。

## 2. 推荐词库构建方案

### 2.1 数据分层

```text
L1 官方范围：课标分级要求、教材版本与册次
        ↓
L2 基础词形与释义：ECDICT（MIT）筛选 + 人工校对
        ↓
L3 英美音标：ipa-dict（MIT）对齐 Word/Sense
        ↓
L4 单元与主题：按本人教材人工映射，形成 Wordbook / Unit / Topic
        ↓
L5 发音资产：Wikimedia 真人录音 + Piper 本地合成 + 来源清单
        ↓
L6 发布版本：去重、抽检、词库版本号、THIRD_PARTY_NOTICES
```

### 2.2 候选词池生成逻辑

1. 从 ECDICT 的 `tag` 字段筛出含 `zk`（中考）的词条，作为候选池，不直接等于“初中 3000”。
2. 用 BNC/COCA 词频、Collins/Oxford 标记、词长、是否专有名词等做初筛。
3. 过滤短语、缩写、明显超纲词，人工复核多义词。
4. 按教材单元建立映射；没有教材依据的词进入“拓展层”，不混入“教材核心层”。
5. 目标 3000 条不是硬凑数字：核心层优先，主题拓展层补足，所有层级在 UI 中可区分。
6. 每条词记录 `source`、`source_version`、`license`、`review_status`，发布前抽样复核。

示意脚本（只示范字段筛选，不是完整生产代码）：

```python
import csv

candidates = []
with open("ecdict.csv", newline="", encoding="utf-8") as f:
    for row in csv.DictReader(f):
        tags = (row.get("tag") or "").lower().split()
        word = (row.get("word") or "").strip()
        translation = (row.get("translation") or "").strip()
        if "zk" not in tags:
            continue
        if not word or not translation:
            continue
        if not word.replace("-", "").replace("'", "").replace(" ", "").isalpha():
            continue
        candidates.append({
            "word": word,
            "phonetic": row.get("phonetic", ""),
            "translation": translation,
            "exchange": row.get("exchange", ""),
            "source": "ECDICT",
        })

print(len(candidates))
```

**注意：** ECDICT 的 `translation` 常含多个词性、长释义和考试式说明，不能直接作为初中默写答案。需要把词义拆成 `WordSense`，给每个词义指定一个适合当前年级的核心答案和可接受答案。

### 2.3 词义拆分示例

```json
{
  "word": "experience",
  "senses": [
    {
      "pos": "n.",
      "meaning_zh": "经历",
      "accepted_zh": ["经历", "一次经历"],
      "example": "It was a valuable experience.",
      "example_zh": "那是一次宝贵的经历。"
    },
    {
      "pos": "n.",
      "meaning_zh": "经验",
      "accepted_zh": ["经验"],
      "example": "She has a lot of teaching experience.",
      "example_zh": "她有丰富的教学经验。"
    }
  ]
}
```

默写题必须绑定 `sense_id`，不能只绑定英文词形。否则学生写对英文，却被另一个词义的中文题干误判，或者进度把两个词义混在一起。

### 2.4 单元映射与人工审核

- 首版只选一个出版社和一个年级，例如“人教版七年级上册”。
- 先在数据库中建立 `Unit` / `Topic`，再导入词条并绑定单元。
- 单元映射必须由教材原文或本人合法笔记核对，不能由 AI 凭常识猜测。
- AI 可做“疑似单元”建议，但必须人工确认后才进入正式词库。
- 词库发布记录：版本号、词条数、来源快照日期、审核人、变更说明。

## 3. 发音来源与落地架构

### 3.1 候选来源比较

| 来源 | 类型 | 许可/接入条件 | 覆盖 3000 词 | 英/美音 | 质量与风险 | 适合阶段 |
|---|---|---|---|---|---|---|
| 金山词霸 / iCIBA 词典 API | 词典发音 | 需申请 key；公开资料中的老接口与 CDN 地址不能替代正式授权，需确认当前服务条款 | 取决于接口词库，通常较高 | 常见英/美音字段 | 词条级发音较好；接口可能老旧、限流、音频不可再分发 | P1 质量增强候选，需书面条款 |
| 有道智云 TTS | 通用语音合成 | 官方 API，需 appKey/appSecret，按服务计费；有体验金 | 可合成任意词 | 可选音色/语种，需核对 | 不是词条词典 API，多音词、重音可能误读；需抽检 | 句子/兜底或已审核词条 |
| 有道 `dictvoice` 公开地址 | 非正式公开接口 | 无明确商业授权与 SLA；易被限制或失效 | 高 | 有 type=1/2 参数 | 不能把“能用”当作“可商用”；不应让前端直连 | 不建议生产使用 |
| Wikimedia Commons / Wiktionary 真人录音 | 真人音频 | 每个文件单独许可，常见 CC0 / CC BY / CC BY-SA；需署名与链接 | 覆盖不均 | 取决于录音 | 音质与口音不统一；需要逐文件记录署名；SA 有传染性要求 | 高频词优先、人工审核 |
| Piper TTS | 本地神经 TTS | 引擎 MIT；每个语音模型有独立许可，必须看 MODEL_CARD | 可覆盖全部词条 | 有 en_US / en_GB 模型 | 离线、可控；多音词需人工干预；模型许可不同 | **推荐作为全量补齐** |
| eSpeak NG | 本地规则 TTS | GPLv3 | 全覆盖 | 有英美音 | 机械感明显；分发软件时有 GPL 义务 | 离线兜底，不作为主音色 |
| ipa-dict | 音标数据 | MIT | 取决于词表 | en_UK / en_US | 只有音标，没有声音；覆盖与多音词需抽查 | **音标主来源** |
| 浏览器 SpeechSynthesis | 设备 TTS | 随浏览器/系统，不可控 | 取决于设备 | 取决于系统 voice | 无统一发音质量、可能无网络/无 voice；不能当作真人音频 | UI 降级，明确标注“设备语音” |

**关于金山词霸：** 网上常见的 `http://dict-co.iciba.com/api/dictionary.php?w=hello&key=...` 是老接口资料，返回音标和 mp3 地址的思路可参考，但当前是否仍开放、授权范围与配额必须以官方平台为准。没有明确授权时，不能把返回的 `res-tts.iciba.com` 地址直接嵌入产品，也不能批量下载后随代码分发。

**关于网易/有道：** 有道智云 TTS 是通用语音合成，不等于“词典词条发音”。`read`、`lead`、`live`、`record` 等多音词若没有词性/词义上下文，TTS 可能读错。若使用，必须对高风险管理词做人工试听与覆盖。

### 3.2 推荐的生产方案

**目标：全部 3000 词可用、无前端密钥、来源可追溯、可离线、可替换。**

```text
词条进入发布流程
  ├─ 1. 先找已审核真人音频（Wikimedia CC0 / CC BY，按文件记录署名）
  ├─ 2. 高频/多音词人工试听，不合格则人工录制或替换
  ├─ 3. 其余词用 Piper 生成英/美两版，人工抽检
  ├─ 4. 浏览器设备语音仅作为“音频缺失”时的 UI 降级
  └─ 5. 音频资产写入 data/audio，manifest 入库，绝不进 Git
```

**为什么不全用商业接口？**

- 3000 词 × 2 口音 = 6000 次请求，长期可用性依赖外部配额和价格。
- 公开播放地址不等于可再分发，容易出现上线后失效或版权问题。
- 音频资产一旦本地化，产品离线可用，响应稳定。

**为什么不全用 TTS？**

- 真人录音对高频词的音质和可信度更好。
- TTS 在多音词、专有名词、词形变化上可能读错。
- TTS 音色统一但容易“机械”，需要抽样主观验收。

### 3.3 音频资产规范

| 项目 | 规范 |
|---|---|
| 文件命名 | `audio/{word_id}/{accent}.mp3`，不能只用英文词名（同形异义词会覆盖） |
| 格式 | MP3 单声道，建议 64kbps；原始 WAV 不进入发布包 |
| 裁切 | 去掉首尾长静音，保留自然起音；不做过度压缩 |
| 时长 | 单词通常 0.3～2.5 秒；异常长/短进入人工复核 |
| 校验 | 文件存在、可解码、时长合理、MD5/SHA256 记录 |
| 元数据 | `accent`、`source_type`、`source_url`、`license`、`attribution`、`checksum`、`review_status` |
| 缓存 | 后端返回音频 URL 或流；设置缓存头；离线包单独导出 |
| 修改 | 音频不可静默覆盖；新版本生成新 asset 记录，保留历史 |

### 3.4 后端接口与缓存

```text
GET /api/v1/audio/{word_id}?accent=uk
  → 200 audio/mpeg
  → 404 AUDIO_NOT_AVAILABLE（前端显示“暂无音频”）
  → 503 AUDIO_PROVIDER_FAILED（前端允许重试/切换设备语音）
```

处理顺序：

1. 查询音频 manifest。
2. 命中且已审核：直接返回本地/对象存储文件。
3. 未命中：按配置的 provider chain 生成或获取。
4. 生成结果先做时长/解码校验，再入库。
5. 失败只影响该词音频，不阻断默写主流程。

**安全要求：**

- 商业 API key 只存在后端环境变量或密钥管理，不进 `package.json`、Vue bundle、GitHub。
- 前端不直连第三方词典域名，避免 key/Referer/防盗链问题与跨域泄露。
- 不把 `dictvoice` 这类公开 URL 写成生产依赖；如用于原型，标注“非生产”。
- 如使用 CC BY-SA 音频，需评估相同方式共享义务；如需避免 SA，优先 CC0 / CC BY 或自制音频。

### 3.5 发音质量验收

建议准备分层样本：

| 样本层 | 数量 | 重点 |
|---|---:|---|
| 高频基础词 | 300 | 清晰度、重音、连读 |
| 多音/同形异义词 | 100 | `read` / `lead` / `live` / `record` / `present` 等词性对应 |
| 英美差异词 | 100 | `tomato`、`schedule`、`either` 等口音差异 |
| 多音节/重音转移 | 100 | `photograph` / `photographer` |
| 缩写/专名/短语 | 100 | 是否适合默写、是否应单独处理 |

**放行门槛建议：**

- 抽样 500 条，人工听辨严重错误率 <1%。
- 多音词、专名、词形变化 100% 人工确认。
- 任何一条音频无来源、无许可或与词义不符，不得进入发布词库。
- 设备语音只能显示“设备语音”，不得显示“真人发音”或“标准英音”。

## 4. 词源与发音的实施步骤

| 阶段 | 操作 | 产出 |
|---|---|---|
| S0 授权确认 | 确定教材版本、词库来源许可、发音来源许可 | 来源清单与许可结论 |
| S1 样本冻结 | 选 200 个核心词，人工建词义/单元/答案 | 金标准样本 |
| S2 数据合并 | ECDICT 词形释义 + ipa-dict 英美音标 + 教材单元映射 | `words.csv` / SQLite |
| S3 音频试产 | 100 个词生成 Piper，另取 50 个 Wikimedia 真人音频 | 听辨报告 |
| S4 全量生产 | 约 3000 词 × 2 口音，异步生成、校验、入库 | 音频 manifest |
| S5 质量门禁 | 分层抽检、多音词复核、来源与许可核验 | 发布候选版本 |
| S6 发布 | 词库版本 + `THIRD_PARTY_NOTICES.md` + 备份 | 可回滚版本 |

## 5. 许可与合规清单

发布前必须逐项确认：

- [ ] 教材词表是否有授权；没有授权则只保留自己重建的字段，不分发教材原文。
- [ ] ECDICT 的来源说明与 MIT 许可证文件已保留。
- [ ] ipa-dict 的 MIT 许可证文件已保留。
- [ ] 每个 Wikimedia 音频记录作者、文件页、许可和修改说明。
- [ ] 商业 API 的使用条款允许缓存、展示和长期分发；不允许则不落地音频文件。
- [ ] Piper 语音模型的 MODEL_CARD 允许当前使用场景。
- [ ] 不把第三方 API key、教材 PDF、商业词库原始文件提交到 GitHub。
- [ ] `THIRD_PARTY_NOTICES.md` 随发布版本提供。
- [ ] 删除来源不明的词表副本，不将其作为产品兜底。

## 6. 参考链接

1. 教育部《义务教育英语课程标准（2022年版）》  
   https://www.moe.gov.cn/srcsite/A26/s8001/202204/W020220420582349487953.pdf
2. 国家中小学智慧教育平台  
   https://basic.smartedu.cn/tchMaterial
3. 人民教育出版社  
   https://www.pep.com.cn/
4. ECDICT（MIT）  
   https://github.com/skywind3000/ECDICT
5. ipa-dict（MIT）  
   https://github.com/open-dict-data/ipa-dict
6. 有道智云 TTS 官方文档  
   https://ai.youdao.com/docs/doc-tts-api.s
7. Piper 本地 TTS（MIT 引擎，语音模型单独许可）  
   https://github.com/rhasspy/piper
8. Wikimedia Commons 文件许可说明  
   https://commons.wikimedia.org/wiki/Commons:Licensing
9. GitHub 细粒度 Token 文档  
   https://docs.github.com/zh/authentication/keeping-your-account-and-data-secure/managing-your-personal-access-tokens

> 本文档中的链接核对日期为 2026-11-03。第三方接口、许可与页面可能变化，正式发布前必须重新核对官方条款。
