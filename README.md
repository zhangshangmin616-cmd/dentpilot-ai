# MedStudy CN MVP

这是一个给零基础练手的最小可用版本：

- 粘贴英文医学/口腔课程内容
- 自动提取内置术语
- 生成中文讲解
- 生成 Quiz
- 生成 Anki CSV 卡片

当前版本是本地演示版，不需要 API Key。它用 `glossary.py` 里的术语库做规则生成。后续可以接入合法可用的 AI 模型供应商。

## 1. 安装 Python

去 Python 官网下载安装 Python 3。

安装时如果是 Windows，请勾选 “Add Python to PATH”。

## 2. 打开终端

Windows：打开 PowerShell。

macOS：打开 Terminal。

进入项目目录，例如：

```bash
cd medstudy_cn_mvp
```

## 3. 创建虚拟环境

Windows：

```bash
python -m venv .venv
.venv\Scripts\activate
```

macOS / Linux：

```bash
python3 -m venv .venv
source .venv/bin/activate
```

## 4. 安装依赖

```bash
pip install -r requirements.txt
```

## 5. 启动网站

```bash
streamlit run app.py
```

然后浏览器会打开：

```text
http://localhost:8501
```

## 6. 怎么修改术语库

打开 `glossary.py`，按下面格式继续添加：

```python
"new term": {
    "zh": "中文术语",
    "definition": "English definition.",
    "explanation_zh": "中文解释。",
    "category": "Dentistry / Your Category",
},
```

## 7. 下一步开发建议

第一阶段：把这个本地 app 跑起来。

第二阶段：增加更多口腔术语。

第三阶段：接入 AI 模型，让它真正生成更自然的中文讲解和题目。

第四阶段：增加登录、课程文件夹、PDF 上传和付费。

## 8. 合规边界

这是学习辅助软件，不是考试作弊、代写、VPN、绕过学校系统或医疗诊断工具。
