# Minecraft Mod 自动汉化工具

自动扫描 Minecraft mod 文件夹中的 jar 文件，提取英文语言文件（en_us.json），翻译为中文，然后打包成标准资源包（.zip）。

## 功能特性

- **自动扫描** - 遍历 mod 文件夹中的所有 jar 文件，自动提取 en_us.json
- **智能跳过** - 已包含 zh_cn.json 的 mod 自动跳过，不覆盖已有汉化
- **导入已有汉化** - 支持导入已有的汉化资源包（zip 或文件夹），比对后只翻译缺失部分
- **两种翻译引擎** - 支持百度翻译 API 和 OpenAI 兼容 API（可自定义提示词）
- **翻译缓存** - 自动缓存已翻译文本，避免重复调用 API，节省费用
- **标准资源包输出** - 生成符合 Minecraft 规范的资源包 zip 文件
- **交互式模式** - 双击运行即可通过菜单引导操作，也支持命令行参数

## 文件结构

```
minecraft-Chinese-Tool/
│
├── main.py                  # 主入口（交互式模式 + 命令行模式）
├── config.json              # 配置文件（翻译API密钥、资源包设置等）
├── requirements.txt         # Python 依赖
├── README.md                # 本文件
│
├── translator/              # 翻译器模块
│   ├── __init__.py          # 模块初始化
│   ├── base.py              # 翻译器抽象基类
│   ├── baidu_translator.py  # 百度翻译 API 实现
│   └── ai_translator.py     # OpenAI 兼容 API 实现（含系统提示词）
│
├── mod_processor.py         # mod 文件处理（扫描 jar、提取语言文件）
├── import_handler.py        # 导入已有汉化资源包并比对翻译
├── resource_pack.py         # 资源包生成（打包为 zip）
├── cache.py                 # 翻译缓存管理
│
├── cache/                   # 缓存目录（自动生成）
│   └── translation_cache.json
│
└── temp/                    # 临时文件目录（运行时自动创建和清理）
```

## 环境要求

- Python 3.7+
- 依赖库：`requests`

## 安装

```bash
# 克隆或下载项目
cd minecraft-Chinese-Tool

# 安装依赖
pip install -r requirements.txt
```

## 使用方法

### 方式一：交互式模式（推荐）

直接运行 `main.py`，按菜单提示操作：

```bash
python main.py
```

运行后会显示：

```
============================================================
  Minecraft Mod 自动汉化工具
  自动扫描 → 提取语言文件 → 翻译 → 打包资源包
============================================================

请选择操作:
  [1] 开始汉化（扫描mod文件夹）
  [2] 初始化配置文件
  [3] 退出
```

按提示依次选择：
1. **mod 文件夹** - 自动检测或手动输入路径
2. **翻译引擎** - AI 翻译或百度翻译
3. **导入已有汉化**（可选）- 导入已有的汉化包减少翻译量
4. **确认开始** - 开始处理

### 方式二：命令行模式

```bash
# 生成配置文件模板
python main.py --init

# 基本用法：扫描 mod 文件夹并翻译打包
python main.py --mods-path "C:\Users\你的用户名\AppData\Roaming\.minecraft\mods"

# 导入已有汉化包，只翻译缺失部分
python main.py --mods-path ./mods --import-pack 已有汉化包.zip

# 使用百度翻译，指定输出文件名
python main.py --mods-path ./mods --translator baidu --output 中文包.zip

# 只导入已有汉化，不调用翻译 API
python main.py --mods-path ./mods --import-pack 已有汉化.zip --no-translate
```

#### 命令行参数说明

| 参数 | 说明 |
|------|------|
| `--init` | 生成配置文件模板 |
| `--mods-path` | mod 文件夹路径（必需） |
| `--import-pack` | 导入已有汉化资源包（zip 文件或文件夹路径） |
| `--translator` | 翻译引擎类型：`baidu` 或 `ai` |
| `--output, -o` | 输出资源包文件名 |
| `--no-translate` | 不调用翻译 API，只使用导入的汉化和缓存 |

## 配置说明

首次使用前，编辑 `config.json` 配置翻译 API 密钥：

```json
{
  "translator": "ai",
  "baidu": {
    "app_id": "你的百度翻译APP_ID",
    "secret_key": "你的百度翻译密钥"
  },
  "ai": {
    "api_url": "https://api.openai.com/v1/chat/completions",
    "api_key": "你的API密钥",
    "model": "gpt-4o-mini",
    "system_prompt": "自定义翻译提示词（留空使用默认）"
  },
  "resource_pack_name": "Mod中文翻译资源包",
  "resource_pack_description": "自动翻译的Mod中文语言包",
  "game_version": "1.20.1"
}
```

### 配置项说明

