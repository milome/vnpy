# 更新：动态画线演示文件路径变更

## 变更时间
2025-12-04

## 变更说明

演示文件从 `examples/demo_drawing_animation.py` 移动到 `examples/drawing/demo_drawing_animation.py`。

## 变更原因

为了更好地组织示例代码结构，将动画相关的演示文件放在独立的 `drawing` 子目录中。

## 文件路径变更

### 旧路径
```
examples/demo_drawing_animation.py
```

### 新路径
```
examples/drawing/demo_drawing_animation.py
```

## 已更新的文件

以下文件中的路径引用已全部更新：

### 1. 启动脚本
- ✅ `run_animation_demo.bat` - Windows启动脚本
- ✅ `run_animation_demo.sh` - Linux/Mac启动脚本

### 2. 文档文件
- ✅ `动态画线快速入门.md` - 快速入门指南
- ✅ `docs/drawing_animation_guide.md` - 详细使用指南
- ✅ `FEATURE_动态画线跑马灯效果.md` - 功能总结
- ✅ `README_动态画线.md` - 项目总览
- ✅ `BUGFIX_动态画线演示QPalette导入错误.md` - 修复说明

## 运行方式（更新后）

### Windows

```bash
# 方式1：使用启动脚本
.\run_animation_demo.bat

# 方式2：直接运行
python examples\drawing\demo_drawing_animation.py
```

### Linux/Mac

```bash
# 方式1：使用启动脚本
chmod +x run_animation_demo.sh
./run_animation_demo.sh

# 方式2：直接运行
python examples/drawing/demo_drawing_animation.py
```

## 验证

所有启动脚本和文档引用已更新并验证：

```bash
# 测试 Windows 启动脚本
.\run_animation_demo.bat

# 测试 Linux/Mac 启动脚本
./run_animation_demo.sh

# 直接运行（跨平台）
python examples/drawing/demo_drawing_animation.py
```

## 目录结构

```
vnpy-007-multi-timeframe-integration/
├── vnpy/
│   └── chart/
│       ├── drawing_animation.py          # 核心实现
│       └── __init__.py
├── examples/
│   └── drawing/                           # 新增：drawing 子目录
│       └── demo_drawing_animation.py      # 演示程序（新位置）
├── docs/
│   └── drawing_animation_guide.md         # 使用指南
├── tests/
│   └── test_drawing_animation.py          # 单元测试
├── run_animation_demo.bat                 # Windows 启动脚本
├── run_animation_demo.sh                  # Linux/Mac 启动脚本
├── 动态画线快速入门.md
├── FEATURE_动态画线跑马灯效果.md
└── README_动态画线.md
```

## 注意事项

1. **启动脚本已更新**：所有启动脚本已自动指向新路径，用户无需修改使用方式
2. **文档引用已更新**：所有文档中的路径引用已更新为新路径
3. **向后兼容**：虽然文件位置改变，但API和使用方式保持不变

## 相关文件清单

### 核心文件
- `vnpy/chart/drawing_animation.py` - 动画管理器实现（未变）
- `examples/drawing/demo_drawing_animation.py` - 演示程序（已移动）

### 文档文件
- `docs/drawing_animation_guide.md` - 详细指南（已更新引用）
- `动态画线快速入门.md` - 快速入门（已更新引用）
- `FEATURE_动态画线跑马灯效果.md` - 功能说明（已更新引用）
- `README_动态画线.md` - 项目总览（已更新引用）

### 启动脚本
- `run_animation_demo.bat` - Windows脚本（已更新）
- `run_animation_demo.sh` - Linux/Mac脚本（已更新）

### 测试文件
- `tests/test_drawing_animation.py` - 单元测试（未变）

## 更新状态

| 文件类型 | 更新状态 | 备注 |
|---------|---------|------|
| 启动脚本 | ✅ 已完成 | bat & sh |
| 文档引用 | ✅ 已完成 | 所有 .md 文件 |
| 核心代码 | ✅ 无需更新 | 路径无关 |
| 测试代码 | ✅ 无需更新 | 使用模块导入 |

## 测试验证

运行以下命令验证更新：

```bash
# 1. 验证启动脚本
.\run_animation_demo.bat

# 2. 验证文档链接
# 打开以下文档，检查示例代码路径
# - 动态画线快速入门.md
# - docs/drawing_animation_guide.md
# - README_动态画线.md

# 3. 验证单元测试
pytest tests/test_drawing_animation.py -v
```

## 完成确认

✅ 所有路径引用已更新
✅ 启动脚本已更新并测试
✅ 文档引用已更新
✅ 功能正常运行

用户可以继续使用原有的启动方式，无需任何修改。

