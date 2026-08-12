"""极简 Access(.mdb) 数据库读取器(纯标准库, 无第三方依赖).

基于 access_parser 的逻辑, 用 struct 直接解析 Jet 数据库格式.
仅支持读取, 满足爆率工具读取 StdItems/Monster 表的需求.
"""

from __future__ import annotations

import struct
from collections import defaultdict

# 页面大小
PAGE_SIZE_V3 = 0x800   # 2048
PAGE_SIZE_V4 = 0x1000  # 4096

# 版本
VERSION_3 = 0x00
VERSION_4 = 0x01
VERSION_5 = 0x02
VERSION_2010 = 0x03

# 类型
TYPE_BOOLEAN = 1
TYPE_INT8 = 2
TYPE_INT16 = 3
TYPE_INT32 = 4
TYPE_MONEY = 5
TYPE_FLOAT32 = 6
TYPE_FLOAT64 = 7
TYPE_DATETIME = 8
TYPE_BINARY = 9
TYPE_TEXT = 10
TYPE_OLE = 11
TYPE_MEMO = 12
TYPE_GUID = 15
TYPE_96_bit_17_BYTES = 16
TYPE_COMPLEX = 18

TABLE_PAGE_MAGIC = b"\x02\x01"
DATA_PAGE_MAGIC = b"\x01\x01"

# 系统表 flag: 不解析这些表
SYSTEM_TABLE_FLAGS = {0, 1, 2, 3, 4, 5, 6, 7}


class _Column:
    __slots__ = (
        "type", "column_id", "variable_column_number", "column_index",
        "fixed_length", "fixed_offset", "name",
    )

    def __init__(self):
        self.type = 0
        self.column_id = 0
        self.variable_column_number = 0
        self.column_index = 0
        self.fixed_length = True
        self.fixed_offset = 0
        self.name = ""


def _parse_header(db_data: bytes):
    """解析文件头, 返回 (version, page_size).

    version 为映射后的值: 3 / 4 / 5 / 2010.
    """
    if len(db_data) < 0x20:
        raise ValueError("无效的 Access 数据库文件")
    # ACCESSHEADER: 4字节 magic + jet_string + Int32ul jet_version
    # magic = \x00\x01\x00\x00
    magic = db_data[:4]
    if magic != b"\x00\x01\x00\x00":
        raise ValueError("不是有效的 Access(.mdb) 数据库")
    # jet_string 是 \x00 结尾字符串
    end = db_data.find(b"\x00", 4)
    if end == -1:
        raise ValueError("无法解析 Access 数据库头")
    # jet_version 在 jet_string 之后, 即 end+1 位置(4字节 little-endian)
    ver_offset = end + 1
    if ver_offset + 4 > len(db_data):
        raise ValueError("无法解析 Access 数据库版本")
    version_raw = struct.unpack_from("<I", db_data, ver_offset)[0]
    if version_raw == VERSION_3:
        return 3, PAGE_SIZE_V3
    if version_raw == VERSION_4:
        return 4, PAGE_SIZE_V4
    if version_raw == VERSION_5:
        return 5, PAGE_SIZE_V4
    if version_raw == VERSION_2010:
        return 2010, PAGE_SIZE_V4
    return 3, PAGE_SIZE_V3


def _categorize_pages(db_data: bytes, page_size: int):
    """把数据库分成数据页和表定义页."""
    data_pages = {}
    table_defs = {}
    n = len(db_data)
    off = 0
    while off < n:
        page = db_data[off:off + page_size]
        if page.startswith(DATA_PAGE_MAGIC):
            data_pages[off] = page
        elif page.startswith(TABLE_PAGE_MAGIC):
            table_defs[off] = page
        off += page_size
    return table_defs, data_pages


def _parse_tdef_header(buffer: bytes, version: int):
    """解析表定义页头."""
    pos = 0
    magic = buffer[pos:pos + 2]
    pos += 2
    if magic != TABLE_PAGE_MAGIC:
        raise ValueError("无效的表定义页")
    pos += 2  # tdef_ver (2字节, 或 "VC")
    next_page_ptr = struct.unpack_from("<I", buffer, pos)[0]
    pos += 4
    # header_end 是 Tell, 不占字节
    # table_definition_length
    table_definition_length = struct.unpack_from("<I", buffer, pos)[0]
    pos += 4
    if version > 3:
        pos += 4  # ver4_unknown
    number_of_rows = struct.unpack_from("<I", buffer, pos)[0]
    pos += 4
    pos += 4  # autonumber
    if version > 3:
        pos += 4  # autonumber_increment
        pos += 4  # complex_autonumber
        pos += 4  # ver4_unknown_1
        pos += 4  # ver4_unknown_2
    table_type_flags = buffer[pos]
    pos += 1
    next_column_id = struct.unpack_from("<H", buffer, pos)[0]
    pos += 2
    variable_columns = struct.unpack_from("<H", buffer, pos)[0]
    pos += 2
    column_count = struct.unpack_from("<H", buffer, pos)[0]
    pos += 2
    index_count = struct.unpack_from("<I", buffer, pos)[0]
    pos += 4
    real_index_count = struct.unpack_from("<I", buffer, pos)[0]
    pos += 4
    row_page_map = struct.unpack_from("<I", buffer, pos)[0]
    pos += 4
    free_space_page_map = struct.unpack_from("<I", buffer, pos)[0]
    pos += 4
    tdef_header_end = pos

    return {
        "next_page_ptr": next_page_ptr,
        "number_of_rows": number_of_rows,
        "table_type_flags": table_type_flags,
        "variable_columns": variable_columns,
        "column_count": column_count,
        "index_count": index_count,
        "real_index_count": real_index_count,
        "tdef_header_end": tdef_header_end,
    }


