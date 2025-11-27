# ANTLR配置快速指南

## 当前状态

✅ **jar文件已就绪**: `jars/antlr-4.13.2-complete.jar`  
❌ **Java未安装**: 需要安装Java才能使用ANTLR

## 快速安装Java（Windows）

### 方法1: 使用Chocolatey（最简单）

```powershell
# 如果已安装Chocolatey
choco install openjdk

# 如果未安装Chocolatey，先安装它
# 以管理员身份运行PowerShell，然后执行:
Set-ExecutionPolicy Bypass -Scope Process -Force; [System.Net.ServicePointManager]::SecurityProtocol = [System.Net.ServicePointManager]::SecurityProtocol -bor 3072; iex ((New-Object System.Net.WebClient).DownloadString('https://community.chocolatey.org/install.ps1'))
```

### 方法2: 使用Winget（Windows 10/11自带）

```powershell
winget install Microsoft.OpenJDK.11
```

### 方法3: 手动下载安装

1. 访问: https://adoptium.net/
2. 选择:
   - Version: 11 或 17 (LTS版本)
   - Operating System: Windows
   - Architecture: x64
3. 下载并运行安装程序
4. 安装时选择"Add to PATH"

## 验证安装

安装完成后，**重新打开命令行窗口**，然后运行:

```bash
java -version
```

应该看到类似输出:
```
openjdk version "11.0.19" 2023-04-18
OpenJDK Runtime Environment (build 11.0.19+9)
OpenJDK 64-Bit Server VM (build 11.0.19+9, mixed mode)
```

## 生成解析器

Java安装完成后，运行:

```bash
cd mflang/grammar
python generate_parser.py
```

脚本会自动:
1. ✅ 检查并安装 `antlr4-python3-runtime`（如果需要）
2. ✅ 查找 `jars/antlr-4.13.2-complete.jar`
3. ✅ 检查Java是否可用
4. ✅ 生成解析器文件

## 如果遇到问题

### 问题: "java不是内部或外部命令"

**原因**: Java未安装或未添加到PATH

**解决**:
1. 确认Java已安装
2. 检查PATH环境变量是否包含Java的bin目录
3. 重新打开命令行窗口

### 问题: "找不到jar文件"

**解决**: 确认jar文件在 `jars/antlr-4.13.2-complete.jar`

### 问题: 生成失败

**检查**:
1. Java版本是否兼容（需要Java 8+）
2. 语法文件 `MFLang.g4` 是否存在
3. 查看错误信息

## 手动生成（如果自动脚本失败）

```bash
cd mflang/grammar
java -jar ../../jars/antlr-4.13.2-complete.jar -Dlanguage=Python3 -visitor MFLang.g4
```

## 下一步

生成成功后，可以:
1. 运行测试: `python test_parser.py`
2. 使用解析器解析麦语言代码
3. 生成Python策略代码

