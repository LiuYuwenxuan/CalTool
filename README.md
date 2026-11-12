# CalTool

一个完全离线的 Windows 桌面日历与工作日计算工具。

## 功能
- 公历/农历双历显示，包含中国法定节假日与调休标记。
- 支持区间工作日/非工作日计算。
- 包含官方纪念日、历史事件与人物纪念（点击查看详情）。
- 完全脱机运行，无需联网。

## 运行环境
需要 Python 3.x 环境。安装依赖：
pip install chinese-calendar borax

运行程序：
python main.py

## 打包
项目包含 `CalTool.spec`，可使用 PyInstaller 打包为独立的 exe 文件：
pyinstaller CalTool.spec