def _parse_column(buffer: bytes, version: int, pos: int):
    """解析单个列定义(COLUMN 结构), 返回 (column, new_pos)."""
    col = _Column()
    col.type = buffer[pos]
    pos += 1
    if version > 3:
        pos += 4  # ver4_unknown_3
    col.column_id = struct.unpack_from("<H", buffer, pos)[0]
    pos += 2
    col.variable_column_number = struct.unpack_from("<H", buffer, pos)[0]
    pos += 2
    col.column_index = struct.unpack_from("<H", buffer, pos)[0]
    pos += 2
    # various 字段: 各类型长度
    t = col.type
    various_size = 6 if version == 3 else 4
    if t in (9, 10, 11, 12, 16, 1, 2, 3, 4, 5, 6, 7, 8, 17, 18):
        pass  # 有 various
    pos += various_size
    # column_flags: 1字节(v3) 或 2字节(v4), construct BitStruct 高位优先
    # fixed_length 是最低位(bit0)
    flags = buffer[pos]
    pos += 1
    if version > 3:
        pos += 1
    col.fixed_length = bool(flags & 0x01)
    if version > 3:
        pos += 4  # ver4_unknown_4
    col.fixed_offset = struct.unpack_from("<H", buffer, pos)[0]
    pos += 2
    col_len = struct.unpack_from("<H", buffer, pos)[0]
    pos += 2
    return col, pos


def _parse_table_columns(buffer: bytes, version: int, column_count: int, index_count: int = 0, real_index_count: int = 0):
    """从表定义数据中解析列 (完整结构: real_index + column + column_names + ...).

    返回 {column_index: _Column}.
    """
    pos = 0
    # real_index: 每个 8 字节 (v3) 或 12 字节 (v4)
    for _ in range(real_index_count):
        pos += 8
        if version > 3:
            pos += 4

    # column: COLUMN 结构
    columns_raw = []
    for _ in range(column_count):
        try:
            col, pos = _parse_column(buffer, version, pos)
        except (struct.error, IndexError):
            break
        columns_raw.append(col)

    # 用 column_index(去offset) 作 key; 若不唯一则用 column_id (模仿 access_parser)
    if columns_raw:
        offset = min(x.column_index for x in columns_raw)
        columns = {x.column_index - offset: x for x in columns_raw}
        if len(columns) != len(columns_raw):
            columns = {x.column_id: x for x in columns_raw}
    else:
        columns = {}

    # column_names: COLUMN_NAMES 数组, 把名字赋给列(按原始顺序)
    for col in columns_raw:
        try:
            if version == 3:
                name_len = buffer[pos]
                pos += 1
                name = buffer[pos:pos + name_len].decode("ascii", errors="ignore")
                pos += name_len
            else:
                name_len = struct.unpack_from("<H", buffer, pos)[0]
                pos += 2
                name = buffer[pos:pos + name_len].decode("utf-16-le", errors="ignore")
                pos += name_len
            col.name = name.rstrip("\x00")
        except (struct.error, IndexError):
            break

    # 其余(real_index_2, all_indexes, index_names) 不需要列定义, 跳过
    return columns


def _parse_data_page_header(buffer: bytes, version: int):
    """解析数据页头, 返回 (record_count, record_offsets)."""
    pos = 0
    magic = buffer[pos:pos + 2]
    pos += 2
    if magic != DATA_PAGE_MAGIC:
        raise ValueError("无效的数据页")
    pos += 2  # data_free_space
    pos += 4  # owner
    if version > 3:
        pos += 4  # ver4_unknown_dat1
    record_count = struct.unpack_from("<H", buffer, pos)[0]
    pos += 2
    offsets = []
    for _ in range(record_count):
        off = struct.unpack_from("<H", buffer, pos)[0]
        pos += 2
        offsets.append(off)
    return record_count, offsets


