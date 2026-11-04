# Windows 运行时资源

- 原生代码修改后执行根目录 `编译.bat`，检查 `bin/neutralino-win_x64.exe` 是否生成。
- 根目录 `换图标、添加版本信息.bat` 保留四款应用的完整图标写入、版本资源编译和运行时复制步骤，不改成其他脚本的入口。
- 编译和资源脚本禁止执行测试；测试放在 `spec/`，通过 `python -m unittest discover -s spec -p "*_test.py"` 单独运行。
- 独立工作区构建时，通过 `DLCV_PLATFORM_WORKTREE`、`DLCV_STUDIO_WORKTREE`、`DLCV_TRAIN_WORKTREE`、`DLCV_TEST_WORKTREE` 指定四个复制目标的项目根目录；未设置时使用同级常规项目目录。新增应用时增加图标、版本信息和复制目标。
