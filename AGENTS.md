# Windows 运行时资源

- 原生代码修改后执行根目录 `编译.bat`，检查 `bin/neutralino-win_x64.exe` 是否生成。
- 根目录 `换图标、添加版本信息.bat` 只调用 `scripts/runtime_resources.py` 生成正式图标、版本资源和运行时文件，不加入或调用测试。
- 只生成指定应用时使用 `--app platform|train|test|studio --output <目标 bin 目录>`，输出目录必须已经存在，使用已确认的独立工作区。无参数时生成四个应用并沿用现有项目复制路径。
- 编译和资源脚本禁止执行测试；测试放在 `spec/`，通过 `python -m unittest discover -s spec -p "*_test.py"` 单独运行。
- 目标项目目录变化时，更新 `scripts/runtime_resources.py` 中的复制路径；新增应用时增加图标、版本信息和复制目标。