def _parse_type(data_type: int, buffer: bytes, length: int = 0, version: int = 3):
    """解析单个字段值."""
    if data_type == TYPE_INT8:
        if len(buffer) < 1:
            return None
        return struct.unpack_from("<b", buffer)[0]
    if data_type == TYPE_INT16:
        if len(buffer) < 2:
            return None
        return struct.unpack_from("<h", buffer)[0]
    if data_type in (TYPE_INT32, TYPE_COMPLEX):
        if len(buffer) < 4:
            return None
        return struct.unpack_from("<i", buffer)[0]
    if data_type == TYPE_MONEY:
        if len(buffer) < 8:
            return None
        return struct.unpack_from("<q", buffer)[0]
    if data_type == TYPE_FLOAT32:
        if len(buffer) < 4:
            return None
        return struct.unpack_from("<f", buffer)[0]
    if data_type == TYPE_FLOAT64:
        if len(buffer) < 8:
            return None
        return struct.unpack_from("<d", buffer)[0]
    if data_type == TYPE_DATETIME:
        if len(buffer) < 8:
            return None
        return struct.unpack_from("<q", buffer)[0]
    if data_type == TYPE_TEXT:
        if length and length > 0:
            buf = buffer[:length]
        else:
            buf = buffer
        if version > 3:
            text = buf.decode("utf-16-le", errors="ignore")
        else:
            text = buf.decode("gbk", errors="ignore")
        return text.replace("\x00", "")
    if data_type == TYPE_BOOLEAN:
        return None
    # 其它类型返回原始字节
    return buffer


def read_table(db_path: str, table_name: str) -> dict:
    """读取 Access 数据库中的表, 返回 {列名: [值, ...]}."""
    with open(db_path, "rb") as f:
        db_data = f.read()

    version, page_size = _parse_header(db_data)
    table_defs, data_pages = _categorize_pages(db_data, page_size)

    # 1. 先解析 MSysObjects 目录获取表名 -> id
    # MSysObjects 表定义在 offset 2*page_size, 其数据页通过 owner 关联
    catalog_page_key = 2 * page_size
    catalog = None
    try:
        catalog = _read_table_data(
            db_data, version, page_size, table_defs, data_pages, catalog_page_key
        )
    except KeyError:
        catalog = None

    # 2. 找到目标表
    table_id = None
    if catalog and "Name" in catalog and "Id" in catalog:
        names = catalog["Name"]
        ids = catalog["Id"]
        for name, tid in zip(names, ids):
            if name == table_name:
                table_id = tid
                break

    if table_id is None:
        raise KeyError(f"表中未找到: {table_name}")

    table_offset = table_id * page_size
    return _read_table_data(
        db_data, version, page_size, table_defs, data_pages, table_offset
    )


def _read_table_data(db_data, version, page_size, table_defs, data_pages, table_offset):
    """读取指定偏移的表."""
    # 找该表的所有数据页
    linked_pages = []
    for offset, page in data_pages.items():
        try:
            _rc, _offs = _parse_data_page_header(page, version)
        except ValueError:
            continue
        # owner 字段在 header 中: magic(2)+data_free_space(2)=offset 4
        owner = struct.unpack_from("<I", page, 4)[0]
        if owner * page_size == table_offset:
            linked_pages.append(page)

    if not linked_pages:
        return defaultdict(list)

    # 解析表定义获取列
    tdef = table_defs.get(table_offset)
    if not tdef:
        raise KeyError(f"表定义不存在: offset {table_offset}")

    header = _parse_tdef_header(tdef, version)
    merged = tdef[header["tdef_header_end"]:]
    # 处理跨页表定义
    nxt = header["next_page_ptr"]
    while nxt:
        tdef2 = table_defs.get(nxt * page_size)
        if not tdef2:
            break
        h2 = _parse_tdef_header(tdef2, version)
        merged += tdef2[h2["tdef_header_end"]:]
        nxt = h2["next_page_ptr"]

    columns = _parse_table_columns(
        merged, version, header["column_count"],
        header["index_count"], header["real_index_count"],
    )
    if not columns:
        return defaultdict(list)

    # 解析数据
    parsed = defaultdict(list)
    for page in linked_pages:
        try:
            record_count, offsets = _parse_data_page_header(page, version)
        except ValueError:
            continue
        last_offset = None
        for rec_offset in offsets:
            if rec_offset & 0x8000:
                last_offset = rec_offset & 0xfff
                continue
            if rec_offset & 0x4000:
                continue  # overflow 页, 简化跳过
            if rec_offset >= len(page):
                continue
            if not last_offset:
                record = page[rec_offset:]
            else:
                record = page[rec_offset:last_offset]
            last_offset = rec_offset
            _parse_record(record, version, header, columns, parsed)
    return parsed


