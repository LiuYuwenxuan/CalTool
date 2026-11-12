import tkinter as tk
import tkinter.font as tkfont
from tkinter import messagebox
from datetime import date, timedelta
import calendar
import re
from borax.calendars.lunardate import LunarDate
from chinese_calendar import is_holiday, get_holiday_detail
import calendar_data as D
import person_data as P


class CalendarApp:
    BASE_W, BASE_H = 780, 900
    MIN_W, MIN_H = 640, 700
    RESIZE_BORDER = 4

    def __init__(self, root):
        self.root = root
        self.root.title("时间看板与工作日计算工具")
        self.root.geometry(f"{self.BASE_W}x{self.BASE_H}")
        self.root.overrideredirect(True)
        self.bg = "#f5f5f5"
        self.root.configure(bg=self.bg)
        self._init_fonts()
        self.today = date.today()
        self.current_year, self.current_month = self.today.year, self.today.month
        self.target_highlight_date = None
        self.pinned_event_date = None
        self._current_scale = 1.0
        self._maximized = False
        self._pre_max_geo = None
        self._create_title_bar()
        self._create_content()
        self._create_resize_handles()
        self.root.bind("<Configure>", self._on_root_configure)
        self.draw_calendar(self.current_year, self.current_month)
        self.update_dashboard()
        self._refresh_history_display()

    def _init_fonts(self):
        self.fonts = {
            "title":         tkfont.Font(family=D.FONT_CN_BOLD, size=11),
            "title_num":     tkfont.Font(family=D.FONT_NUM, size=14, weight="bold"),
            "title_cn":      tkfont.Font(family=D.FONT_CN_BOLD, size=14),
            "week":          tkfont.Font(family=D.FONT_CN_BOLD, size=11),
            "day":           tkfont.Font(family=D.FONT_NUM, size=10, weight="bold"),
            "lunar":         tkfont.Font(family=D.FONT_CN_PLAIN, size=10),
            "festival":      tkfont.Font(family=D.FONT_CN_BOLD, size=10),
            "badge":         tkfont.Font(family=D.FONT_CN_BOLD, size=8),
            "dot":           tkfont.Font(family="Arial", size=7),
            "dash_cn":       tkfont.Font(family=D.FONT_CN_PLAIN, size=11),
            "dash_num":      tkfont.Font(family=D.FONT_NUM, size=11),
            "dash_bold_cn":  tkfont.Font(family=D.FONT_CN_BOLD, size=11),
            "dash_bold_num": tkfont.Font(family=D.FONT_NUM, size=11, weight="bold"),
            "small_cn":      tkfont.Font(family=D.FONT_CN_PLAIN, size=10),
            "small_num":     tkfont.Font(family=D.FONT_NUM, size=10),
            "btn":           tkfont.Font(family=D.FONT_CN_PLAIN, size=10),
            "entry":         tkfont.Font(family=D.FONT_NUM, size=10),
            "win_btn":       tkfont.Font(family=D.FONT_NUM, size=11),
            "watermark":     tkfont.Font(family=D.FONT_NUM, size=9),
            "label_bold_cn": tkfont.Font(family=D.FONT_CN_BOLD, size=10),
            "history_cn":    tkfont.Font(family=D.FONT_CN_PLAIN, size=11),
            "history_num":   tkfont.Font(family=D.FONT_NUM, size=11),
            "history_bold_cn":  tkfont.Font(family=D.FONT_CN_BOLD, size=12),
            "history_bold_num": tkfont.Font(family=D.FONT_NUM, size=12, weight="bold"),
        }
        self._base_sizes = {k: int(v.cget("size")) for k, v in self.fonts.items()}

    def _create_title_bar(self):
        bar = tk.Frame(self.root, bg="#e8e8e8", height=36)
        bar.pack(side=tk.TOP, fill=tk.X)
        bar.pack_propagate(False)
        self.title_bar = bar

        title_lbl = tk.Label(bar, text="时间看板与工作日计算工具",
                             font=self.fonts["title"], bg="#e8e8e8", fg="#333",
                             anchor="w")
        title_lbl.pack(side=tk.LEFT, padx=12, fill=tk.Y)

        self._make_titlebar_button(bar, "×", self._on_close, is_close=True, width=4)
        self._make_titlebar_button(bar, "□", self._toggle_maximize, width=4)
        self._make_titlebar_button(bar, "-", self._minimize, width=4)

        for w in (bar, title_lbl):
            w.bind("<ButtonPress-1>", self._start_move)
            w.bind("<B1-Motion>", self._on_move)
            w.bind("<Double-Button-1>", lambda e: self._toggle_maximize())

    def _make_titlebar_button(self, parent, text, command,
                              is_close=False, width=4):
        bg_normal = "#e8e8e8"
        bg_hover = "#e81123" if is_close else "#d0d0d0"
        fg_normal = "#444"
        fg_hover = "white" if is_close else "#000"
        btn = tk.Label(parent, text=text, font=self.fonts["win_btn"],
                       bg=bg_normal, fg=fg_normal, width=width, cursor="hand2")
        btn.pack(side=tk.RIGHT, fill=tk.Y)
        btn.bind("<Enter>", lambda e: btn.configure(bg=bg_hover, fg=fg_hover))
        btn.bind("<Leave>", lambda e: btn.configure(bg=bg_normal, fg=fg_normal))
        btn.bind("<Button-1>", lambda e: command())
        return btn

    def _create_content(self):
        top_frame = tk.Frame(self.root, pady=8, bg=self.bg)
        top_frame.pack(side=tk.TOP, fill=tk.X, padx=10)
        tk.Button(top_frame, text="◀ 上个月", command=self.prev_month,
                  font=self.fonts["btn"]).pack(side=tk.LEFT, padx=5)
        self.month_frame = tk.Frame(top_frame, bg=self.bg)
        self.month_frame.pack(side=tk.LEFT, padx=25)
        tk.Button(top_frame, text="下个月 ▶", command=self.next_month,
                  font=self.fonts["btn"]).pack(side=tk.LEFT, padx=5)
        tk.Button(top_frame, text="回到今天", command=self.go_to_today,
                  font=self.fonts["btn"]).pack(side=tk.RIGHT, padx=10)

        footer = tk.Frame(self.root, bg=self.bg)
        footer.pack(side=tk.BOTTOM, fill=tk.X)
        tk.Label(footer, text="Cal-tool V1.11.10 @2026-11-10 ©️", font=self.fonts["watermark"],
                 fg="#a0a0a0", bg=self.bg).pack(pady=3)

        bottom_frame = tk.Frame(self.root, padx=10, pady=5, bg=self.bg)
        bottom_frame.pack(side=tk.BOTTOM, fill=tk.X)

        input_frame = tk.Frame(bottom_frame, bg=self.bg)
        input_frame.pack(fill=tk.X, pady=5)
        lbl_box = tk.Frame(input_frame, bg=self.bg)
        lbl_box.pack(side=tk.LEFT, padx=5)
        tk.Label(lbl_box, text="目标日期 ", font=self.fonts["label_bold_cn"],
                 bg=self.bg).pack(side=tk.LEFT)
        tk.Label(lbl_box, text="(YYYY-MM-DD):", font=self.fonts["entry"],
                 bg=self.bg).pack(side=tk.LEFT)
        self.date_entry = tk.Entry(input_frame, width=15, font=self.fonts["entry"])
        self.date_entry.insert(0, self.today.strftime("%Y-%m-%d"))
        self.date_entry.pack(side=tk.LEFT, padx=5)
        self.calendar_type = tk.StringVar(value="公历")
        tk.Radiobutton(input_frame, text="公历", variable=self.calendar_type,
                       value="公历", font=self.fonts["small_cn"],
                       bg=self.bg).pack(side=tk.LEFT, padx=10)
        tk.Radiobutton(input_frame, text="农历", variable=self.calendar_type,
                       value="农历", font=self.fonts["small_cn"],
                       bg=self.bg).pack(side=tk.LEFT, padx=5)
        tk.Button(input_frame, text="开始计算", command=self.calculate_days,
                  font=self.fonts["btn"]).pack(side=tk.LEFT, padx=15)

        board_group = tk.LabelFrame(bottom_frame, text=" 实时时间看板与数据盘点 ",
                                    font=self.fonts["small_cn"], padx=5, pady=5, bg=self.bg)
        board_group.pack(fill=tk.X, expand=False, pady=5)

        self.board_canvas = tk.Canvas(board_group, height=240, highlightthickness=0, bg="white")
        self.scrollbar = tk.Scrollbar(board_group, orient="vertical",
                                      command=self.board_canvas.yview)
        self.scrollable_frame = tk.Frame(self.board_canvas, bg="white", padx=10, pady=10)
        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.board_canvas.configure(scrollregion=self.board_canvas.bbox("all")))
        self.canvas_window = self.board_canvas.create_window((0, 0),
                                                             window=self.scrollable_frame,
                                                             anchor="nw")
        self.board_canvas.configure(yscrollcommand=self.scrollbar.set)
        self.board_canvas.bind("<Configure>", self._on_canvas_configure)
        self.board_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.board_canvas.bind_all("<MouseWheel>", self._on_mousewheel)

        self.top_row = tk.Frame(self.scrollable_frame, bg="white")
        self.top_row.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        self.left_board = tk.Frame(self.top_row, bg="white")
        self.left_board.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 15))

        self.result_frame = tk.LabelFrame(self.top_row, text=" 计算结果 ",
                                          font=self.fonts["small_cn"], bg="white", fg="#555")
        self.result_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        self.result_content = tk.Frame(self.result_frame, bg="white")
        self.result_content.pack(fill=tk.BOTH, expand=True, padx=6, pady=6)

        # 历史事件区：普通 Frame + 标题 Label + Text（避免 LabelFrame 拉高）
        self.history_frame = tk.Frame(self.scrollable_frame, bg="white", highlightbackground="#d0d0d0",
                                      highlightthickness=1)
        self.history_title = tk.Label(self.history_frame, text=" 历史事件 ", font=self.fonts["small_cn"], bg="white",
                                      fg="#555", anchor="w")
        self.history_title.pack(fill=tk.X, padx=4, pady=(4, 0))
        self.history_text = tk.Text(self.history_frame, wrap=tk.WORD, bd=0, highlightthickness=0, bg="white",
                                    fg="#444", font=self.fonts["history_cn"], cursor="arrow", spacing1=2, spacing3=2,
                                    padx=8, pady=4, height=1, width=1)
        self.history_text.pack(fill=tk.X, expand=False)
        self.history_text.bind("<MouseWheel>", self._on_history_mousewheel)

        self._configure_history_tags()

        self.result_content.bind("<Configure>", lambda e: self._update_result_wrap())

        self.cal_frame = tk.Frame(self.root, padx=10, pady=5, bg=self.bg)
        self.cal_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

    def _create_resize_handles(self):
        B = self.RESIZE_BORDER
        h = {}
        h["s"]  = tk.Frame(self.root, cursor="size_ns", bg=self.bg)
        h["s"].place(x=B, rely=1.0, y=-B, relwidth=1.0, width=-2*B, height=B)
        h["w"]  = tk.Frame(self.root, cursor="size_we", bg=self.bg)
        h["w"].place(x=0, y=B, width=B, relheight=1.0, height=-2*B)
        h["e"]  = tk.Frame(self.root, cursor="size_we", bg=self.bg)
        h["e"].place(relx=1.0, x=-B, y=B, width=B, relheight=1.0, height=-2*B)
        h["nw"] = tk.Frame(self.root, cursor="size_nw_se", bg=self.bg)
        h["nw"].place(x=0, y=0, width=B, height=B)
        h["ne"] = tk.Frame(self.root, cursor="size_ne_sw", bg=self.bg)
        h["ne"].place(relx=1.0, x=-B, y=0, width=B, height=B)
        h["sw"] = tk.Frame(self.root, cursor="size_ne_sw", bg=self.bg)
        h["sw"].place(x=0, rely=1.0, y=-B, width=B, height=B)
        h["se"] = tk.Frame(self.root, cursor="size_nw_se", bg=self.bg)
        h["se"].place(relx=1.0, x=-B, rely=1.0, y=-B, width=B, height=B)
        for d, frame in h.items():
            frame.bind("<ButtonPress-1>", lambda e, _d=d: self._start_resize(e, _d))
            frame.bind("<B1-Motion>", lambda e, _d=d: self._on_resize(e, _d))

    def _start_move(self, event):
        self._drag_x = event.x_root - self.root.winfo_x()
        self._drag_y = event.y_root - self.root.winfo_y()

    def _on_move(self, event):
        if self._maximized:
            return
        self.root.geometry(f"+{event.x_root - self._drag_x}+{event.y_root - self._drag_y}")

    def _toggle_maximize(self):
        if self._maximized:
            if self._pre_max_geo:
                self.root.geometry(self._pre_max_geo)
            self._maximized = False
        else:
            self._pre_max_geo = self.root.geometry()
            self.root.geometry(f"{self.root.winfo_screenwidth()}x{self.root.winfo_screenheight()}+0+0")
            self._maximized = True

    def _minimize(self):
        self.root.overrideredirect(False)
        self.root.iconify()
        self.root.bind("<Map>", self._on_restore_from_min)

    def _on_restore_from_min(self, event):
        self.root.overrideredirect(True)
        self.root.unbind("<Map>")

    def _on_close(self):
        self.root.destroy()

    def _start_resize(self, event, direction):
        self._resize_dir = direction
        self._resize_x, self._resize_y = event.x_root, event.y_root
        self._resize_w, self._resize_h = self.root.winfo_width(), self.root.winfo_height()
        self._resize_gx, self._resize_gy = self.root.winfo_x(), self.root.winfo_y()

    def _on_resize(self, event, direction):
        if self._maximized:
            return
        dx, dy = event.x_root - self._resize_x, event.y_root - self._resize_y
        x, y = self._resize_gx, self._resize_gy
        w, h = self._resize_w, self._resize_h
        if "e" in direction: w = max(self.MIN_W, self._resize_w + dx)
        if "s" in direction: h = max(self.MIN_H, self._resize_h + dy)
        if "w" in direction:
            nw = max(self.MIN_W, self._resize_w - dx)
            x = self._resize_gx + (self._resize_w - nw); w = nw
        if "n" in direction:
            nh = max(self.MIN_H, self._resize_h - dy)
            y = self._resize_gy + (self._resize_h - nh); h = nh
        self.root.geometry(f"{w}x{h}+{x}+{y}")

    def _on_root_configure(self, event):
        if event.widget is not self.root:
            return
        w, h = self.root.winfo_width(), self.root.winfo_height()
        if w < 50 or h < 50:
            return
        scale = max(0.72, min(min(w / self.BASE_W, h / self.BASE_H), 2.5))
        if abs(scale - self._current_scale) < 0.03:
            return
        self._current_scale = scale
        for key, font in self.fonts.items():
            try:
                font.configure(size=max(6, int(round(self._base_sizes[key] * scale))))
            except tk.TclError:
                pass

    def _on_canvas_configure(self, event):
        self.board_canvas.itemconfig(self.canvas_window, width=event.width)
        # 宽度变化后重新计算历史事件区高度
        if hasattr(self, "history_text"):
            self.root.after_idle(self._resize_history_text)

    def _update_result_wrap(self):
        w = max(100, self.result_content.winfo_width() - 10)
        self._apply_wrap(self.result_content, w)

    def _apply_wrap(self, container, width):
        for widget in container.winfo_children():
            if isinstance(widget, tk.Label):
                try:
                    widget.configure(wraplength=width)
                except tk.TclError:
                    pass
            self._apply_wrap(widget, width)

    def _on_mousewheel(self, event):
        if self.board_canvas.winfo_height() < self.scrollable_frame.winfo_height():
            self.board_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    def _on_history_mousewheel(self, event):
        # 历史事件区内的滚轮转发给外层看板，保持全局滚动一致
        self._on_mousewheel(event)
        return "break"

    def _update_month_label(self, year, month):
        for w in self.month_frame.winfo_children():
            w.destroy()
        bg = self.bg
        tk.Label(self.month_frame, text=str(year), font=self.fonts["title_num"], bg=bg).pack(side=tk.LEFT)
        tk.Label(self.month_frame, text="年 ", font=self.fonts["title_cn"], bg=bg).pack(side=tk.LEFT)
        tk.Label(self.month_frame, text=str(month), font=self.fonts["title_num"], bg=bg).pack(side=tk.LEFT)
        tk.Label(self.month_frame, text="月", font=self.fonts["title_cn"], bg=bg).pack(side=tk.LEFT)

    def draw_calendar(self, year, month):
        for w in self.cal_frame.winfo_children():
            w.destroy()
        self._update_month_label(year, month)

        weeks = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
        for i, week in enumerate(weeks):
            tk.Label(self.cal_frame, text=week, font=self.fonts["week"],
                     anchor="center", bg=self.bg).grid(row=0, column=i, sticky="nsew", pady=8)

        cal = calendar.Calendar(firstweekday=0)
        month_dates = cal.monthdatescalendar(year, month)
        for i in range(7):
            self.cal_frame.columnconfigure(i, weight=1, uniform="cal")
        for j in range(len(month_dates) + 1):
            self.cal_frame.rowconfigure(j, weight=1, uniform="cal")

        for r, week in enumerate(month_dates, start=1):
            for c, cur_date in enumerate(week):
                is_current_month = (cur_date.month == month and cur_date.year == year)
                day = cur_date.day

                lunar_text = ""
                try:
                    lunar = LunarDate.from_solar_date(cur_date.year, cur_date.month, cur_date.day)
                    lunar_text = lunar.strftime("%D") if lunar.day != 1 else f"{lunar.strftime('%M')}月"
                except Exception:
                    pass

                h_name = ""
                is_work = cur_date.weekday() < 5
                has_data = True
                try:
                    lunar = LunarDate.from_solar_date(cur_date.year, cur_date.month, cur_date.day)
                    try:
                        last_day = LunarDate(lunar.year, 12, 1).length_of_month
                        if lunar.month == 12 and lunar.day == last_day:
                            h_name = "除夕"
                        elif (lunar.month, lunar.day) in D.LUNAR_FESTIVALS:
                            h_name = D.LUNAR_FESTIVALS[(lunar.month, lunar.day)]
                    except Exception:
                        if (lunar.month, lunar.day) in D.LUNAR_FESTIVALS:
                            h_name = D.LUNAR_FESTIVALS[(lunar.month, lunar.day)]
                except Exception:
                    pass
                if not h_name and (cur_date.month, cur_date.day) in D.SOLAR_FESTIVALS:
                    h_name = D.SOLAR_FESTIVALS[(cur_date.month, cur_date.day)]

                if cur_date.year == 2027:
                    is_work, _ = self.safe_is_workday(cur_date)
                    if cur_date == date(2027, 4, 5):
                        h_name = "清明节"
                else:
                    try:
                        is_work, _ = self.safe_is_workday(cur_date)
                        hol_info = get_holiday_detail(cur_date)
                        if hol_info and hol_info[0] and hol_info[1]:
                            raw = D.FESTIVAL_MAP.get(hol_info[1], hol_info[1])
                            if raw == "清明节" and (hol_info[2] is None or hol_info[2] == cur_date):
                                h_name = "清明节"
                    except NotImplementedError:
                        has_data = False

                info = D.get_memorial_info(cur_date.month, cur_date.day)
                persons = P.get_person_info(cur_date.month, cur_date.day)
                official_name = info["official_name"] if is_current_month else None
                has_events = (bool(info["events"]) or bool(persons)) and is_current_month

                bd_width, relief_style = 1, "groove"
                if not is_current_month:
                    if is_work:
                        bg_color, fg_color, sub_fg = "#fafafa", "#aaaaaa", "#bbbbbb"
                    else:
                        bg_color, fg_color, sub_fg = "#fdf0ed", "#aaaaaa", "#bbbbbb"
                else:
                    bg_color, fg_color, sub_fg = "#ffffff", "#000000", "#555555"
                    if cur_date == self.today:
                        bg_color = "#e1f5fe"
                    elif not is_work:
                        bg_color = "#fbe9e7"

                if self.target_highlight_date and cur_date == self.target_highlight_date:
                    bg_color = "#fff9c4"
                    bd_width, relief_style = 2, "solid"
                    fg_color = "#000000"

                cell = tk.Frame(self.cal_frame, bg=bg_color, relief=relief_style, borderwidth=bd_width)
                cell.grid(row=r, column=c, sticky="nsew", padx=3, pady=3)

                day_lbl = tk.Label(cell, text=str(day), bg=bg_color, fg=fg_color, font=self.fonts["day"])
                day_lbl.pack(side=tk.TOP, pady=(6, 2))

                if is_current_month and h_name:
                    bottom_text, text_fg, text_font = h_name, "#d32f2f", self.fonts["festival"]
                elif is_current_month and official_name:
                    bottom_text, text_fg, text_font = official_name, "#1565c0", self.fonts["festival"]
                else:
                    bottom_text, text_fg, text_font = lunar_text, sub_fg, self.fonts["lunar"]

                sub_lbl = None
                if bottom_text:
                    sub_lbl = tk.Label(cell, text=bottom_text, bg=bg_color,
                                       fg=text_fg, font=text_font)
                    sub_lbl.pack(side=tk.TOP, pady=(0, 4))

                if has_events:
                    tk.Label(cell, text="●", bg=bg_color, fg="#8b4513",
                             font=self.fonts["dot"]).place(relx=0.0, rely=1.0, anchor="sw", x=3, y=-3)

                if is_current_month and has_data:
                    if is_work and c in (5, 6):
                        tk.Label(cell, text="班", bg="#efebe9", fg="#d32f2f",
                                 font=self.fonts["badge"]).place(relx=1.0, rely=0.0, anchor="ne")
                    elif not is_work and c not in (5, 6):
                        tk.Label(cell, text="假", bg="#ffc107", fg="#000000",
                                 font=self.fonts["badge"]).place(relx=1.0, rely=0.0, anchor="ne")

                for w in [x for x in (cell, day_lbl, sub_lbl) if x is not None]:
                    w.bind("<Button-1>", lambda e, d=cur_date: self._on_cell_click(d))

    def _on_cell_click(self, clicked_date):
        self.pinned_event_date = clicked_date
        self._refresh_history_display()

    # ---------- 历史事件区：单 Text + 多 tag ----------
    def _configure_history_tags(self):
        t = self.history_text
        t.tag_configure("date_cn", font=self.fonts["history_bold_cn"], foreground="#c62828")
        t.tag_configure("date_num", font=self.fonts["history_bold_num"], foreground="#c62828")
        t.tag_configure("official_cn", font=self.fonts["history_bold_cn"], foreground="#c62828")
        t.tag_configure("official_num", font=self.fonts["history_bold_num"], foreground="#c62828")
        t.tag_configure("body_cn", font=self.fonts["history_cn"], foreground="#555")
        t.tag_configure("body_num", font=self.fonts["history_num"], foreground="#555")
        t.tag_configure("cat_cn", font=self.fonts["history_bold_cn"], foreground="#6a1b9a")
        t.tag_configure("title_cn", font=self.fonts["history_bold_cn"], foreground="#1565c0")
        t.tag_configure("title_num", font=self.fonts["history_bold_num"], foreground="#1565c0")
        t.tag_configure("age_cn", font=self.fonts["history_bold_cn"], foreground="#e65100")
        t.tag_configure("age_num", font=self.fonts["history_bold_num"], foreground="#e65100")
        t.tag_configure("summary_cn", font=self.fonts["history_cn"], foreground="#444")
        t.tag_configure("summary_num", font=self.fonts["history_num"], foreground="#444")
        t.tag_configure("detail_cn", font=self.fonts["history_cn"], foreground="#666")
        t.tag_configure("detail_num", font=self.fonts["history_num"], foreground="#666")

    _MIXED_RE = re.compile(
        r"([\u4e00-\u9fff\u3000-\u303f\uff00-\uffef]+)"
        r"|([A-Za-z0-9\-\.\:\/\s]+)")

    def _insert_mixed(self, text, tag_cn, tag_num):
        pos = 0
        for m in self._MIXED_RE.finditer(text):
            if m.start() > pos:
                self.history_text.insert(tk.END, text[pos:m.start()], tag_cn)
            if m.group(1):
                self.history_text.insert(tk.END, m.group(1), tag_cn)
            else:
                self.history_text.insert(tk.END, m.group(2), tag_num)
            pos = m.end()
        if pos < len(text):
            self.history_text.insert(tk.END, text[pos:], tag_cn)

    def _insert_date_line(self, target_date, label, official_name):
        t = self.history_text
        if label:
            t.insert(tk.END, f"【{label}】", "official_cn")
        self._insert_mixed(str(target_date.month), "date_num", "date_num")
        t.insert(tk.END, " 月 ", "date_cn")
        self._insert_mixed(str(target_date.day), "date_num", "date_num")
        t.insert(tk.END, " 日", "date_cn")
        if official_name:
            t.insert(tk.END, "  ·  ", "official_cn")
            self._insert_mixed(official_name, "official_cn", "official_num")
        t.insert(tk.END, "\n")

    def _refresh_history_display(self):
        today_info = D.get_memorial_info(self.today.month, self.today.day)
        today_persons = P.get_person_info(self.today.month, self.today.day)
        today_has = bool(today_info["official_name"] or today_info["events"] or today_persons)

        show_pinned = False
        pinned_info = None
        pinned_persons = []
        if self.pinned_event_date and self.pinned_event_date != self.today:
            pinned_info = D.get_memorial_info(self.pinned_event_date.month, self.pinned_event_date.day)
            pinned_persons = P.get_person_info(self.pinned_event_date.month, self.pinned_event_date.day)
            show_pinned = bool(pinned_info["official_name"] or pinned_info["events"] or pinned_persons)

        if not today_has and not show_pinned:
            self.history_frame.pack_forget()
            return

        t = self.history_text
        t.config(state="normal")
        t.delete("1.0", tk.END)

        first_block = True
        if today_has:
            self._render_block_into_text(self.today, today_info, today_persons, "今天")
            first_block = False
        if show_pinned:
            if not first_block:
                t.insert(tk.END, "\n")
            self._render_block_into_text(self.pinned_event_date, pinned_info, pinned_persons, None)

        t.config(state="disabled")
        if not self.history_frame.winfo_manager():
            self.history_frame.pack(side=tk.BOTTOM, fill=tk.X, pady=(6, 0))
        # 等布局完成后再算高度，避免宽度未定时 displaylines 算错
        self.root.after_idle(self._resize_history_text)

    def _resize_history_text(self):
        if not self.history_text.winfo_manager():
            return
        t = self.history_text
        t.update_idletasks()
        try:
            result = t.count("1.0", tk.END, "displaylines")
        except Exception:
            return
        if result:
            lines = int(result[0])
            t.config(height=max(1, lines))

    def _render_block_into_text(self, target_date, info, persons, label):
        t = self.history_text
        self._insert_date_line(target_date, label, info["official_name"])

        if info.get("official_detail"):
            self._insert_mixed(info["official_detail"], "body_cn", "body_num")
            t.insert(tk.END, "\n")

        for p in persons:
            t.insert(tk.END, f"【{p['category']}】", "cat_cn")
            self._insert_mixed(str(p["year"]), "title_num", "title_num")
            t.insert(tk.END, " 年 · ", "title_cn")
            self._insert_mixed(p["name"], "title_cn", "title_num")
            age = self.today.year - p["year"]
            if age > 0:
                t.insert(tk.END, "（", "age_cn")
                self._insert_mixed(str(age), "age_num", "age_num")
                t.insert(tk.END, " 周年）", "age_cn")
            t.insert(tk.END, "\n")
            self._insert_mixed(p["title"] + " · " + p["summary"], "summary_cn", "summary_num")
            t.insert(tk.END, "\n")
            if p.get("detail"):
                self._insert_mixed(p["detail"], "detail_cn", "detail_num")
                t.insert(tk.END, "\n")

        if persons and info["events"]:
            t.insert(tk.END, "\n")

        for ev in info["events"]:
            year = ev.get("year")
            if year:
                self._insert_mixed(str(year), "title_num", "title_num")
                t.insert(tk.END, " 年 · ", "title_cn")
            self._insert_mixed(ev["name"], "title_cn", "title_num")
            if year:
                age = self.today.year - year
                if age > 0:
                    t.insert(tk.END, "（", "age_cn")
                    self._insert_mixed(str(age), "age_num", "age_num")
                    t.insert(tk.END, " 周年）", "age_cn")
            t.insert(tk.END, "\n")
            if ev.get("summary"):
                self._insert_mixed(ev["summary"], "summary_cn", "summary_num")
                t.insert(tk.END, "\n")
            if ev.get("detail"):
                self._insert_mixed(ev["detail"], "detail_cn", "detail_num")
                t.insert(tk.END, "\n")

    def prev_month(self):
        if self.current_month == 1:
            self.current_month, self.current_year = 12, self.current_year - 1
        else:
            self.current_month -= 1
        self.draw_calendar(self.current_year, self.current_month)

    def next_month(self):
        if self.current_month == 12:
            self.current_month, self.current_year = 1, self.current_year + 1
        else:
            self.current_month += 1
        self.draw_calendar(self.current_year, self.current_month)

    def go_to_today(self):
        self.today = date.today()
        self.current_year, self.current_month = self.today.year, self.today.month
        self.target_highlight_date = None
        self.pinned_event_date = None
        self.draw_calendar(self.current_year, self.current_month)
        self.update_dashboard()
        self._refresh_history_display()

    def safe_is_workday(self, d):
        return D.is_workday_extended(d)

    def _add_mixed_line(self, parent, segments, pady=3):
        line = tk.Frame(parent, bg="white")
        line.pack(anchor=tk.W, pady=pady, fill=tk.X)
        for seg in segments:
            text, font = seg[0], seg[1]
            fg = seg[2] if len(seg) > 2 and seg[2] else None
            kw = {"text": text, "font": font, "bg": "white"}
            if fg:
                kw["fg"] = fg
            tk.Label(line, **kw).pack(side=tk.LEFT)
        return line

    def _add_calc_result(self, parent, result_text):
        txt = tk.Text(parent, wrap=tk.WORD, bd=0, highlightthickness=0, bg="white",
                      fg="blue", font=self.fonts["dash_cn"], cursor="arrow",
                      spacing1=2, spacing3=2, height=6)
        txt.pack(anchor=tk.W, fill=tk.BOTH, expand=True, pady=3)
        pattern = re.compile(r"([\u4e00-\u9fff\u3000-\u303f\uff00-\uffef]+)|([A-Za-z0-9\-\.\:\/\s]+)")
        pos = 0
        for m in pattern.finditer(result_text):
            if m.start() > pos:
                txt.insert(tk.END, result_text[pos:m.start()], "cn")
            txt.insert(tk.END, m.group(1) if m.group(1) else m.group(2),
                       "cn" if m.group(1) else "num")
            pos = m.end()
        if pos < len(result_text):
            txt.insert(tk.END, result_text[pos:], "cn")
        txt.tag_configure("cn", font=self.fonts["dash_cn"], foreground="blue")
        txt.tag_configure("num", font=self.fonts["dash_num"], foreground="blue")
        txt.config(state="disabled")
        txt.update_idletasks()
        try:
            lines = txt.count("1.0", tk.END, "displaylines")
            if lines:
                txt.config(height=max(2, lines[0]))
        except Exception:
            pass

    def update_dashboard(self, calc_result_text=None):
        for w in self.left_board.winfo_children():
            w.destroy()
        for w in self.result_content.winfo_children():
            w.destroy()

        ty, tm = self.today.year, self.today.month
        year_start, year_end = date(ty, 1, 1), date(ty, 12, 31)
        passed = (self.today - year_start).days + 1
        remain_year = (year_end - self.today).days

        rem_month_workdays = 0
        last_day = calendar.monthrange(ty, tm)[1]
        curr = self.today
        while curr <= date(ty, tm, last_day):
            if self.safe_is_workday(curr)[0]:
                rem_month_workdays += 1
            curr += timedelta(days=1)

        rem_year_wd = rem_year_hol_all = rem_year_hol_wd = 0
        curr = self.today
        while curr <= year_end:
            is_wk, _ = self.safe_is_workday(curr)
            if is_wk:
                rem_year_wd += 1
            else:
                is_hol = True if curr.year == 2027 else False
                if curr.year != 2027:
                    try:
                        is_hol = is_holiday(curr)
                    except NotImplementedError:
                        pass
                if is_hol:
                    rem_year_hol_all += 1
                    if curr.weekday() < 5:
                        rem_year_hol_wd += 1
            curr += timedelta(days=1)

        next_hol = None
        curr = self.today + timedelta(days=1)
        for _ in range(365):
            if curr.year == 2027:
                is_hol = not self.safe_is_workday(curr)[0]
            else:
                try:
                    is_hol = is_holiday(curr)
                except NotImplementedError:
                    break
            if is_hol and curr.weekday() < 5:
                next_hol = (curr - self.today).days
                break
            curr += timedelta(days=1)

        self._add_mixed_line(self.left_board, [
            ("本年进度：本年度已过去 ", self.fonts["dash_cn"], None),
            (str(passed), self.fonts["dash_num"], None),
            (" 天，还剩 ", self.fonts["dash_cn"], None),
            (str(remain_year), self.fonts["dash_num"], None),
            (" 天", self.fonts["dash_cn"], None)])
        self._add_mixed_line(self.left_board, [
            ("月度盘点：本月份接下来还剩 ", self.fonts["dash_cn"], None),
            (str(rem_month_workdays), self.fonts["dash_num"], None),
            (" 个工作日", self.fonts["dash_cn"], None)])
        self._add_mixed_line(self.left_board, [
            ("年度盘点：本年度接下来还剩 ", self.fonts["dash_cn"], None),
            (str(rem_year_wd), self.fonts["dash_num"], None),
            (" 个工作日", self.fonts["dash_cn"], None)])
        self._add_mixed_line(self.left_board, [
            ("假期预报：本年剩余法定假 ", self.fonts["dash_cn"], None),
            (str(rem_year_hol_all), self.fonts["dash_num"], None),
            (" 天 (含周末) ｜ 非周末 ", self.fonts["dash_cn"], None),
            (str(rem_year_hol_wd), self.fonts["dash_num"], None),
            (" 天", self.fonts["dash_cn"], None)])
        if next_hol is None:
            self._add_mixed_line(self.left_board, [
                ("距离下次法定节假日 (非周末) 还剩：", self.fonts["dash_bold_cn"], "green"),
                ("暂无数据", self.fonts["dash_cn"], "green")])
        else:
            self._add_mixed_line(self.left_board, [
                ("距离下次法定节假日 (非周末) 还剩：", self.fonts["dash_bold_cn"], "green"),
                (str(next_hol), self.fonts["dash_bold_num"], "green"),
                (" 天", self.fonts["dash_bold_cn"], "green")])

        if calc_result_text:
            self._add_calc_result(self.result_content, calc_result_text)
        else:
            tk.Label(self.result_content,
                     text="提示：在上方输入日期并点击“开始计算”，累计区间天数及详细的工作日/非工作日统计报告将会呈现在这里。",
                     font=self.fonts["small_cn"], fg="gray", bg="white",
                     justify=tk.LEFT, wraplength=300, anchor="w")\
                .pack(anchor="w", fill=tk.X, pady=3)
        self.root.after_idle(self._update_result_wrap)

    def calculate_days(self):
        input_str = self.date_entry.get().strip()
        try:
            parts = [int(x) for x in input_str.split("-")]
            if len(parts) != 3:
                raise ValueError
            if self.calendar_type.get() == "农历":
                target_date = LunarDate(parts[0], parts[1], parts[2]).to_solar_date()
            else:
                target_date = date(parts[0], parts[1], parts[2])
        except Exception:
            messagebox.showerror("输入错误", "请输入正确的日期格式，例如: 2027-10-01")
            return

        self.target_highlight_date = target_date
        d1, d2 = min(self.today, target_date), max(self.today, target_date)
        total_days = (d2 - d1).days
        wd = nwd = 0
        out_of_range = False
        curr = d1
        while curr <= d2:
            is_w, acc = self.safe_is_workday(curr)
            if not acc:
                out_of_range = True
            if is_w:
                wd += 1
            else:
                nwd += 1
            curr += timedelta(days=1)

        direction = "前" if target_date < self.today else "后"
        result_text = (
            f"累计天数计算报告：\n目标公历日期: {target_date.strftime('%Y-%m-%d')}\n"
            f"距离今天 ({direction}共计 {total_days} 天)\n\n"
            f"【工作日总计】 {wd} 天\n【非工作日总计】 {nwd} 天")
        if out_of_range:
            result_text += "\n\n注：区间包含 2004 前或 2027 后，缺少官方调休方案的部分已按标准周末对齐。"

        self.current_year, self.current_month = target_date.year, target_date.month
        self.draw_calendar(self.current_year, self.current_month)
        self.update_dashboard(calc_result_text=result_text)


if __name__ == "__main__":
    root = tk.Tk()
    app = CalendarApp(root)
    root.mainloop()