| 配置项 | 说明 |
|--------|------|
| `translator` | 默认翻译引擎：`ai`（OpenAI兼容）或 `baidu`（百度翻译） |
| `baidu.app_id` | 百度翻译开放平台的 APP ID |
| `baidu.secret_key` | 百度翻译开放平台的密钥 |
| `ai.api_url` | OpenAI 兼容 API 的地址（支持各类兼容接口） |
| `ai.api_key` | API 密钥 |
| `ai.model` | 模型名称（如 `gpt-4o-mini`、`deepseek-chat` 等） |
| `ai.system_prompt` | AI 翻译的系统提示词（留空使用内置默认提示词） |
| `resource_pack_name` | 输出资源包的名称 |
| `resource_pack_description` | 资源包的描述文本 |
| `game_version` | 目标 Minecraft 版本号（影响 pack_format） |

### 翻译 API 获取方式

**百度翻译：**
1. 访问 [百度翻译开放平台](https://fanyi-api.baidu.com/)
2. 注册账号并开通通用翻译 API
3. 获取 APP ID 和密钥

**OpenAI 兼容 API：**
- 支持任何 OpenAI 兼容接口，包括：
  - OpenAI 官方 API
  - DeepSeek API
  - 本地部署的 Ollama / LM Studio 等
  - 其他兼容 OpenAI 格式的 API 服务

## 工作流程

```
┌─────────────────────────────────────────────────────────┐
│                     开始                                 │
└─────────────────────┬───────────────────────────────────┘
                      ▼
┌─────────────────────────────────────────────────────────┐
│  Step 1: 扫描 mod 文件夹中的 jar 文件                    │
│  - 跳过已有 zh_cn.json 的 jar                            │
│  - 提取 en_us.json 到临时文件夹                          │
└─────────────────────┬───────────────────────────────────┘
                      ▼
┌─────────────────────────────────────────────────────────┐
│  Step 2: 导入已有汉化资源包（可选）                       │
│  - 解析资源包中的 zh_cn.json                             │
│  - 按 modid 匹配和比对                                   │
└─────────────────────┬───────────────────────────────────┘
                      ▼
┌─────────────────────────────────────────────────────────┐
│  Step 3: 比对并翻译                                      │
│  - 已有汉化的 key → 跳过                                 │
│  - 缓存中的 key → 直接使用                               │
│  - 剩余 key → 调用翻译 API                               │
└─────────────────────┬───────────────────────────────────┘
                      ▼
┌─────────────────────────────────────────────────────────┐
│  Step 4: 打包资源包                                      │
│  - 生成 pack.mcmeta                                      │
│  - 按 assets/<modid>/lang/zh_cn.json 结构打包            │
│  - 输出为 zip 文件                                       │
└─────────────────────┬───────────────────────────────────┘
                      ▼
┌─────────────────────────────────────────────────────────┐
│  完成！将资源包放入 .minecraft/resourcepacks 文件夹使用   │
└─────────────────────────────────────────────────────────┘
```

## 输出资源包结构

```
Mod中文翻译资源包.zip
├── pack.mcmeta                    # 资源包元数据
└── assets/
    ├── modid1/
    │   └── lang/
    │       └── zh_cn.json         # 中文语言文件
    ├── modid2/
    │   └── lang/
    │       └── zh_cn.json
    └── ...
```

## 使用翻译后的资源包

1. 将生成的 `.zip` 文件放入 Minecraft 的 `resourcepacks` 文件夹
2. 启动游戏 → 设置 → 资源包 → 启用生成的汉化资源包
3. 确保游戏语言设置为 **简体中文**

## 支持的游戏版本

| 游戏版本 | pack_format |
|----------|-------------|
| 1.16.x - 1.16.5 | 5 |
| 1.17.x | 7 |
| 1.18.x | 8 |
| 1.19 - 1.19.2 | 9 |
| 1.19.3 | 12 |
| 1.19.4 | 13 |
| 1.20 - 1.20.1 | 15 |
| 1.20.2 | 18 |
| 1.20.3 - 1.20.4 | 22 |
| 1.20.5 - 1.20.6 | 32 |
| 1.21 - 1.21.3 | 34 |
| 1.21.4 | 46 |

## 常见问题

**Q: 翻译质量不好怎么办？**
A: 可以在 `config.json` 中修改 `ai.system_prompt`，自定义翻译提示词来优化翻译效果。例如可以指定特定 mod 的术语风格。

**Q: 如何节省 API 调用费用？**
A: 使用 `--import-pack` 参数导入已有的汉化包，程序会自动比对并跳过已翻译的内容。翻译结果也会被缓存，下次运行相同文本不会重复翻译。

**Q: 某些 mod 翻译后有乱码？**
A: 请确保 mod 的 jar 文件使用 UTF-8 编码。部分老版本 mod 可能使用其他编码。

**Q: 可以同时使用多个翻译引擎吗？**
A: 目前每次运行只能选择一种翻译引擎。可以通过命令行参数 `--translator` 覆盖配置文件中的默认设置。

## 许可证

MIT License
