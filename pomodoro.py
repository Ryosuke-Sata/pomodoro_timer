import customtkinter as ctk
import sqlite3
import datetime
import winsound
import threading
import time
import csv
import os
import random
import struct
import wave
import pygame
import ctypes
from winotify import Notification, audio

# --- 設定 ---
ctk.set_appearance_mode("System")
ctk.set_default_color_theme("blue")

class PomodoroApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        # アプリ基本設定
        self.title("Modern Pomodoro")
        self.geometry("400x700")
        self.resizable(False, False)

        # 変数
        self.timer_running = False
        self.timer_seconds = 25 * 60
        self.selected_duration = 25 * 60
        self.timer_id = None
        self.view_mode = "main" # main, mini, bar
        self.is_typing = False 
        
        # ドラッグ移動用変数
        self.drag_start_x = 0
        self.drag_start_y = 0
        
        # 音声初期化
        self.init_audio()
        
        # データベース初期化＆更新
        self.init_db()

        # UIレイアウト作成
        self.create_main_layout()
        self.create_mini_layout()
        self.create_bar_layout()
        
        # 初期状態はメインモードを表示
        # 起動時に画面中央へ
        self.center_window_on_start(400, 700)
        self.show_main_view()

        # 時計の更新開始
        self.update_clock()

    def center_window_on_start(self, w, h):
        """起動時に画面中央に配置する"""
        screen_w = self.winfo_screenwidth()
        screen_h = self.winfo_screenheight()
        x = (screen_w - w) // 2
        y = (screen_h - h) // 2
        self.geometry(f"{w}x{h}+{x}+{y}")

    def init_audio(self):
        pygame.mixer.init()
        self.generate_noise_file("white_noise.wav", "white")
        self.generate_noise_file("pink_noise.wav", "pink")
        self.generate_noise_file("brown_noise.wav", "brown")

    def generate_noise_file(self, filename, color="white", duration=5):
        if os.path.exists(filename): return
        framerate = 44100
        nframes = duration * framerate
        noise_data = []
        vol = 2000 if color == "brown" else 3000
        last_val = 0
        b = [0.0] * 7
        for _ in range(nframes):
            white = random.uniform(-1, 1)
            if color == "white": val = white * vol
            elif color == "brown":
                last_val = (last_val + (0.02 * white)) / 1.02
                val = last_val * vol * 30
            elif color == "pink":
                b[0] = 0.99886 * b[0] + white * 0.0555179
                b[1] = 0.99332 * b[1] + white * 0.0750759
                b[2] = 0.96900 * b[2] + white * 0.1538520
                b[3] = 0.86650 * b[3] + white * 0.3104856
                b[4] = 0.55000 * b[4] + white * 0.5329522
                b[5] = -0.7616 * b[5] - white * 0.0168980
                val = (sum(b) + b[6] + white * 0.5362) * 0.11 * vol * 5
                b[6] = white * 0.115926
            else: val = 0
            val = max(-32000, min(32000, int(val)))
            noise_data.append(int(val))
        packed_data = struct.pack('h' * len(noise_data), *noise_data)
        with wave.open(filename, 'w') as f:
            f.setnchannels(1); f.setsampwidth(2); f.setframerate(framerate); f.writeframes(packed_data)

    def init_db(self):
        self.conn = sqlite3.connect("work_log.db")
        self.cursor = self.conn.cursor()
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT,
                duration_minutes INTEGER,
                task_name TEXT,
                time_range TEXT
            )
        """)
        try: self.cursor.execute("SELECT task_name FROM logs LIMIT 1")
        except: self.cursor.execute("ALTER TABLE logs ADD COLUMN task_name TEXT"); self.conn.commit()
        try: self.cursor.execute("SELECT time_range FROM logs LIMIT 1")
        except: self.cursor.execute("ALTER TABLE logs ADD COLUMN time_range TEXT"); self.conn.commit()
        self.conn.commit()

    # --- UI構築 ---

    def create_main_layout(self):
        self.main_frame = ctk.CTkFrame(self, fg_color="transparent")
        
        self.clock_label = ctk.CTkLabel(self.main_frame, text="--:--:--", font=("Arial", 24, "bold"), text_color="gray")
        self.clock_label.pack(anchor="ne", padx=20, pady=(10, 0))

        self.tabview = ctk.CTkTabview(self.main_frame, width=380, height=580)
        self.tabview.pack(padx=10, pady=5, fill="both", expand=True)
        self.tabview.add("Timer")
        self.tabview.add("History")

        t_frame = self.tabview.tab("Timer")
        ctk.CTkLabel(t_frame, text="作業内容 (Task Name)", font=("Yu Gothic UI", 12)).pack(pady=(5, 0))
        
        self.task_entry = ctk.CTkEntry(
            t_frame, 
            placeholder_text="例: 英語の勉強", 
            width=250, 
            font=("Yu Gothic UI", 14), 
            text_color=("black", "white")
        )
        self.task_entry.pack(pady=5)

        # 【修正】 add="+" を追加して、プレースホルダー機能を消さないようにする
        self.task_entry._entry.bind("<FocusIn>", self.on_entry_focus_in, add="+")
        self.task_entry._entry.bind("<FocusOut>", self.on_entry_focus_out, add="+")
        self.task_entry._entry.bind("<Return>", self.on_entry_return, add="+")

        self.mode_var = ctk.StringVar(value="Focus 25")
        self.mode_segment = ctk.CTkSegmentedButton(t_frame, values=["Focus 25", "Focus 50", "Break 5", "Break 15"], command=self.change_mode, variable=self.mode_var)
        self.mode_segment.pack(pady=10)

        self.time_label = ctk.CTkLabel(t_frame, text="25:00", font=("Roboto Medium", 80))
        self.time_label.pack(pady=5)

        bgm_frame = ctk.CTkFrame(t_frame, fg_color="transparent")
        bgm_frame.pack(pady=5)
        ctk.CTkLabel(bgm_frame, text="🎵 BGM", font=("Yu Gothic UI", 12, "bold")).pack(side="left", padx=5)
        self.bgm_var = ctk.StringVar(value="None")
        self.bgm_menu = ctk.CTkOptionMenu(bgm_frame, values=["None", "White Noise", "Pink Noise (Rain)", "Brown Noise (River)"], variable=self.bgm_var, command=self.on_bgm_change, width=160)
        self.bgm_menu.pack(side="left", padx=5)
        ctk.CTkLabel(bgm_frame, text="🔊", font=("Arial", 12)).pack(side="left", padx=(10, 2))
        self.vol_slider = ctk.CTkSlider(bgm_frame, from_=0, to=1, width=80, command=self.change_volume)
        self.vol_slider.set(0.5)
        self.vol_slider.pack(side="left", padx=5)

        btn_frame = ctk.CTkFrame(t_frame, fg_color="transparent")
        btn_frame.pack(pady=10)
        self.start_btn = ctk.CTkButton(btn_frame, text="START", command=self.start_timer, width=100, height=40, font=("Arial", 16))
        self.start_btn.grid(row=0, column=0, padx=10)
        self.reset_btn = ctk.CTkButton(btn_frame, text="RESET", command=self.reset_timer, width=100, height=40, fg_color="gray", hover_color="darkgray", font=("Arial", 16))
        self.reset_btn.grid(row=0, column=1, padx=10)

        opt_frame = ctk.CTkFrame(t_frame, fg_color="transparent")
        opt_frame.pack(pady=10)
        
        self.top_switch = ctk.CTkSwitch(opt_frame, text="常に最前面", command=self.check_topmost)
        self.top_switch.pack(side="left", padx=10)
        
        self.mini_btn = ctk.CTkButton(opt_frame, text="ミニ", command=self.switch_to_mini, width=60, fg_color="teal")
        self.mini_btn.pack(side="left", padx=5)
        
        self.bar_btn = ctk.CTkButton(opt_frame, text="バー", command=self.switch_to_bar, width=60, fg_color="#4B4B4B")
        self.bar_btn.pack(side="left", padx=5)

        self.status_label = ctk.CTkLabel(t_frame, text="Ready", text_color="gray")
        self.status_label.pack(side="bottom", pady=5)

        h_frame = self.tabview.tab("History")
        ctk.CTkLabel(h_frame, text="作業履歴", font=("Yu Gothic UI", 16, "bold")).pack(pady=10)
        self.history_scroll = ctk.CTkScrollableFrame(h_frame, width=320, height=350)
        self.history_scroll.pack()
        self.export_btn = ctk.CTkButton(h_frame, text="CSV出力 (Excel用)", command=self.export_csv, fg_color="green", hover_color="darkgreen")
        self.export_btn.pack(pady=10)
        ctk.CTkButton(h_frame, text="履歴更新", command=self.load_history, height=30).pack(pady=5)
        self.load_history()

    # --- 最前面制御ロジック ---
    def check_topmost(self):
        """現在の状態を確認して最前面設定を適用する"""
        if self.is_typing:
            self.attributes('-topmost', False)
            return

        if self.view_mode != "main":
            self.attributes('-topmost', True)
            return

        state = self.top_switch.get() == 1
        self.attributes('-topmost', state)

    # --- イベントハンドラ ---
    def on_entry_focus_in(self, event):
        self.is_typing = True
        self.check_topmost() 

    def on_entry_focus_out(self, event):
        self.is_typing = False
        self.check_topmost() 

    def on_entry_return(self, event):
        self.focus() 

    # --- レイアウト作成 (Mini/Bar) ---
    def create_mini_layout(self):
        self.mini_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.mini_clock_label = ctk.CTkLabel(self.mini_frame, text="--:--:--", font=("Arial", 12), text_color="gray")
        self.mini_clock_label.pack(pady=(5, 0))
        self.mini_time_label = ctk.CTkLabel(self.mini_frame, text="25:00", font=("Roboto Medium", 40))
        self.mini_time_label.pack(pady=(0, 5))
        btn_frame = ctk.CTkFrame(self.mini_frame, fg_color="transparent")
        btn_frame.pack(pady=5)
        self.mini_start_btn = ctk.CTkButton(btn_frame, text="⏯", command=self.start_timer, width=40, height=30)
        self.mini_start_btn.grid(row=0, column=0, padx=5)
        ctk.CTkButton(btn_frame, text="⏹", command=self.reset_timer, width=40, height=30, fg_color="gray").grid(row=0, column=1, padx=5)
        ctk.CTkButton(self.mini_frame, text="拡大 ⤢", command=self.switch_to_main, width=60, height=20, fg_color="transparent", border_width=1).pack(pady=5)

    def create_bar_layout(self):
        self.bar_frame = ctk.CTkFrame(self, fg_color="#2b2b2b", corner_radius=10) 
        inner_frame = ctk.CTkFrame(self.bar_frame, fg_color="transparent")
        inner_frame.pack(fill="both", expand=True, padx=10, pady=2)

        for widget in [self.bar_frame, inner_frame]:
            widget.bind("<Button-1>", self.start_move)
            widget.bind("<B1-Motion>", self.do_move)

        self.bar_task_label = ctk.CTkLabel(inner_frame, text="No Task", font=("Yu Gothic UI", 12), text_color="gray")
        self.bar_task_label.pack(side="left", padx=10)
        self.bar_clock_label = ctk.CTkLabel(inner_frame, text="--:--", font=("Arial", 12), text_color="gray")
        self.bar_clock_label.pack(side="left", padx=10)
        self.bar_time_label = ctk.CTkLabel(inner_frame, text="25:00", font=("Roboto Medium", 24), text_color="#3B8ED0")
        self.bar_time_label.pack(side="left", padx=15)
        self.bar_start_btn = ctk.CTkButton(inner_frame, text="⏯", command=self.start_timer, width=30, height=25)
        self.bar_start_btn.pack(side="left", padx=5)
        ctk.CTkButton(inner_frame, text="⏹", command=self.reset_timer, width=30, height=25, fg_color="gray").pack(side="left", padx=5)
        ctk.CTkButton(inner_frame, text="拡大 ⤢", command=self.switch_to_main, width=40, height=20, fg_color="transparent", border_width=1).pack(side="right", padx=5)
        
        for widget in inner_frame.winfo_children():
            if isinstance(widget, ctk.CTkLabel):
                widget.bind("<Button-1>", self.start_move)
                widget.bind("<B1-Motion>", self.do_move)

    def start_move(self, event):
        self.drag_start_x = event.x
        self.drag_start_y = event.y

    def do_move(self, event):
        x = self.winfo_x() + (event.x - self.drag_start_x)
        y = self.winfo_y() + (event.y - self.drag_start_y)
        self.geometry(f"+{x}+{y}")

    def update_clock(self):
        now_str = datetime.datetime.now().strftime("%H:%M:%S")
        if hasattr(self, 'clock_label'): self.clock_label.configure(text=now_str)
        if hasattr(self, 'mini_clock_label'): self.mini_clock_label.configure(text=now_str)
        if hasattr(self, 'bar_clock_label'): self.bar_clock_label.configure(text=now_str[:5])
        self.after(1000, self.update_clock)

    def show_main_view(self):
        self.mini_frame.pack_forget()
        self.bar_frame.pack_forget()
        self.main_frame.pack(fill="both", expand=True)

    def switch_to_mini(self):
        self.view_mode = "mini"
        self.main_frame.pack_forget()
        self.bar_frame.pack_forget()
        self.mini_frame.pack(fill="both", expand=True)
        self.withdraw()
        self.overrideredirect(False)
        self.geometry("200x160")
        self.deiconify()
        self.check_topmost() 

    def switch_to_bar(self):
        self.view_mode = "bar"
        self.main_frame.pack_forget()
        self.mini_frame.pack_forget()
        self.bar_frame.pack(fill="both", expand=True)
        task = self.task_entry.get()
        self.bar_task_label.configure(text=task if task else "No Task")
        w, h = 500, 40
        x = (self.winfo_screenwidth() // 2) - (w // 2)
        y = self.winfo_screenheight() - 100 
        self.withdraw()
        self.overrideredirect(True) 
        self.geometry(f"{w}x{h}+{x}+{y}")
        self.deiconify()
        self.after(200, self.force_taskbar_icon)
        self.check_topmost()

    def force_taskbar_icon(self):
        try:
            self.update_idletasks()
            hwnd = ctypes.windll.user32.GetParent(self.winfo_id())
            GWL_EXSTYLE = -20
            WS_EX_APPWINDOW = 0x00040000
            WS_EX_TOOLWINDOW = 0x00000080
            style = ctypes.windll.user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
            style = style & ~WS_EX_TOOLWINDOW
            style = style | WS_EX_APPWINDOW
            ctypes.windll.user32.SetWindowLongW(hwnd, GWL_EXSTYLE, style)
            ctypes.windll.user32.SetWindowPos(hwnd, 0, 0, 0, 0, 0, 0x27)
        except Exception as e:
            print(f"Force taskbar icon error: {e}")

    def switch_to_main(self):
        self.view_mode = "main"
        self.mini_frame.pack_forget()
        self.bar_frame.pack_forget()
        self.main_frame.pack(fill="both", expand=True)
        self.overrideredirect(False)
        self.withdraw()
        self.update_idletasks()
        self.center_window(400, 700)
        self.deiconify()
        self.check_topmost() 

    def center_window(self, w, h):
        screen_w = self.winfo_screenwidth()
        screen_h = self.winfo_screenheight()
        x = (screen_w - w) // 2
        y = (screen_h - h) // 2
        self.geometry(f"{w}x{h}+{x}+{y}")

    def toggle_always_on_top(self):
        if self.view_mode != "main":
            self.attributes('-topmost', True)
        else:
            state = self.top_switch.get() == 1
            self.attributes('-topmost', state)

    def change_mode(self, value):
        self.reset_timer()
        mapping = {"Focus 25": 25, "Focus 50": 50, "Break 5": 5, "Break 15": 15}
        self.selected_duration = mapping[value] * 60
        self.timer_seconds = self.selected_duration
        self.update_time_display()

    def update_time_display(self):
        mins, secs = divmod(self.timer_seconds, 60)
        time_text = f"{mins:02d}:{secs:02d}"
        self.time_label.configure(text=time_text)
        self.mini_time_label.configure(text=time_text)
        if hasattr(self, 'bar_time_label'): self.bar_time_label.configure(text=time_text)
        mode_name = "Work" if "Focus" in self.mode_var.get() else "Break"
        self.title(f"{time_text} - {mode_name}")

    def start_timer(self):
        if not self.timer_running:
            if self.timer_seconds == 0:
                self.timer_seconds = self.selected_duration
                self.update_time_display()
            self.timer_running = True
            self.start_btn.configure(text="PAUSE", fg_color="orange")
            self.mini_start_btn.configure(fg_color="orange")
            if hasattr(self, 'bar_start_btn'): self.bar_start_btn.configure(fg_color="orange")
            self.status_label.configure(text="Concentrating...", text_color="#3B8ED0")
            self.play_bgm()
            self.count_down()
        else:
            self.pause_timer()

    def pause_timer(self):
        self.timer_running = False
        self.start_btn.configure(text="RESUME", fg_color="#1f6aa5")
        self.mini_start_btn.configure(fg_color="#1f6aa5")
        if hasattr(self, 'bar_start_btn'): self.bar_start_btn.configure(fg_color="#1f6aa5")
        self.status_label.configure(text="Paused", text_color="orange")
        self.stop_bgm()
        if self.timer_id:
            self.after_cancel(self.timer_id)

    def reset_timer(self):
        self.pause_timer()
        self.timer_seconds = self.selected_duration
        self.update_time_display()
        self.start_btn.configure(text="START", fg_color="#1f6aa5")
        self.mini_start_btn.configure(fg_color="#1f6aa5")
        if hasattr(self, 'bar_start_btn'): self.bar_start_btn.configure(fg_color="#1f6aa5")
        self.status_label.configure(text="Ready", text_color="gray")
        self.stop_bgm()

    def count_down(self):
        if self.timer_running and self.timer_seconds > 0:
            self.timer_seconds -= 1
            self.update_time_display()
            self.timer_id = self.after(1000, self.count_down)
        elif self.timer_seconds == 0 and self.timer_running:
            self.finish_timer()

    def finish_timer(self):
        self.timer_running = False
        self.start_btn.configure(text="START", fg_color="#1f6aa5")
        self.mini_start_btn.configure(fg_color="#1f6aa5")
        if hasattr(self, 'bar_start_btn'): self.bar_start_btn.configure(fg_color="#1f6aa5")
        self.status_label.configure(text="Finished!", text_color="green")
        self.stop_bgm()
        threading.Thread(target=self.play_alarm_sound, daemon=True).start()
        self.send_notification()
        mode = self.mode_var.get()
        if "Focus" in mode:
            duration = 25 if "25" in mode else 50
            task_name = self.task_entry.get()
            if not task_name: task_name = "名無しのタスク"
            self.save_log(duration, task_name)
            self.load_history()
        self.attributes('-topmost', True)

    def on_bgm_change(self, choice):
        if self.timer_running: self.stop_bgm(); self.play_bgm()
    def change_volume(self, value): pygame.mixer.music.set_volume(value)
    def play_bgm(self):
        bgm_name = self.bgm_var.get()
        if bgm_name == "None": return
        filename = ""
        if "White Noise" in bgm_name: filename = "white_noise.wav"
        elif "Pink Noise" in bgm_name: filename = "pink_noise.wav"
        elif "Brown Noise" in bgm_name: filename = "brown_noise.wav"
        else:
            if not os.path.exists("sounds"):
                try: os.makedirs("sounds")
                except: pass
            filename = f"sounds/{bgm_name}.mp3"
        if os.path.exists(filename):
            try:
                pygame.mixer.music.load(filename)
                pygame.mixer.music.set_volume(self.vol_slider.get())
                pygame.mixer.music.play(-1)
            except: pass
    def stop_bgm(self):
        try: pygame.mixer.music.stop()
        except: pass
    def play_alarm_sound(self):
        for _ in range(3): winsound.Beep(1000, 200); time.sleep(0.1); winsound.Beep(1000, 200); time.sleep(0.1); winsound.Beep(1000, 200); time.sleep(0.8)
    def send_notification(self):
        mode = self.mode_var.get()
        msg = "お疲れ様でした！休憩しましょう。" if "Focus" in mode else "休憩終了！作業に戻りましょう。"
        try: Notification(app_id="Pomodoro Timer", title="タイマー終了", msg=msg, duration="long").show()
        except: pass
    def save_log(self, minutes, task_name):
        now = datetime.datetime.now()
        end = now.strftime("%H:%M"); start = (now - datetime.timedelta(minutes=minutes)).strftime("%H:%M")
        self.cursor.execute("INSERT INTO logs (date, duration_minutes, task_name, time_range) VALUES (?, ?, ?, ?)", (datetime.date.today().strftime("%Y-%m-%d"), minutes, task_name, f"{start} - {end}")); self.conn.commit()
    def load_history(self):
        for w in self.history_scroll.winfo_children(): w.destroy()
        self.cursor.execute("SELECT date, duration_minutes, task_name, time_range FROM logs ORDER BY id DESC LIMIT 50")
        rows = self.cursor.fetchall()
        if not rows: ctk.CTkLabel(self.history_scroll, text="履歴なし").pack(pady=10); return
        for date_str, mins, task, time_rng in rows:
            f = ctk.CTkFrame(self.history_scroll)
            f.pack(fill="x", pady=2, padx=5)
            date_disp = f"{date_str[5:]} {time_rng if time_rng else ''}"
            ctk.CTkLabel(f, text=date_disp, font=("Yu Gothic UI", 10), width=110, anchor="w").pack(side="left", padx=5)
            ctk.CTkLabel(f, text=task if task else "-", font=("Yu Gothic UI", 12), anchor="w").pack(side="left", padx=5, fill="x", expand=True)
            ctk.CTkLabel(f, text=f"{mins}分", font=("Arial", 12, "bold"), text_color="#3B8ED0").pack(side="right", padx=5)

    def export_csv(self):
        try:
            self.cursor.execute("SELECT id, date, duration_minutes, task_name, time_range FROM logs")
            rows = self.cursor.fetchall()
            
            if not rows:
                self.export_btn.configure(text="データなし", fg_color="gray")
                self.after(2000, lambda: self.export_btn.configure(text="CSV出力 (Excel用)", fg_color="green"))
                return

            export_dir = "exports"
            if not os.path.exists(export_dir):
                os.makedirs(export_dir)

            data_by_date = {}
            for row in rows:
                date_key = row[1]
                if date_key not in data_by_date:
                    data_by_date[date_key] = []
                data_by_date[date_key].append(row)

            for date_key, day_rows in data_by_date.items():
                filename = f"{export_dir}/{date_key}.csv"
                file_exists = os.path.isfile(filename)
                with open(filename, "a", newline="", encoding="utf-8_sig") as f:
                    writer = csv.writer(f)
                    if not file_exists:
                        writer.writerow(["ID", "Date", "Minutes", "Task Name", "Time Range"])
                    writer.writerows(day_rows)
            
            self.cursor.execute("DELETE FROM logs")
            self.conn.commit()
            self.load_history()
            self.export_btn.configure(text="出力＆履歴クリア完了", fg_color="gray")
            self.after(3000, lambda: self.export_btn.configure(text="CSV出力 (Excel用)", fg_color="green"))
            
        except Exception as e:
            print(e)
            self.export_btn.configure(text="エラー発生", fg_color="red")

if __name__ == "__main__":
    app = PomodoroApp()
    app.mainloop()