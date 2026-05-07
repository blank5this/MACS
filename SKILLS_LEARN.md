# Python + LangChain AI 开发速成路线

> 目标：让 Java 程序员快速具备 AI/LLM 开发能力，写进简历

---

## 一、Python 快速上手 (1-2周)

你是 Java 选手，学 Python 很快！重点看差异：

### 必学语法 (1-3天)

```python
# 1. 变量和类型 (Python 不用声明类型，但可以加类型提示)
name: str = "张三"
age: int = 25

# 2. 函数定义
def greet(name: str) -> str:
    return f"Hello, {name}"

# 3. 异步编程 (面试常问！)
import asyncio

async def fetch_data():
    return await some_async_call()

# 4. 列表/字典推导式
squares = [x**2 for x in range(10)]
d = {k: v for k, v in items if v > 0}

# 5. 类和继承
class Agent:
    def __init__(self, name: str):
        self.name = name
    
    async def think(self) -> str:
        return f"{self.name} is thinking..."

# 6. 类型提示 (简历里写"熟悉 Python 类型提示")
from typing import List, Optional, Dict, Any
```

### 快速入门资源

| 资源 | 链接 | 时间 |
|------|------|------|
| 官方教程 | python.org/tutorial | 2小时 |
| 廖雪峰 Python | liaoxuefeng.com/wiki/1016959663602400 | 1天 |
| 异步编程 | asyncio 官方文档 | 半天 |

---

## 二、LangChain 核心 (2-3周)

**这是 AI 开发的核心框架！面试必问！**

### 快速学习路线

```
Day 1-3: LangChain 基础概念
├── LangChain Expression Language (LCEL)
├── Prompt Template
└── Output Parser

Day 4-7: LLM 调用
├── ChatOpenAI / ChatAnthropic
├── 国产: ChatZhipuAI / ChatTongyi
└── 流式输出 Streaming

Day 8-14: RAG 开发
├── Document Loading
├── Text Splitting
├── Embedding
├── Vector Store (Chroma/FAISS)
└── Retrieval + QA

Day 15-21: Agent 开发
├── LCEL + Tool
├── create_react_agent
└── 自定义 Tool
```

### 简历能写什么 (重点！)

```yaml
技能清单:
  Python:
    - 熟练使用类型提示、异步编程 (asyncio)
    - 熟悉装饰器、生成器、上下文管理器
    - 能读懂和修改 Python 开源项目

  LangChain:
    - 熟练使用 LangChain LCEL 构建 Chain
    - 熟悉 RAG 开发流程: Document → Split → Embed → Retrieve → QA
    - 能自定义 Tool 和 Agent
    - 了解 ChatModel / LLMs 调用方式
    - 熟悉 Prompt Template 设计

  AI/LLM:
    - 了解主流 LLM 特性 (GPT-4/Claude/混元/Qwen)
    - 熟悉 Function Calling / Tool Use 机制
    - 了解 RAG、Agent、Memory 核心概念
    - 了解向量数据库原理 (Milvus/Chroma)
```

### 快速上手代码

```python
# === 1. 简单的 LLM 调用 ===
from langchain_openai import ChatOpenAI

llm = ChatOpenAI(model="gpt-4", api_key="your-key")
response = llm.invoke("你好，请自我介绍")
print(response.content)

# === 2. Prompt Template ===
from langchain_core.prompts import ChatPromptTemplate

prompt = ChatPromptTemplate.from_messages([
    ("system", "你是一个{role}，擅长{skill}"),
    ("human", "{question}"),
])

chain = prompt | llm  # LCEL 语法！
response = chain.invoke({
    "role": "Python导师",
    "skill": "教人写代码",
    "question": "什么是装饰器？"
})

# === 3. RAG 简单实现 ===
from langchain_community.document_loaders import TextLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import Chroma

# 加载文档
loader = TextLoader("你的文档.txt")
docs = loader.load()

# 分块
splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
chunks = splitter.split_documents(docs)

# 向量化
embeddings = OpenAIEmbeddings()
vectorstore = Chroma.from_documents(chunks, embeddings)

# 检索
retriever = vectorstore.as_retriever(search_kwargs={"k": 3})
results = retriever.invoke("你的问题")

# === 4. 简单 Agent ===
from langchain.agents import AgentType, initialize_agent
from langchain.tools import Tool
from langchain_community.chat_models import ChatZhipuAI

llm = ChatZhipuAI(zhipuai_api_key="your-key", model="glm-4")

def search_weather(city: str) -> str:
    """模拟搜索天气"""
    return f"{city}今天晴天，26度"

tools = [
    Tool(name="weather", func=search_weather, description="查询城市天气")
]

agent = initialize_agent(
    tools, llm, agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION, verbose=True
)

agent.run("深圳明天会下雨吗？")
```

---

## 三、推荐学习资源

### 视频教程 (免费)

| 课程 | 平台 | 链接 |
|------|------|------|
| LangChain 官方教程 | YouTube | LangChain AI |
| 跟月狐学 AI | B站 | 搜索"LangChain教程" |

### 文档 (必读)

| 文档 | 重点 |
|------|------|
| python.langchain.com | 官方文档 |
| github.com/langchain-ai/langchain | 源码 |

### 项目练习

1. **LangChain 官方 Quickstart** (必做!)
   - https://python.langchain.com/docs/get_started/quickstart

2. **RAG 实战项目**
   - 自己搭一个本地知识库问答

3. **Agent 练手**
   - 用 LangChain Agent 调用计算器/搜索

---

## 四、学习时间安排

```
Week 1: Python 基础 + 差异点
Week 2: LangChain LCEL + LLM 调用  
Week 3: RAG 开发
Week 4: Agent 开发 + 实战项目
```

---

## 五、简历写法示例

```yaml
项目经历:

MACS - Multi-Agent Collaboration System
- 独立开发的多智能体协作框架，支持层级/管道/去中心化三种协作模式
- 集成 8+ LLM Provider，包括混元/Qwen/Claude/DeepSeek 等主流模型
- 实现 10+ 工具集：搜索/计算/代码执行/RAG 检索等
- 技术栈: Python / LangChain / AutoGen / RAG / 向量数据库
- GitHub: https://github.com/blank5this/MACS (200+ stars)

个人项目 - 本地知识库问答系统
- 基于 LangChain 实现 RAG 全流程：文档加载→分块→向量化→检索→生成
- 使用 Chroma 向量数据库，支持百万级文档检索
- 支持 GPT-4 / 混元 / Qwen 多模型切换
- 技术栈: Python / LangChain / Chroma / FastAPI
```

---

## 六、面试高频问题 (准备！)

| 问题 | 答案要点 |
|------|----------|
| 什么是 RAG？ | Retrieval Augmented Generation，检索增强生成 |
| RAG 和微调的区别？ | RAG 更新知识快，成本低；微调成本高但更定制 |
| LangChain 的 LCEL 是什么？ | LangChain Expression Language，链式调用语法 |
| Agent 和 Chain 的区别？ | Agent 有自主决策能力，能选择工具 |
| 你的 MACS 项目怎么实现的？ | 协作模式、消息路由、Agent 抽象 |

---

**下一步行动：**
1. ⬇️ 安装 `pip install langchain langchain-openai`
2. 📖 跟着官方 Quickstart 做一遍
3. 🚀 把 MACS demo 跑起来

有问题随时问我！
