# 第三方组件与素材

应用界面使用 PySide6 6.11.2 / Qt 6.11，按其 LGPLv3 开源许可使用；组件采用动态链接，完整许可文本随源码位于 assets/licenses，并包含在 EXE 资源中。

- Qt / PySide 项目与源码：https://code.qt.io/cgit/pyside/pyside-setup.git/
- Qt 源码：https://download.qt.io/official_releases/qt/6.11/
- PyInstaller 6.22.3：GPLv2-or-later，包含允许分发打包应用的例外；用于构建 EXE。
- Python 3.11：Python Software Foundation License。

程序源码及语录按项目 LICENSE 提供。12 张风景由内置 image_gen 工具生成，原始提示词保存在 assets/image_prompts.json。它们是主题视觉素材，未作为真实地点标注。

项目同时提供源码、依赖清单与 build.ps1，可通过替换环境中的 Qt / PySide 动态库并重新打包来构建修改版本。
