"""从传奇服务端数据生成爆率查询系统网页的核心逻辑.

数据来源与输出对应关系:
  - Mud2/DB/ApexM2.DB  StdItems 表  -> items.js   (Idx -> Name 映射)
  - Mud2/DB/ApexM2.DB  Monster  表  -> mons.js    (怪物名称列表)
  - Mir200/Envir/MonItems/*.txt      -> monOutput.js (怪物 -> 爆出物品ID列表)
  - Mir200/Envir/MonGen.txt          -> monGen.js   (刷怪记录)
  - Mir200/Envir/MapInfo.txt         -> mapInfo.js / mapGo.js
  - Mir200/Envir/MerChant.txt        -> merchant.js (NPC)
  - 母版模板(assets/)                 -> index.html / index.js / index.css
"""

from __future__ import annotations

import os
import re
import sqlite3
import shutil

# 常见文件编码
GBK = "gbk"
UTF8 = "utf-8"

# ---------------------------------------------------------------------------
# 路径定位
# ---------------------------------------------------------------------------


def find_db_file(server_dir: str) -> str | None:
    """从服务端 Config.ini 或常见路径定位 ApexM2.DB."""
    candidates = [
        os.path.join(server_dir, "Mud2", "DB", "ApexM2.DB"),
        os.path.join(server_dir, "ApexM2.DB"),
    ]
    for c in candidates:
        if os.path.exists(c):
            return c

    # 尝试从 Config.ini 中读取 SqliteDBName
    cfg = os.path.join(server_dir, "Config.ini")
    if os.path.exists(cfg):
        text = _read_text(cfg)
        m = re.search(r"SqliteDB(?:Name|File)\s*=\s*(.+)$", text, re.MULTILINE)
        if m:
            raw = m.group(1).strip().strip('"')
            raw = raw.replace("\\", "/")
            if os.path.exists(raw):
                return raw
            base = os.path.basename(raw)
            cand = os.path.join(server_dir, "Mud2", "DB", base)
            if os.path.exists(cand):
                return cand
    return None


def find_envir_dir(server_dir: str) -> str:
    return os.path.join(server_dir, "Mir200", "Envir")


# ---------------------------------------------------------------------------
# 编码工具
# ---------------------------------------------------------------------------


def _read_text(path: str, encoding: str = GBK) -> str:
    with open(path, "r", encoding=encoding, errors="replace") as f:
        return f.read()


def read_auto(path: str) -> str:
    """优先 GBK，失败退回 UTF-8."""
    try:
        return _read_text(path, GBK)
    except Exception:
        return _read_text(path, UTF8)


# ---------------------------------------------------------------------------
# items.js: 物品数据库
# ---------------------------------------------------------------------------


