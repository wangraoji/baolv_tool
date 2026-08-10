# baolv_tool 爆率查询一键生成

从传奇(Mir)服务端数据生成一套静态"爆率查询系统"网页，功能等价于原易语言工具《爆率查询一键编译》。

## 功能

- 读取服务端 `ApexM2.DB`(物品/怪物)、`MonItems`(爆率)、`MonGen.txt`(刷怪)、`MapInfo.txt`(地图/走法)、`MerChant.txt`(NPC)
- 生成 `index.html` + 数据 JS 文件，支持：
  - 物品查询(查出处)
  - 怪物查询(查产出、刷新地)
  - 地图查询(刷怪、NPC、走法)
  - NPC 查询
  - 版本攻略
- 可配置查询类型、过滤物品、网站标题、攻略内容

## 运行

```bash
python3 main.py
```

依赖：仅 Python 标准库(tkinter / sqlite3)，无第三方依赖。

## 打包成 exe / app

本地打包:

```bash
pyinstaller --onefile --windowed --name baolv_tool main.py
```

GitHub Actions 已配置自动打包 Windows `.exe`，推送 `main` 分支后在 Actions 的
Artifact 中下载。

## 目录结构

```
baolv_tool/
├── main.py               # 入口
├── baolv_tool/
│   ├── gui.py            # tkinter 界面
│   ├── generator.py      # 数据解析 + 网页生成
│   └── assets/           # 前端资源(Vue3 + Element Plus)与母版模板
```

## 与原始工具的数据对应

| 生成文件 | 数据来源 |
|---------|---------|
| items.js | ApexM2.DB StdItems 表 |
| mons.js | ApexM2.DB Monster 表 |
| monOutput.js | Mir200/Envir/MonItems/*.txt |
| monGen.js | Mir200/Envir/MonGen.txt |
| mapInfo.js / mapGo.js | Mir200/Envir/MapInfo.txt |
| merchant.js | Mir200/Envir/MerChant.txt |