def _parse_record(record: bytes, version: int, header: dict, columns: dict, parsed: dict):
    """解析一行记录 (完整实现: 固定字段 + 动态字段)."""
    if not record:
        return
    column_count = header["column_count"]
    null_table_len = (column_count + 7) // 8
    if null_table_len > len(record):
        return

    null_table = record[-null_table_len:]
    null_table_bits = []
    for i in range(null_table_len * 8):
        null_table_bits.append(bool(null_table[i // 8] & (1 << (i % 8))))
    null_table_bits = null_table_bits[:column_count]

    # 跳过字段计数(2字节 v4 / 1字节 v3)
    body = record
    if version > 3:
        body = record[2:]
    else:
        body = record[1:]

    # 固定长度字段
    relative_cols = {}
    for idx, col in columns.items():
        if col.fixed_length:
            _parse_fixed_field(body, col, null_table_bits, parsed, version)
        else:
            relative_cols[idx] = col

    # 动态长度字段
    if relative_cols:
        _parse_dynamic_fields(record, body, null_table_len, version, header, relative_cols, null_table_bits, parsed)


def _parse_fixed_field(body: bytes, col: _Column, null_table_bits: list, parsed: dict, version: int):
    """解析单个固定长度字段."""
    has_value = True
    if col.column_id < len(null_table_bits):
        has_value = null_table_bits[col.column_id]
    if not has_value:
        parsed[col.name].append(None)
        return
    if col.fixed_offset >= len(body):
        parsed[col.name].append(None)
        return
    val = _parse_type(col.type, body[col.fixed_offset:], 0, version)
    parsed[col.name].append(val)


def _parse_dynamic_fields(record, body, null_table_len, version, header, relative_cols, null_table_bits, parsed):
    """解析动态长度字段."""
    # 元数据在记录尾部(倒序)
    reverse_record = record[::-1]
    if version > 3:
        reverse_record = reverse_record[null_table_len:]
        # 变长字段计数(v4: 2字节, 大端 Int16ub)
        if len(reverse_record) < 2:
            return
        field_count = struct.unpack_from(">H", reverse_record)[0]
        pos = 2
        # 变长字段偏移数组(每个2字节, 大端)
        offsets = []
        for _ in range(field_count):
            if pos + 2 > len(reverse_record):
                break
            off = struct.unpack_from(">H", reverse_record, pos)[0]
            pos += 2
            offsets.append(off)
        # var_len_count(v4: 2字节, 大端)
        if pos + 2 > len(reverse_record):
            return
        var_len_count = struct.unpack_from(">H", reverse_record, pos)[0]
    else:
        reverse_record = reverse_record[null_table_len:]
        if len(reverse_record) < 1:
            return
        field_count = reverse_record[0]
        pos = 1
        jump_table_cnt = (len(record) - 1) // 256
        jump_table = []
        for _ in range(jump_table_cnt):
            if pos >= len(reverse_record):
                break
            jump_table.append(reverse_record[pos])
            pos += 1
        offsets = []
        for _ in range(field_count):
            if pos >= len(reverse_record):
                break
            offsets.append(reverse_record[pos])
            pos += 1
        if pos >= len(reverse_record):
            return
        var_len_count = reverse_record[pos]

    # 动态字段按 offsets 解析
    # 动态字段按 variable_column_number 排序(与 offsets 数组对应)
    sorted_cols = sorted(relative_cols.items(), key=lambda kv: kv[1].variable_column_number)
    for i, (idx, col) in enumerate(sorted_cols):
        has_value = True
        if col.column_id < len(null_table_bits):
            has_value = null_table_bits[col.column_id]
        if not has_value:
            parsed[col.name].append(None)
            continue
        if i >= len(offsets):
            break
        rel_start = offsets[i]
        if i + 1 == len(offsets):
            rel_end = var_len_count
        else:
            rel_end = offsets[i + 1]
        if rel_start == rel_end:
            parsed[col.name].append("")
            continue
        data = record[rel_start:rel_end]
        val = _parse_type(col.type, data, len(data), version)
        parsed[col.name].append(val)


def _estimate_size(data_type: int, buffer: bytes, version: int) -> int:
    """估算字段占用字节数(用于偏移推进)."""
    if data_type == TYPE_INT8 or data_type == TYPE_BOOLEAN:
        return 1
    if data_type == TYPE_INT16:
        return 2
    if data_type in (TYPE_INT32, TYPE_COMPLEX):
        return 4
    if data_type in (TYPE_MONEY, TYPE_DATETIME, TYPE_FLOAT64):
        return 8
    if data_type == TYPE_FLOAT32:
        return 4
    if data_type == TYPE_TEXT:
        if version > 3:
            # utf-16, 双字节; 取前2字节长度
            if len(buffer) >= 2:
                ln = struct.unpack_from("<H", buffer)[0]
                return ln
            return 2
        else:
            if len(buffer) >= 1:
                return buffer[0]
            return 1
    return 1
