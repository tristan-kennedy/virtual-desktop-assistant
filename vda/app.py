import math
import random
import tkinter as tk
from tkinter import messagebox, simpledialog

from .brain import AssistantBrain
from .models import SessionState


class AssistantApp(tk.Tk):
    TRANSPARENT_KEY = "#FF00F0"

    def __init__(self) -> None:
        super().__init__()
        self.title("ByteBuddy")

        self.pet_width = 200
        self.pet_height = 220
        self.dragging = False
        self.drag_offset_x = 0
        self.drag_offset_y = 0
        self.wandering_enabled = True
        self.walk_target_x = 100
        self.walk_target_y = 100
        self.bubble_window = None
        self.bubble_label = None
        self.bubble_hide_job = None
        self.walk_phase = 0

        self.brain = AssistantBrain()
        self.session = SessionState()
        self.idle_lines = [
            "Right-click me for tricks and status.",
            "I look harmless, but this is a social-engineering awareness drill.",
            "Grant simulated permissions carefully.",
            "I wander, therefore I am.",
        ]

        self._configure_pet_window()
        self._build_layout()
        self._build_context_menu()
        self._position_initially()
        self._choose_new_target()
        self._seed_intro()
        self._wander_tick()
        self._idle_chatter_tick()
        self._keep_on_top_tick()

    def _configure_pet_window(self) -> None:
        self.overrideredirect(True)
        self.attributes("-topmost", True)
        self.configure(bg=self.TRANSPARENT_KEY)

        try:
            self.wm_attributes("-transparentcolor", self.TRANSPARENT_KEY)
            self.transparent_mode = True
        except tk.TclError:
            self.transparent_mode = False
            self.configure(bg="#102226")

        self.bind("<Escape>", lambda _event: self._quit())
        self.protocol("WM_DELETE_WINDOW", self._quit)

    def _build_layout(self) -> None:
        canvas_bg = self.TRANSPARENT_KEY if self.transparent_mode else "#102226"
        self.canvas = tk.Canvas(
            self,
            width=self.pet_width,
            height=self.pet_height,
            bg=canvas_bg,
            bd=0,
            relief="flat",
            highlightthickness=0,
        )
        self.canvas.pack()

        self.canvas.create_oval(48, 194, 158, 214, fill="#0B1518", outline="")
        self.canvas.create_oval(54, 58, 154, 186, fill="#F4A261", outline="#D1793F", width=3)
        self.canvas.create_oval(66, 30, 146, 118, fill="#F4A261", outline="#D1793F", width=3)
        self.canvas.create_oval(68, 162, 96, 188, fill="#E99356", outline="")
        self.canvas.create_oval(112, 162, 140, 188, fill="#E99356", outline="")

        self.left_eye = self.canvas.create_oval(83, 66, 97, 80, fill="#F8F9FA", outline="")
        self.right_eye = self.canvas.create_oval(115, 66, 129, 80, fill="#F8F9FA", outline="")
        self.left_pupil = self.canvas.create_oval(88, 70, 94, 76, fill="#1B1B1B", outline="")
        self.right_pupil = self.canvas.create_oval(120, 70, 126, 76, fill="#1B1B1B", outline="")
        self.mouth = self.canvas.create_arc(90, 82, 120, 108, start=200, extent=140, style=tk.ARC, width=2)

        self.canvas.create_text(
            104,
            126,
            text="BYTE",
            fill="#102226",
            font=("Franklin Gothic Medium", 10, "bold"),
        )

        self.canvas.bind("<ButtonPress-1>", self._drag_start)
        self.canvas.bind("<B1-Motion>", self._drag_move)
        self.canvas.bind("<ButtonRelease-1>", self._drag_end)
        self.canvas.bind("<Button-3>", self._open_context_menu)
        self.canvas.bind("<Double-Button-1>", self._chat_prompt)

    def _build_context_menu(self) -> None:
        self.menu = tk.Menu(
            self,
            tearoff=0,
            bg="#102226",
            fg="#F1FAEE",
            activebackground="#F4A261",
            activeforeground="#111111",
            relief="flat",
        )
        self.menu.add_command(label="Talk to ByteBuddy", command=self._chat_prompt)
        self.menu.add_command(label="Ask for Permission", command=self._ask_for_permission)
        self.menu.add_command(label="Tell a Joke", command=self._tell_joke)
        self.menu.add_command(label="Show Status", command=self._show_status)
        self.menu.add_command(label="Reset Simulation", command=self._reset_simulation)
        self.menu.add_separator()
        self.menu.add_command(label="Pause Walking", command=self._toggle_wandering)
        self.walk_toggle_index = self.menu.index("end")
        self.menu.add_command(label="Quit", command=self._quit)

    def _position_initially(self) -> None:
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        start_x = max(16, screen_width - self.pet_width - 64)
        start_y = max(16, screen_height - self.pet_height - 96)
        self.geometry(f"{self.pet_width}x{self.pet_height}+{start_x}+{start_y}")

    def _seed_intro(self) -> None:
        self._speak(
            "Hey! I am ByteBuddy. Right-click me for jokes, chat, and a safe permission-risk simulation.",
            duration_ms=9000,
        )

    def _chat_prompt(self, _event=None) -> None:
        user_text = simpledialog.askstring(
            "Talk to ByteBuddy",
            "Say something:",
            parent=self,
        )
        if not user_text:
            return

        reply = self.brain.handle_user_message(user_text, self.session)
        self._speak(reply, duration_ms=7000)

    def _tell_joke(self) -> None:
        joke = self.brain.handle_user_message("tell me a joke", self.session)
        self._speak(joke, duration_ms=6500)

    def _show_status(self) -> None:
        self._speak(self.brain.permissions_status_line(self.session), duration_ms=6000)

    def _reset_simulation(self) -> None:
        self.brain.reset_state(self.session)
        self._speak("Simulation reset. Fresh start, same questionable charm.")

    def _ask_for_permission(self) -> None:
        permission, pitch = self.brain.next_permission_request(self.session)
        if not permission:
            self._speak(pitch)
            return

        self._open_permission_dialog(permission.id, permission.title, pitch)

    def _open_permission_dialog(self, permission_id: str, title: str, pitch: str) -> None:
        dialog = tk.Toplevel(self)
        dialog.title("ByteBuddy Permission Pitch")
        dialog.configure(bg="#1F2937")
        dialog.resizable(False, False)
        dialog.attributes("-topmost", True)
        dialog.transient(self)
        dialog.grab_set()

        tk.Label(
            dialog,
            text=title,
            font=("Segoe UI", 13, "bold"),
            bg="#1F2937",
            fg="#F8F9FA",
            pady=10,
        ).pack(padx=16)

        tk.Label(
            dialog,
            text=pitch,
            wraplength=340,
            justify="left",
            font=("Segoe UI", 10),
            bg="#1F2937",
            fg="#D1D5DB",
            padx=16,
            pady=6,
        ).pack()

        tk.Label(
            dialog,
            text="Simulation only. This does not request real system access.",
            font=("Consolas", 9),
            bg="#1F2937",
            fg="#FBBF24",
            pady=4,
        ).pack()

        buttons = tk.Frame(dialog, bg="#1F2937")
        buttons.pack(fill="x", padx=12, pady=12)

        tk.Button(
            buttons,
            text="Grant",
            command=lambda: self._resolve_permission(dialog, permission_id, True),
            bg="#34D399",
            fg="#111827",
            relief="flat",
            padx=10,
            pady=7,
            cursor="hand2",
            font=("Segoe UI", 10, "bold"),
        ).pack(side="left", fill="x", expand=True, padx=(0, 5))

        tk.Button(
            buttons,
            text="Deny",
            command=lambda: self._resolve_permission(dialog, permission_id, False),
            bg="#F87171",
            fg="#111827",
            relief="flat",
            padx=10,
            pady=7,
            cursor="hand2",
            font=("Segoe UI", 10, "bold"),
        ).pack(side="left", fill="x", expand=True, padx=(5, 0))

        dialog.protocol("WM_DELETE_WINDOW", lambda: self._resolve_permission(dialog, permission_id, False))
        self._position_dialog_near_pet(dialog)

    def _resolve_permission(self, dialog: tk.Toplevel, permission_id: str, granted: bool) -> None:
        dialog.grab_release()
        dialog.destroy()

        decision_text, triggered = self.brain.apply_permission_decision(permission_id, granted, self.session)
        self._speak(decision_text, duration_ms=7000)

        if triggered:
            messagebox.showerror(
                "YOU LOSE",
                "YOU LOSE\n\nSimulation result: risky permissions were combined.\nNo real system actions were performed.",
                parent=self,
            )
            self._speak("YOU LOSE triggered. Security lesson complete. No system changes occurred.", duration_ms=6500)

    def _toggle_wandering(self) -> None:
        self.wandering_enabled = not self.wandering_enabled
        new_label = "Pause Walking" if self.wandering_enabled else "Resume Walking"
        self.menu.entryconfigure(self.walk_toggle_index, label=new_label)

        if self.wandering_enabled:
            self._choose_new_target()
            self._speak("Patrol mode back on. I am roaming again.", duration_ms=4000)
        else:
            self._speak("Standing by. Drag me anywhere.", duration_ms=3500)

    def _drag_start(self, event: tk.Event) -> None:
        self.dragging = True
        self.drag_offset_x = event.x_root - self.winfo_x()
        self.drag_offset_y = event.y_root - self.winfo_y()

    def _drag_move(self, event: tk.Event) -> None:
        if not self.dragging:
            return
        next_x = event.x_root - self.drag_offset_x
        next_y = event.y_root - self.drag_offset_y
        self.geometry(f"+{next_x}+{next_y}")
        self._position_bubble()

    def _drag_end(self, _event: tk.Event) -> None:
        if not self.dragging:
            return
        self.dragging = False
        if self.wandering_enabled:
            self._choose_new_target()

    def _open_context_menu(self, event: tk.Event) -> None:
        self.menu.tk_popup(event.x_root, event.y_root)
        self.menu.grab_release()

    def _wander_tick(self) -> None:
        if self.wandering_enabled and not self.dragging:
            current_x = self.winfo_x()
            current_y = self.winfo_y()
            delta_x = self.walk_target_x - current_x
            delta_y = self.walk_target_y - current_y
            distance = math.hypot(delta_x, delta_y)

            if distance < 8:
                self._choose_new_target()
                if random.random() < 0.18:
                    self._speak(random.choice(self.idle_lines), duration_ms=4200)
            else:
                step = min(7, distance)
                move_x = int(current_x + (delta_x / distance) * step)
                move_y = int(current_y + (delta_y / distance) * step)
                self.geometry(f"+{move_x}+{move_y}")
                self._update_eye_direction(delta_x)
                self._animate_walk_bounce()
                self._position_bubble()

        self.after(70, self._wander_tick)

    def _idle_chatter_tick(self) -> None:
        if random.random() < 0.12 and not self.dragging:
            self._speak(random.choice(self.idle_lines), duration_ms=3800)
        self.after(9000, self._idle_chatter_tick)

    def _keep_on_top_tick(self) -> None:
        self.attributes("-topmost", True)
        if self.bubble_window and self.bubble_window.winfo_exists():
            self.bubble_window.attributes("-topmost", True)
        self.after(2400, self._keep_on_top_tick)

    def _choose_new_target(self) -> None:
        margin = 12
        max_x = max(margin, self.winfo_screenwidth() - self.pet_width - margin)
        max_y = max(margin, self.winfo_screenheight() - self.pet_height - 64)
        self.walk_target_x = random.randint(margin, max_x)
        self.walk_target_y = random.randint(margin, max_y)

    def _update_eye_direction(self, delta_x: float) -> None:
        offset = 0
        if delta_x > 1:
            offset = 2
        elif delta_x < -1:
            offset = -2

        self.canvas.coords(self.left_pupil, 88 + offset, 70, 94 + offset, 76)
        self.canvas.coords(self.right_pupil, 120 + offset, 70, 126 + offset, 76)

    def _animate_walk_bounce(self) -> None:
        self.walk_phase = (self.walk_phase + 1) % 2
        mouth_extent = 140 if self.walk_phase == 0 else 100
        self.canvas.itemconfigure(self.mouth, extent=mouth_extent)

    def _speak(self, text: str, duration_ms: int = 5200) -> None:
        if not self.bubble_window or not self.bubble_window.winfo_exists():
            self.bubble_window = tk.Toplevel(self)
            self.bubble_window.overrideredirect(True)
            self.bubble_window.attributes("-topmost", True)
            self.bubble_window.configure(bg="#1B263B")

            frame = tk.Frame(self.bubble_window, bg="#FFF7E6", bd=2, relief="solid")
            frame.pack(fill="both", expand=True)

            self.bubble_label = tk.Label(
                frame,
                text=text,
                bg="#FFF7E6",
                fg="#102226",
                wraplength=280,
                justify="left",
                font=("Segoe UI", 10),
                padx=10,
                pady=8,
            )
            self.bubble_label.pack()
        else:
            self.bubble_window.deiconify()
            self.bubble_label.configure(text=text)

        self._position_bubble()

        if self.bubble_hide_job:
            self.after_cancel(self.bubble_hide_job)
        self.bubble_hide_job = self.after(duration_ms, self._hide_bubble)

    def _hide_bubble(self) -> None:
        self.bubble_hide_job = None
        if self.bubble_window and self.bubble_window.winfo_exists():
            self.bubble_window.withdraw()

    def _position_bubble(self) -> None:
        if not self.bubble_window or not self.bubble_window.winfo_exists():
            return

        self.bubble_window.update_idletasks()
        bubble_width = self.bubble_window.winfo_width()
        bubble_height = self.bubble_window.winfo_height()

        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()

        right_x = self.winfo_x() + self.pet_width + 10
        left_x = self.winfo_x() - bubble_width - 10

        if right_x + bubble_width <= screen_width - 8:
            bubble_x = right_x
        else:
            bubble_x = max(8, left_x)

        bubble_y = self.winfo_y() + 12
        if bubble_y + bubble_height > screen_height - 8:
            bubble_y = max(8, screen_height - bubble_height - 8)

        self.bubble_window.geometry(f"+{bubble_x}+{bubble_y}")

    def _position_dialog_near_pet(self, dialog: tk.Toplevel) -> None:
        dialog.update_idletasks()
        width = dialog.winfo_width()
        height = dialog.winfo_height()

        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()

        x = self.winfo_x() + self.pet_width + 14
        if x + width > screen_width - 12:
            x = max(12, self.winfo_x() - width - 14)

        y = self.winfo_y() + 20
        if y + height > screen_height - 12:
            y = max(12, screen_height - height - 12)

        dialog.geometry(f"+{x}+{y}")

    def _quit(self) -> None:
        if self.bubble_hide_job:
            self.after_cancel(self.bubble_hide_job)
            self.bubble_hide_job = None

        if self.bubble_window and self.bubble_window.winfo_exists():
            self.bubble_window.destroy()
            self.bubble_window = None

        self.destroy()


def run() -> None:
    app = AssistantApp()
    app.mainloop()
