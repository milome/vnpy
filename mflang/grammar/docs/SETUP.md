# ANTLR配置说明

## ✅ 已检测到jar文件

检测到您已经下载了 `antlr-4.13.2-complete.jar` 文件，位于 `jars/` 目录下。

## 自动配置

脚本 `generate_parser.py` 已经更新，会自动查找并使用项目中的jar文件。

## 使用步骤

### 1. ⚠️ 安装Java（必需）

ANTLR需要Java运行时环境（JRE）或Java开发工具包（JDK）。

**检查Java是否已安装**:
```bash
java -version
```

**如果显示"找不到java"或类似错误，请安装Java**:

#### Windows安装Java:

1. **方式1: 使用Chocolatey（推荐）**
   ```powershell
   choco install openjdk
   ```

2. **方式2: 手动下载安装**
   - 访问 [Adoptium OpenJDK](https://adoptium.net/)
   - 下载Windows版本的JDK（推荐JDK 11或17）
   - 运行安装程序
   - 确保添加到PATH环境变量

3. **方式3: 使用Winget**
   ```powershell
   winget install Microsoft.OpenJDK.11
   ```

#### Linux安装Java:
```bash
# Ubuntu/Debian
sudo apt-get update
sudo apt-get install default-jdk

# CentOS/RHEL
sudo yum install java-11-openjdk
```

#### macOS安装Java:
```bash
brew install openjdk
```

**安装后验证**:
```bash
java -version
# 应该显示类似: openjdk version "11.0.x" 或 "17.0.x"
```

### 2. 安装ANTLR Python运行时

```bash
pip install antlr4-python3-runtime
```

### 3. 生成解析器

直接运行生成脚本，脚本会自动找到jar文件：

```bash
cd mflang/grammar
python generate_parser.py
```

脚本会：
1. 自动查找 `jars/antlr-4.13.2-complete.jar`
2. 检查Java是否可用
3. 使用 `java -jar` 命令生成解析器

## 手动生成（可选）

如果自动脚本无法工作，可以手动运行：

```bash
cd mflang/grammar
java -jar ../../jars/antlr-4.13.2-complete.jar -Dlanguage=Python3 -visitor MFLang.g4
```

## 验证

生成成功后，应该看到以下文件：
- `MFLangLexer.py` - 词法分析器
- `MFLangParser.py` - 语法分析器
- `MFLangListener.py` - 监听器接口
- `MFLangVisitor.py` - 访问者接口

## 故障排除

### 问题1: "Java未安装"

**解决方案**: 安装Java（见步骤1）

### 问题2: "找不到jar文件"

**检查**:
1. 确认jar文件在 `jars/antlr-4.13.2-complete.jar`
2. 或修改脚本中的路径

### 问题3: "生成失败"

**检查**:
1. 语法文件 `MFLang.g4` 是否存在
2. Java版本是否兼容（需要Java 8+）
3. 查看错误信息

### 问题4: 权限错误

**解决方案**:
- Windows: 以管理员身份运行
- Linux/macOS: 使用 `sudo`（如果需要）

## 项目结构

```
vnpy/
├── jars/
│   └── antlr-4.13.2-complete.jar  ← jar文件位置
└── mflang/
    └── grammar/
        ├── MFLang.g4              ← 语法文件
        ├── generate_parser.py     ← 生成脚本（已更新）
        └── ...                    ← 生成的文件会在这里
```

## 下一步

生成解析器后，可以：

1. **测试解析器**:
   ```bash
   python mflang/grammar/test_parser.py
   ```

2. **使用解析器**:
   ```python
   from mflang.grammar import parse_mflang_string
   ast = parse_mflang_string("NUMOFDAY: BARPOS, NODRAW;")
   ```

3. **生成Python代码**:
   ```python
   from mflang.grammar import StrategyCodeGenerator
   generator = StrategyCodeGenerator("MyStrategy")
   code = generator.generate(ast)
   ```

