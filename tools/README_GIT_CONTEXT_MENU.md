# 添加 Git 命令到 Windows 右键菜单

本目录包含两个脚本，用于将常用的 Git 命令添加到 Windows 资源管理器的右键菜单中。

## 方法一：使用 PowerShell 脚本（推荐）

### 使用步骤：

1. **以管理员身份运行 PowerShell**
   - 按 `Win + X`，选择"Windows PowerShell (管理员)"
   - 或者在开始菜单搜索 PowerShell，右键选择"以管理员身份运行"

2. **运行脚本**
   ```powershell
   cd D:\Dev\vnpy
   .\add_git_context_menu.ps1
   ```

3. **刷新资源管理器**
   - 按 `Win + R`，输入 `explorer`，回车
   - 或者注销并重新登录

### 功能说明：

脚本会自动检测 Git 安装路径，并添加以下菜单项：

- **Git Bash Here** - 在当前目录打开 Git Bash
- **Git GUI Here** - 在当前目录打开 Git GUI
- **Git Status** - 显示 git status
- **Git Commit** - 执行 git commit -a
- **Git Push** - 执行 git push
- **Git Pull** - 执行 git pull
- **Git Log** - 显示最近20条提交记录

这些菜单项会出现在：
- 文件夹右键菜单
- 文件夹空白处右键菜单

## 方法二：使用注册表文件（简单快速）

### 使用步骤：

1. **检查 Git 安装路径**
   - 默认路径：`C:\Program Files\Git\`
   - 如果 Git 安装在其他位置，需要修改 `add_git_context_menu_simple.reg` 文件中的路径

2. **双击运行注册表文件**
   - 双击 `add_git_context_menu_simple.reg`
   - 点击"是"确认添加

3. **刷新资源管理器**

### 功能说明：

注册表文件会添加：
- **Git Bash Here** - 在当前目录打开 Git Bash
- **Git GUI Here** - 在当前目录打开 Git GUI

## 注意事项

1. **管理员权限**：PowerShell 脚本需要管理员权限运行
2. **Git 路径**：如果 Git 安装在其他位置，需要修改脚本中的路径
3. **刷新资源管理器**：添加后需要刷新资源管理器才能看到新菜单
4. **删除菜单**：如果需要删除，可以运行以下 PowerShell 命令：
   ```powershell
   Remove-Item "HKCU:\Software\Classes\Directory\shell\Git*" -Recurse -Force
   Remove-Item "HKCU:\Software\Classes\Directory\Background\shell\Git*" -Recurse -Force
   ```

## 自定义菜单项

如果需要添加其他 Git 命令，可以修改 PowerShell 脚本中的 `$menuItems` 数组，添加新的菜单项定义。

例如，添加 "Git Diff" 菜单项：
```powershell
@{
    Name = "Git Diff"
    Command = "powershell -NoExit -Command `"cd '%v'; git diff`""
    Icon = "$gitPath"
}
```

## 故障排除

1. **菜单不显示**：
   - 确认已刷新资源管理器
   - 检查注册表项是否正确创建
   - 使用 `regedit` 查看注册表

2. **命令执行失败**：
   - 检查 Git 是否正确安装
   - 确认 Git 路径是否正确
   - 检查 PowerShell 执行策略：`Get-ExecutionPolicy`

3. **权限问题**：
   - 确保以管理员权限运行脚本
   - 检查注册表权限设置

