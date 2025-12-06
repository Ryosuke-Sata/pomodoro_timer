import customtkinter as ctk
import sqlite3
import datetime
import winsound
import threading
import time
import csv
import os
from winotify import Notification, audio

# --- 設定 ---
ctk.set_appearance_mode("System")
ctk.set_default_color_theme("blue")

class PomodoroApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        # アプリ基本設定
        self.title("Modern Pomodoro")
        self.geometry("400x600")
        self.resizable(False, False)

        # 変数
        self.timer_running = False
        self.timer_seconds = 25 * 60
        self.selected_duration = 25 * 60
        self.timer_id = None
        self.is_mini_mode = False
        self.previous_geometry = "400x600"
        
        # データベース初期化＆更新
        self.init_db()

        # UIレイアウト作成
        self.create_main_layout()
        self.create_mini_layout()
        
        # 初期状態はメインモードを表示
        self.show_main_view()

    def init_db(self):
        """DB初期化とテーブル更新（タスク名カラムの追加）"""
        self.conn = sqlite3.connect("work_log.db")
        self.cursor = self.conn.cursor()
        
        # テーブル作成
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT,
                duration_minutes INTEGER,
                task_name TEXT
            )
        """)
        
        # 既存DBへのカラム追加（アップデート対応）
        try:
            self.cursor.execute("SELECT task_name FROM logs LIMIT 1")
        except sqlite3.OperationalError:
            self.cursor.execute("ALTER TABLE logs ADD COLUMN task_name TEXT")
            self.conn.commit()
            
        self.conn.commit()

    # --- UI構築 ---

    def create_main_layout(self):
        """通常モードのUI作成"""
        self.main_frame = ctk.CTkFrame(self, fg_color="transparent")
        
        # タブ
        self.tabview = ctk.CTkTabview(self.main_frame, width=380, height=500)
        self.tabview.pack(padx=10, pady=5, fill="both", expand=True)
        self.tabview.add("Timer")
        self.tabview.add("History")

        # --- Timer Tab ---
        t_frame = self.tabview.tab("Timer")

        # 1. タスク名入力
        ctk.CTkLabel(t_frame, text="作業内容 (Task Name)", font=("Arial", 12)).pack(pady=(10, 0))
        self.task_entry = ctk.CTkEntry(t_frame, placeholder_text="例: 英語の勉強", width=250)
        self.task_entry.pack(pady=5)

        # 2. モード選択
        self.mode_var = ctk.StringVar(value="Focus 25")
        self.mode_segment = ctk.CTkSegmentedButton(
            t_frame,
            values=["Focus 25", "Focus 50", "Break 5", "Break 15"],
            command=self.change_mode,
            variable=self.mode_var
        )
        self.mode_segment.pack(pady=15)

        # 3. タイマー表示
        self.time_label = ctk.CTkLabel(t_frame, text="25:00", font=("Roboto Medium", 80))
        self.time_label.pack(pady=10)

        # 4. コントロールボタン
        btn_frame = ctk.CTkFrame(t_frame, fg_color="transparent")
        btn_frame.pack(pady=10)
        
        self.start_btn = ctk.CTkButton(btn_frame, text="START", command=self.start_timer, width=100, height=40, font=("Arial", 16))
        self.start_btn.grid(row=0, column=0, padx=10)
        
        self.reset_btn = ctk.CTkButton(btn_frame, text="RESET", command=self.reset_timer, width=100, height=40, fg_color="gray", hover_color="darkgray", font=("Arial", 16))
        self.reset_btn.grid(row=0, column=1, padx=10)

        # 5. オプション（最前面 & ミニモード）
        opt_frame = ctk.CTkFrame(t_frame, fg_color="transparent")
        opt_frame.pack(pady=20)
        
        self.top_switch = ctk.CTkSwitch(opt_frame, text="常に最前面", command=self.toggle_always_on_top)
        self.top_switch.pack(side="left", padx=10)
        
        self.mini_btn = ctk.CTkButton(opt_frame, text="ミニモードへ", command=self.switch_to_mini, width=80, fg_color="teal")
        self.mini_btn.pack(side="left", padx=10)

        # ステータス
        self.status_label = ctk.CTkLabel(t_frame, text="Ready", text_color="gray")
        self.status_label.pack(side="bottom", pady=5)

        # --- History Tab ---
        h_frame = self.tabview.tab("History")
        ctk.CTkLabel(h_frame, text="作業履歴", font=("Arial", 16, "bold")).pack(pady=10)
        
        self.history_scroll = ctk.CTkScrollableFrame(h_frame, width=320, height=300)
        self.history_scroll.pack()

        # CSVエクスポートボタン
        self.export_btn = ctk.CTkButton(h_frame, text="CSV出力 (Excel用)", command=self.export_csv, fg_color="green", hover_color="darkgreen")
        self.export_btn.pack(pady=10)
        
        ctk.CTkButton(h_frame, text="履歴更新", command=self.load_history, height=30).pack(pady=5)
        
        self.load_history()

    def create_mini_layout(self):
        """ミニモードのUI作成"""
        self.mini_frame = ctk.CTkFrame(self, fg_color="transparent")
        
        # 時間表示（小）
        self.mini_time_label = ctk.CTkLabel(self.mini_frame, text="25:00", font=("Roboto Medium", 40))
        self.mini_time_label.pack(pady=(10, 5))
        
        # コントロール（小）
        btn_frame = ctk.CTkFrame(self.mini_frame, fg_color="transparent")
        btn_frame.pack(pady=5)
        
        self.mini_start_btn = ctk.CTkButton(btn_frame, text="⏯", command=self.start_timer, width=40, height=30)
        self.mini_start_btn.grid(row=0, column=0, padx=5)
        
        ctk.CTkButton(btn_frame, text="⏹", command=self.reset_timer, width=40, height=30, fg_color="gray").grid(row=0, column=1, padx=5)
        
        # 戻るボタン
        ctk.CTkButton(self.mini_frame, text="拡大 ⤢", command=self.switch_to_main, width=60, height=20, fg_color="transparent", border_width=1).pack(pady=5)

    # --- モード切替ロジック ---

    def show_main_view(self):
        self.mini_frame.pack_forget()
        self.main_frame.pack(fill="both", expand=True)

    def switch_to_mini(self):
        self.is_mini_mode = True
        self.main_frame.pack_forget()
        self.mini_frame.pack(fill="both", expand=True)
        self.previous_geometry = self.geometry() # サイズ記憶
        self.geometry("200x150") # ミニサイズ
        # ミニモード時は自動で最前面にするのが親切
        self.attributes('-topmost', True) 

    def switch_to_main(self):
        self.is_mini_mode = False
        self.mini_frame.pack_forget()
        self.main_frame.pack(fill="both", expand=True)
        self.geometry("400x600") # 元のサイズ
        # スイッチの状態に合わせて最前面設定を戻す
        self.toggle_always_on_top()

    # --- タイマーロジック ---

    def toggle_always_on_top(self):
        state = self.top_switch.get() == 1
        # ミニモード中は常に最前面、そうでなければスイッチ依存
        if self.is_mini_mode:
            self.attributes('-topmost', True)
        else:
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

    def start_timer(self):
        if not self.timer_running:
            self.timer_running = True
            self.start_btn.configure(text="PAUSE", fg_color="orange")
            self.mini_start_btn.configure(fg_color="orange") # ミニモード用
            self.status_label.configure(text="Concentrating...", text_color="#3B8ED0")
            self.count_down()
        else:
            self.pause_timer()

    def pause_timer(self):
        self.timer_running = False
        self.start_btn.configure(text="RESUME", fg_color="#1f6aa5")
        self.mini_start_btn.configure(fg_color="#1f6aa5")
        self.status_label.configure(text="Paused", text_color="orange")
        if self.timer_id:
            self.after_cancel(self.timer_id)

    def reset_timer(self):
        self.pause_timer()
        self.timer_seconds = self.selected_duration
        self.update_time_display()
        self.start_btn.configure(text="START", fg_color="#1f6aa5")
        self.mini_start_btn.configure(fg_color="#1f6aa5")
        self.status_label.configure(text="Ready", text_color="gray")

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
        self.status_label.configure(text="Finished!", text_color="green")
        
        # 1. 音再生
        threading.Thread(target=self.play_alarm_sound, daemon=True).start()

        # 2. Windowsネイティブ通知 (トースト)
        self.send_notification()

        # 3. ログ保存
        mode = self.mode_var.get()
        if "Focus" in mode:
            duration = 25 if "25" in mode else 50
            task_name = self.task_entry.get()
            if not task_name:
                task_name = "名無しのタスク"
            self.save_log(duration, task_name)
            self.load_history()

        # ウィンドウを強調
        self.attributes('-topmost', True)
        if not self.is_mini_mode:
             # 少し経ったら設定に戻すなどの処理も可能だが、ここでは気づかせるために前面維持
             pass

    def play_alarm_sound(self):
        for _ in range(3): 
            winsound.Beep(1000, 200)
            time.sleep(0.1)
            winsound.Beep(1000, 200)
            time.sleep(0.1)
            winsound.Beep(1000, 200)
            time.sleep(0.8)

    def send_notification(self):
        """Windows 11 トースト通知"""
        mode = self.mode_var.get()
        msg = "お疲れ様でした！休憩しましょう。" if "Focus" in mode else "休憩終了！作業に戻りましょう。"
        
        toast = Notification(
            app_id="Pomodoro Timer",
            title="タイマー終了",
            msg=msg,
            duration="long"
        )
        toast.set_audio(audio.Default, loop=False)
        toast.show()

    # --- データ管理 ---

    def save_log(self, minutes, task_name):
        today = datetime.date.today().strftime("%Y-%m-%d")
        self.cursor.execute(
            "INSERT INTO logs (date, duration_minutes, task_name) VALUES (?, ?, ?)",
            (today, minutes, task_name)
        )
        self.conn.commit()

    def load_history(self):
        for widget in self.history_scroll.winfo_children():
            widget.destroy()

        # 詳細表示に変更（タスク名も見せる）
        self.cursor.execute("SELECT date, duration_minutes, task_name FROM logs ORDER BY id DESC LIMIT 50")
        rows = self.cursor.fetchall()

        if not rows:
            ctk.CTkLabel(self.history_scroll, text="履歴なし").pack(pady=10)
            return

        for date_str, mins, task in rows:
            f = ctk.CTkFrame(self.history_scroll)
            f.pack(fill="x", pady=2, padx=5)
            
            # 日付
            ctk.CTkLabel(f, text=date_str, font=("Arial", 10), width=80).pack(side="left", padx=5)
            # タスク名
            ctk.CTkLabel(f, text=task if task else "-", font=("Arial", 12), anchor="w").pack(side="left", padx=5, fill="x", expand=True)
            # 時間
            ctk.CTkLabel(f, text=f"{mins}分", font=("Arial", 12, "bold"), text_color="#3B8ED0").pack(side="right", padx=5)

    def export_csv(self):
        """データベースの内容をCSVに出力"""
        try:
            filename = f"pomodoro_log_{datetime.date.today()}.csv"
            
            self.cursor.execute("SELECT * FROM logs")
            rows = self.cursor.fetchall()
            
            with open(filename, "w", newline="", encoding="utf-8_sig") as f:
                writer = csv.writer(f)
                writer.writerow(["ID", "Date", "Minutes", "Task Name"]) # ヘッダー
                writer.writerows(rows)
            
            # 完了通知をUI上に簡易表示（今回はボタン文字を変える）
            self.export_btn.configure(text=f"出力完了: {filename}", fg_color="gray")
            self.after(3000, lambda: self.export_btn.configure(text="CSV出力 (Excel用)", fg_color="green"))
            
            # フォルダを開く
            os.startfile(".")
            
        except Exception as e:
            print(e)
            self.export_btn.configure(text="エラー発生", fg_color="red")

if __name__ == "__main__":
    app = PomodoroApp()
    app.mainloop()