def build_items_js(db_path: str) -> str:
    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    try:
        rows = conn.execute("SELECT Idx, Name FROM StdItems ORDER BY Idx").fetchall()
    finally:
        conn.close()
    lines = ["let items = {"]
    for idx, name in rows:
        lines.append(f'\t"{idx}":"{name}",')
    lines.append("}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# mons.js: 怪物列表
# ---------------------------------------------------------------------------


def build_mons_js(db_path: str) -> str:
    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    try:
        rows = conn.execute("SELECT Name FROM Monster").fetchall()
    finally:
        conn.close()
    lines = ["let mons = ["]
    for (name,) in rows:
        lines.append(f'\t"{name}",')
    lines.append("]")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# monOutput.js: 怪物爆出物品
# ---------------------------------------------------------------------------


def build_monoutput_js(db_path: str, monitems_dir: str, exclude_names: set[str] | None = None) -> str:
    """读取每个怪物的爆率文件, 把物品名解析成数据库中的 ID.

    解析规则:
      - 跳过空行 / 注释(;) / #CHILD / (  / )
      - 取行内第 2 个 token 作为物品名
      - 名字 -> ID 采用数据库首个匹配(与源工具一致)
      - exclude_names 中列出的物品名会被过滤掉(可选)
    """
    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    try:
        rows = conn.execute("SELECT Idx, Name FROM StdItems ORDER BY Idx").fetchall()
    finally:
        conn.close()
    name2id: dict[str, str] = {}
    for idx, name in rows:
        if name not in name2id:
            name2id[name] = str(idx)

    exclude = exclude_names or set()

    # 怪物列表(与 mons.js 顺序一致)
    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    try:
        mon_rows = conn.execute("SELECT Name FROM Monster").fetchall()
    finally:
        conn.close()

    lines = ["let monOutput = {"]
    for (monname,) in mon_rows:
        ids: list[str] = []
        seen: set[str] = set()
        file_path = os.path.join(monitems_dir, f"{monname}.txt")
        if os.path.exists(file_path):
            for line in read_auto(file_path).split("\n"):
                line = line.strip()
                if not line or line.startswith(";") or line.startswith("#CHILD"):
                    continue
                if line in ("(", ")"):
                    continue
                tokens = line.split()
                if len(tokens) < 2 or "/" not in tokens[0]:
                    continue
                name = tokens[1]
                if name in exclude:
                    continue
                item_id = name2id.get(name)
                if item_id and item_id not in seen:
                    seen.add(item_id)
                    ids.append(item_id)
        lines.append(f'\t"{monname}":`{",".join(ids)}`,')
    lines.append("}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# monGen.js: 刷怪列表
# ---------------------------------------------------------------------------


def build_mongen_js(envir_dir: str) -> str:
    src = os.path.join(envir_dir, "MonGen.txt")
    lines_out = ["let mongen = ["]
    if os.path.exists(src):
        for line in read_auto(src).split("\n"):
            line = line.strip()
            if not line or line.startswith(";"):
                continue
            parts = re.sub(r"[ \t]+", " ", line).split(" ")
            if len(parts) > 3:
                parts[3] = parts[3].upper()
            lines_out.append(f"`{' '.join(parts)}`,")
    lines_out.append("]")
    return "\n".join(lines_out)


# ---------------------------------------------------------------------------
# mapInfo.js + mapGo.js
# ---------------------------------------------------------------------------


def build_mapinfo_and_mapgo(envir_dir: str) -> tuple[str, str, dict[str, str]]:
    src = os.path.join(envir_dir, "MapInfo.txt")
    mapinfo_lines = ["let mapInfo = {"]
    mapgo_lines = ["let mapGo = ["]
    map_info: dict[str, str] = {}
    if os.path.exists(src):
        for raw in read_auto(src).split("\n"):
            line = raw.rstrip("\r\n")
            m = re.match(r"\s*\[([^\]]+)\]", line)
            if m:
                header = m.group(1).strip()
                if "|" in header:
                    left, right = header.split("|", 1)
                    key = left.strip().upper()
                    right_tokens = right.split()
                    value = right_tokens[-1] if right_tokens else key
                else:
                    tokens = header.split()
                    key = tokens[0].upper() if tokens else header
                    value = tokens[1] if len(tokens) > 1 else key
                map_info[key] = value
                mapinfo_lines.append(f'"{key}":`{value}`,')
                continue
            if "->" in line and line.strip():
                parts = line.split("->")
                if len(parts) == 2:
                    trailing = line[len(line.rstrip()):]
                    trailing = re.sub(r"\t", " ", trailing)
                    left = _upper_first_preserve(parts[0].strip())
                    right = _upper_first_preserve(parts[1].strip())
                    mapgo_lines.append(f'"{left} -> {right}{trailing}",')
    mapinfo_lines.append("}")
    mapgo_lines.append("]")
    return "\n".join(mapinfo_lines), "\n".join(mapgo_lines), map_info


def _upper_first_preserve(text: str) -> str:
    """把地图代码(第一个 token)转大写, 并保留尾随空白."""
    leading = len(text) - len(text.lstrip())
    trailing = len(text) - len(text.rstrip())
    body = text[leading:len(text) - trailing] if trailing else text[leading:]
    parts = body.split()
    if parts:
        parts[0] = parts[0].upper()
    return " " * leading + " ".join(parts) + " " * trailing


# ---------------------------------------------------------------------------
# merchant.js: NPC 列表
# ---------------------------------------------------------------------------


def build_merchant_js(envir_dir: str, extra_npc: str | None = None) -> str:
    """extra_npc: 需要插入到指定 NPC 后的额外条目, 格式 "插入在|完整条目".

    与原工具一致: 小灵通 NPC 为内置补充条目。
    """
    src = os.path.join(envir_dir, "MerChant.txt")
    lines = ["let merchant = ["]
    insert_idx: int | None = None
    if os.path.exists(src):
        entries = []
        for line in read_auto(src).split("\n"):
            line = line.strip()
            if not line:
                continue
            entries.append(line.replace("\\", "|"))
        if extra_npc:
            after, value = extra_npc.split("|", 1)
            # 找到最后一个匹配前缀的条目, 在其后插入
            for idx, entry in enumerate(entries):
                if entry.split("|", 1)[0].strip() == after.strip():
                    insert_idx = idx
        for idx, entry in enumerate(entries):
            lines.append(f"`{entry}`,")
            if insert_idx is not None and idx == insert_idx:
                lines.append(f"`{value}`,")
    lines.append("]")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# npcMapGo.js: NPC 脚本地图入口(源工具中为空对象)
# ---------------------------------------------------------------------------


def build_npc_mapgo_js(envir_dir: str, map_info: dict[str, str] | None = None) -> str:
    """扫描 Envir 下 NPC/脚本中的 MapMove 传送命令, 生成 地图 -> 进入方式 映射.

    数据来源:
      - Market_Def/*.txt   (NPC 脚本, 文件名多为 "NPC名-目标地图名.txt")
      - QuestDiary/*.txt   (系统脚本)
    格式: npcMapGo[地图] = ["进入方式描述", ...]
    地图 key 同时兼容 MapMove 目标原名与 mapInfo 显示名.
    """
    map_info = map_info or {}
    entries: dict[str, list[str]] = {}

    def add_entry(target: str, desc: str) -> None:
        # 目标原名 + mapInfo 中所有值为该目标的 key
        keys = {target.upper()}
        for mk, mv in map_info.items():
            if mv == target or mk == target or mk == target.upper():
                keys.add(mk.upper())
                keys.add(mv.upper())
        for k in keys:
            if desc not in entries.setdefault(k, []):
                entries[k].append(desc)

    # merchant 里的 NPC 名 -> (所在地图, x, y, 显示名)
    merchant_info: dict[str, tuple[str, str, str]] = {}
    merchant_path = os.path.join(envir_dir, "MerChant.txt")
    if os.path.exists(merchant_path):
        for line in read_auto(merchant_path).split("\n"):
            line = line.strip()
            if not line:
                continue
            parts = line.replace("\\", "|").split(" ")
            parts = [p for p in parts if p]
            if len(parts) >= 4:
                merchant_info[parts[0]] = (parts[1], parts[2], parts[3])

    script_dirs = ["Market_Def", "QuestDiary"]
    skip_names = {"qfunction", "qmanage", "qmapenent", "qmission", "qchatbox", "qbatter", "守关人"}
    for sub in script_dirs:
        base = os.path.join(envir_dir, sub)
        if not os.path.exists(base):
            continue
        for root, _dirs, files in os.walk(base):
            for fn in files:
                if not fn.lower().endswith(".txt"):
                    continue
                path = os.path.join(root, fn)
                text = read_auto(path)
                moves = re.findall(r"MapMove\s+(\S+)", text, re.IGNORECASE)
                targets = [m for m in moves if not m.startswith("<")]
                if not targets:
                    continue

                # 确定 NPC 名: 优先文件名 "NPC名-xxx", 否则用 merchant 匹配
                rel = os.path.relpath(path, envir_dir).replace("\\", "/")
                fname = fn[:-4]
                npc_cand = fname.split("-")[0].strip()
                if npc_cand.lower() in skip_names:
                    continue
                npc_full = None
                for key in merchant_info:
                    if key.split("|")[-1] == npc_cand:
                        npc_full = key
                        break
                if npc_full:
                    pos = merchant_info[npc_full]
                    label = f"{npc_full}({pos[0]} {pos[1]},{pos[2]})"
                else:
                    label = f"{npc_cand}({rel})"

                for target in targets:
                    desc = f"{label} 传送到{target}"
                    add_entry(target, desc)

    lines = [
        "// Populated from fixed Map and MapMove targets in NPC scripts when available.",
        "let npcMapGo = {",
    ]
    for target in sorted(entries):
        descs = entries[target]
        joined = ", ".join(_js_quote(d) for d in descs)
        lines.append(f'\t"{target}":[{joined}],')
    lines.append("};")
    return "\n".join(lines)


def _js_quote(text: str) -> str:
    """转义 JS 字符串(单引号), 用于数组元素."""
    return "'" + text.replace("\\", "\\\\").replace("'", "\\'") + "'"


# ---------------------------------------------------------------------------
# 读取服务端游戏名
# ---------------------------------------------------------------------------


def read_game_name(server_dir: str) -> str:
    cfg = os.path.join(server_dir, "Config.ini")
    if os.path.exists(cfg):
        text = _read_text(cfg)
        m = re.search(r"GameName\s*=\s*(.+)$", text, re.MULTILINE)
        if m:
            return m.group(1).strip()
    return "查询系统"


# ---------------------------------------------------------------------------
# index.js: 母版注入配置
# ---------------------------------------------------------------------------


def build_index_js(template: str, config: dict) -> str:
    """把配置写入母版 index.js.

    config 支持的键:
      isDbClickMon   bool
      loadJsTime     int
      itemQueryType  int
      monQueryType   int
      mapQueryType   int
      gonglveShow    bool
      isShowMonGenInfo bool
      webTitle       str
      gonglveContent str
    """
    js = template
    replacements = [
        ("isDbClickMon: true,", f"isDbClickMon: {str(config.get('isDbClickMon', True)).lower()},"),
        ("isDbClickMon: false,", f"isDbClickMon: {str(config.get('isDbClickMon', True)).lower()},"),
        ("loadJsTime: 3000,", f"loadJsTime: {int(config.get('loadJsTime', 3000))},"),
        ("itemQueryType: 3,", f"itemQueryType: {int(config.get('itemQueryType', 3))},"),
        ("monQueryType: 4,", f"monQueryType: {int(config.get('monQueryType', 4))},"),
        ("mapQueryType: 3,", f"mapQueryType: {int(config.get('mapQueryType', 3))},"),
        ("gonglveShow: true,", f"gonglveShow: {str(config.get('gonglveShow', True)).lower()},"),
        ("gonglveShow: false,", f"gonglveShow: {str(config.get('gonglveShow', True)).lower()},"),
        ("isShowMonGenInfo: true,", f"isShowMonGenInfo: {str(config.get('isShowMonGenInfo', True)).lower()},"),
        ("isShowMonGenInfo: false,", f"isShowMonGenInfo: {str(config.get('isShowMonGenInfo', True)).lower()},"),
    ]
    for old, new in replacements:
        if old in js:
            js = js.replace(old, new)

    # webTitle
    web_title = config.get("webTitle", "查询系统")
    js = re.sub(r"webTitle:\s*`[^`]*`", f"webTitle:`{web_title}`", js)

    # 攻略内容
    content = config.get("gonglveContent")
    if content is not None:
        js = re.sub(r"gonglveContent:\s*`[^`]*`", "gonglveContent: `" + content + "`", js, flags=re.DOTALL)
    return js


# ---------------------------------------------------------------------------
# 主生成流程
# ---------------------------------------------------------------------------


def generate(
    server_dir: str,
    output_dir: str,
    assets_dir: str,
    config: dict | None = None,
    exclude_names: set[str] | None = None,
    log: callable | None = None,
) -> None:
    """生成完整的查询系统到 output_dir."""
    config = config or {}
    log = log or (lambda msg: None)

    envir_dir = find_envir_dir(server_dir)
    db_path = find_db_file(server_dir)
    if not db_path:
        raise FileNotFoundError(f"未找到 ApexM2.DB (服务端目录: {server_dir})")
    if not os.path.exists(envir_dir):
        raise FileNotFoundError(f"未找到 Mir200/Envir 目录: {envir_dir}")

    monitems_dir = os.path.join(envir_dir, "MonItems")
    os.makedirs(output_dir, exist_ok=True)

    log("读取物品数据库...")
    items_js = build_items_js(db_path)
    log("读取怪物列表...")
    mons_js = build_mons_js(db_path)
    log("解析怪物爆率...")
    monoutput_js = build_monoutput_js(db_path, monitems_dir, exclude_names)
    log("解析刷怪列表...")
    mongen_js = build_mongen_js(envir_dir)
    log("解析地图信息...")
    mapinfo_js, mapgo_js, map_info = build_mapinfo_and_mapgo(envir_dir)
    log("解析 NPC 列表...")
    extra_npc = config.get("extra_npc")
    merchant_js = build_merchant_js(envir_dir, extra_npc)
    npc_mapgo_js = build_npc_mapgo_js(envir_dir, map_info)

    # 母版 -> index 文件
    log("生成 index.html / index.js / index.css ...")
    with open(os.path.join(assets_dir, "template_index.html"), encoding=UTF8) as f:
        html_tpl = f.read()
    with open(os.path.join(assets_dir, "template_index.js"), encoding=UTF8) as f:
        js_tpl = f.read()
    with open(os.path.join(assets_dir, "template_index.css"), encoding=UTF8) as f:
        css_tpl = f.read()

    index_js = build_index_js(js_tpl, config)

    with open(os.path.join(output_dir, "index.html"), "w", encoding=UTF8) as f:
        f.write(html_tpl)
    with open(os.path.join(output_dir, "index.js"), "w", encoding=UTF8) as f:
        f.write(index_js)
    with open(os.path.join(output_dir, "index.css"), "w", encoding=UTF8) as f:
        f.write(css_tpl)

    # 数据文件
    data_files = {
        "items.js": items_js,
        "mons.js": mons_js,
        "monOutput.js": monoutput_js,
        "monGen.js": mongen_js,
        "mapInfo.js": mapinfo_js,
        "mapGo.js": mapgo_js,
        "merchant.js": merchant_js,
        "npcMapGo.js": npc_mapgo_js,
    }
    for fname, content in data_files.items():
        with open(os.path.join(output_dir, fname), "w", encoding=UTF8) as f:
            f.write(content)

    # 复制静态资源
    log("复制前端资源...")
    dst_assets = os.path.join(output_dir, "assets")
    os.makedirs(dst_assets, exist_ok=True)
    for name in os.listdir(assets_dir):
        src = os.path.join(assets_dir, name)
        if name.startswith("template_"):
            continue
        if os.path.isfile(src):
            shutil.copy2(src, os.path.join(dst_assets, name))

    shutil.copy2(os.path.join(assets_dir, "favicon.ico"), os.path.join(output_dir, "favicon.ico"))

    # 复制 MonItems 目录 (保持原编码)
    log("复制怪物爆率文件...")
    if os.path.exists(monitems_dir):
        dst_mon = os.path.join(output_dir, "MonItems")
        os.makedirs(dst_mon, exist_ok=True)
        for name in os.listdir(monitems_dir):
            src = os.path.join(monitems_dir, name)
            if os.path.isfile(src):
                shutil.copy2(src, os.path.join(dst_mon, name))

    # 复制完整地图文件(供页面上"完整地图文件"链接使用)
    src_mapinfo = os.path.join(envir_dir, "MapInfo.txt")
    if os.path.exists(src_mapinfo):
        shutil.copy2(src_mapinfo, os.path.join(output_dir, "MapInfo.txt"))

    log("生成完成!")
