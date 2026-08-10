"""tkinter 图形界面."""

from __future__ import annotations

import os
import queue
import sys
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from . import generator

APP_NAME = "爆率查询一键生成"

DEFAULT_EXCLUDE = (
    "金钥匙,天之屠龙,龙牙,逍遥扇,怒斩,黄金开天,海边月,七星刀,苹果,封魔剑,"
    "乾坤剑,斩魔魔剑,绝息之锋,黑暗使者称号卷,虎卫堂探险家称号卷"
)

# 与原工具一致: 小灵通 NPC 为内置补充条目(插入在 大雄宝殿|神魂颠倒 之后)
DEFAULT_EXTRA_NPC = "大雄宝殿|大雄宝殿|小灵通 大雄宝殿 23 34 \u3000 0 11046 0"


class MainApp:
    def __init__(self, root: tk.Tk, assets_dir: str) -> None:
        self.root = root
        self.assets_dir = assets_dir
        self.log_queue: queue.Queue[str] = queue.Queue()

        root.title(APP_NAME)
        root.geometry("720x560")
        root.minsize(640, 480)

        self._build_ui()
        self._poll_log()

    # ------------------------------------------------------------------
    # UI 构建
    # ------------------------------------------------------------------
    def _build_ui(self) -> None:
        pad = {"padx": 8, "pady": 4}

        # 服务端目录
        row = ttk.Frame(self.root)
        row.pack(fill="x", **pad)
        ttk.Label(row, text="服务端目录:").pack(side="left")
        self.server_var = tk.StringVar()
        entry = ttk.Entry(row, textvariable=self.server_var)
        entry.pack(side="left", fill="x", expand=True, padx=4)
        ttk.Button(row, text="选择...", command=self._pick_server).pack(side="left")

        # 输出目录
        row = ttk.Frame(self.root)
        row.pack(fill="x", **pad)
        ttk.Label(row, text="输出目录:").pack(side="left")
        self.output_var = tk.StringVar()
        entry = ttk.Entry(row, textvariable=self.output_var)
        entry.pack(side="left", fill="x", expand=True, padx=4)
        ttk.Button(row, text="选择...", command=self._pick_output).pack(side="left")

        # 网站标题
        row = ttk.Frame(self.root)
        row.pack(fill="x", **pad)
        ttk.Label(row, text="网站标题:").pack(side="left")
        self.title_var = tk.StringVar(value="查询系统")
        ttk.Entry(row, textvariable=self.title_var).pack(side="left", fill="x", expand=True)

        # 查询类型配置
        cfg = ttk.LabelFrame(self.root, text="查询选项")
        cfg.pack(fill="x", **pad)

        self.item_query = tk.IntVar(value=3)
        self.mon_query = tk.IntVar(value=4)
        self.map_query = tk.IntVar(value=3)
        self.dbl_click = tk.BooleanVar(value=True)
        self.show_mon_gen = tk.BooleanVar(value=True)
        self.show_gonglve = tk.BooleanVar(value=True)

        ttk.Label(cfg, text="物品查询:").grid(row=0, column=0, sticky="w", padx=4, pady=2)
        ttk.Combobox(
            cfg,
            textvariable=self.item_query,
            values=[1, 2, 3],
            width=6,
            state="readonly",
        ).grid(row=0, column=1, sticky="w")
        ttk.Label(cfg, text="怪物查询:").grid(row=0, column=2, sticky="w", padx=4)
        ttk.Combobox(
            cfg,
            textvariable=self.mon_query,
            values=[1, 2, 3, 4],
            width=6,
            state="readonly",
        ).grid(row=0, column=3, sticky="w")
        ttk.Label(cfg, text="地图查询:").grid(row=0, column=4, sticky="w", padx=4)
        ttk.Combobox(
            cfg,
            textvariable=self.map_query,
            values=[1, 2, 3],
            width=6,
            state="readonly",
        ).grid(row=0, column=5, sticky="w")

        ttk.Checkbutton(cfg, text="双击查看爆率", variable=self.dbl_click).grid(
            row=1, column=0, columnspan=2, sticky="w", padx=4
        )
        ttk.Checkbutton(cfg, text="显示刷怪坐标", variable=self.show_mon_gen).grid(
            row=1, column=2, columnspan=2, sticky="w", padx=4
        )
        ttk.Checkbutton(cfg, text="显示版本攻略", variable=self.show_gonglve).grid(
            row=1, column=4, columnspan=2, sticky="w", padx=4
        )

        # 过滤物品
        row = ttk.LabelFrame(self.root, text="过滤物品 (用逗号分隔, 这些物品不会出现在爆率查询中)")
        row.pack(fill="both", expand=True, **pad)
        self.exclude_text = tk.Text(row, height=4)
        self.exclude_text.pack(fill="both", expand=True, padx=4, pady=4)
        self.exclude_text.insert("1.0", DEFAULT_EXCLUDE)

        # 额外 NPC(内置补充)
        self.extra_npc = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            self.root,
            text="补充内置 NPC 条目 (小灵通等)",
            variable=self.extra_npc,
        ).pack(anchor="w", **pad)

        # 攻略内容
        row = ttk.LabelFrame(self.root, text="版本攻略内容 (留空则不生成攻略, 显示版本攻略时生效)")
        row.pack(fill="both", expand=True, **pad)
        self.gonglve_text = tk.Text(row, height=5)
        self.gonglve_text.pack(fill="both", expand=True, padx=4, pady=4)

        # 日志
        row = ttk.LabelFrame(self.root, text="日志")
        row.pack(fill="both", expand=True, **pad)
        self.log_text = tk.Text(row, height=8, state="disabled")
        self.log_text.pack(fill="both", expand=True, padx=4, pady=4)

        # 生成按钮
        ttk.Button(self.root, text="生成查询系统", command=self._on_generate).pack(
            fill="x", **pad
        )

    # ------------------------------------------------------------------
    # 事件
    # ------------------------------------------------------------------
    def _pick_server(self) -> None:
        path = filedialog.askdirectory(title="选择传奇服务端目录")
        if path:
            self.server_var.set(path)
            if not self.output_var.get():
                self.output_var.set(os.path.join(path, "查询系统"))
            game = generator.read_game_name(path)
            if game:
                self.title_var.set(f"{game}查询系统")

    def _pick_output(self) -> None:
        path = filedialog.askdirectory(title="选择输出目录")
        if path:
            self.output_var.set(path)

    def _on_generate(self) -> None:
        server_dir = self.server_var.get().strip()
        output_dir = self.output_var.get().strip()
        if not server_dir:
            messagebox.showwarning(APP_NAME, "请选择服务端目录")
            return
        if not output_dir:
            messagebox.showwarning(APP_NAME, "请选择输出目录")
            return

        exclude_text = self.exclude_text.get("1.0", "end").strip()
        exclude_names = {n.strip() for n in exclude_text.split(",") if n.strip()}

        config = {
            "isDbClickMon": self.dbl_click.get(),
            "loadJsTime": 3000,
            "itemQueryType": self.item_query.get(),
            "monQueryType": self.mon_query.get(),
            "mapQueryType": self.map_query.get(),
            "gonglveShow": self.show_gonglve.get(),
            "isShowMonGenInfo": self.show_mon_gen.get(),
            "webTitle": self.title_var.get().strip() or "查询系统",
        }
        if self.extra_npc.get():
            config["extra_npc"] = DEFAULT_EXTRA_NPC
        content = self.gonglve_text.get("1.0", "end").rstrip("\n")
        if content.strip():
            config["gonglveContent"] = content

        self._set_ui_enabled(False)
        threading.Thread(
            target=self._worker,
            args=(server_dir, output_dir, config, exclude_names),
            daemon=True,
        ).start()

    def _worker(self, server_dir: str, output_dir: str, config: dict, exclude_names: set[str]) -> None:
        def log(msg: str) -> None:
            self.log_queue.put(msg)

        try:
            generator.generate(
                server_dir=server_dir,
                output_dir=output_dir,
                assets_dir=self.assets_dir,
                config=config,
                exclude_names=exclude_names,
                log=log,
            )
            self.log_queue.put("__DONE_OK__")
        except Exception as exc:  # noqa: BLE001
            self.log_queue.put(f"__ERROR__:{exc}")

    # ------------------------------------------------------------------
    # 日志轮询
    # ------------------------------------------------------------------
    def _poll_log(self) -> None:
        try:
            while True:
                msg = self.log_queue.get_nowait()
                if msg == "__DONE_OK__":
                    self._log("=== 生成完成 ===")
                    self._set_ui_enabled(True)
                    messagebox.showinfo(APP_NAME, "生成完成!")
                    continue
                if msg.startswith("__ERROR__:"):
                    self._log("=== 生成失败: " + msg[len("__ERROR__:"):] + " ===")
                    self._set_ui_enabled(True)
                    continue
                self._log(msg)
        except queue.Empty:
            pass
        self.root.after(100, self._poll_log)

    def _log(self, msg: str) -> None:
        self.log_text.configure(state="normal")
        self.log_text.insert("end", msg + "\n")
        self.log_text.see("end")
        self.log_text.configure(state="disabled")

    def _set_ui_enabled(self, enabled: bool) -> None:
        state = "normal" if enabled else "disabled"
        for child in self.root.winfo_children():
            try:
                child.configure(state=state)
            except tk.TclError:
                pass


def _resource_base() -> str:
    """返回资源根目录: 源码运行时为包目录, 打包后为 _MEIPASS."""
    if getattr(sys, "frozen", False):
        return getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.dirname(os.path.abspath(__file__))


def main() -> None:
    root = tk.Tk()
    assets_dir = os.path.join(_resource_base(), "assets")
    MainApp(root, assets_dir)
    root.mainloop()


if __name__ == "__main__":
    main()
