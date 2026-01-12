#!/usr/bin/env python3
"""
Password Kraken - An encrypted password manager with 4-digit PIN protection.
Native Windows theme support with dark/light mode detection.
"""

import os
import sys
import json
import csv
import base64
import ctypes
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from pathlib import Path
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import secrets
import string

# Windows dark mode constants
DWMWA_USE_IMMERSIVE_DARK_MODE = 20


def get_script_dir() -> Path:
    """Get the directory where the script is located."""
    return Path(__file__).parent.resolve()


def is_windows_dark_mode() -> bool:
    """Check if Windows is using dark mode."""
    try:
        import winreg
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize"
        )
        value, _ = winreg.QueryValueEx(key, "AppsUseLightTheme")
        winreg.CloseKey(key)
        return value == 0
    except Exception:
        return False


def set_window_dark_mode(hwnd: int, dark: bool):
    """Set the window title bar to dark/light mode."""
    try:
        dwmapi = ctypes.windll.dwmapi
        value = ctypes.c_int(1 if dark else 0)
        dwmapi.DwmSetWindowAttribute(
            hwnd,
            DWMWA_USE_IMMERSIVE_DARK_MODE,
            ctypes.byref(value),
            ctypes.sizeof(value)
        )
    except Exception:
        pass


class ThemeColors:
    """Color scheme for dark and light modes."""

    def __init__(self, dark_mode: bool):
        self.dark_mode = dark_mode

        if dark_mode:
            self.bg = "#1e1e1e"
            self.fg = "#d4d4d4"
            self.entry_bg = "#2d2d2d"
            self.entry_fg = "#d4d4d4"
            self.button_bg = "#3c3c3c"
            self.button_fg = "#d4d4d4"
            self.select_bg = "#094771"
            self.select_fg = "#ffffff"
            self.border = "#3c3c3c"
            self.treeview_bg = "#1e1e1e"
            self.treeview_fg = "#d4d4d4"
            self.treeview_select_bg = "#094771"
            self.treeview_select_fg = "#ffffff"
            self.status_bg = "#007acc"
            self.status_fg = "#ffffff"
        else:
            self.bg = "#f0f0f0"
            self.fg = "#000000"
            self.entry_bg = "#ffffff"
            self.entry_fg = "#000000"
            self.button_bg = "#e1e1e1"
            self.button_fg = "#000000"
            self.select_bg = "#0078d7"
            self.select_fg = "#ffffff"
            self.border = "#adadad"
            self.treeview_bg = "#ffffff"
            self.treeview_fg = "#000000"
            self.treeview_select_bg = "#0078d7"
            self.treeview_select_fg = "#ffffff"
            self.status_bg = "#0078d7"
            self.status_fg = "#ffffff"


class PasswordKraken:
    """Encrypted password manager backend."""

    def __init__(self, data_file: str = "passwords.kraken"):
        script_dir = get_script_dir()
        self.data_file = script_dir / data_file
        self.salt_file = script_dir / (data_file + ".salt")
        self.fernet = None
        self.passwords = {}

    def _derive_key(self, pin: str, salt: bytes) -> bytes:
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=480000,
        )
        return base64.urlsafe_b64encode(kdf.derive(pin.encode()))

    def vault_exists(self) -> bool:
        return self.data_file.exists() and self.salt_file.exists()

    def setup(self, pin: str) -> bool:
        if len(pin) != 4 or not pin.isdigit():
            return False

        salt = os.urandom(16)
        self.salt_file.write_bytes(salt)
        key = self._derive_key(pin, salt)
        self.fernet = Fernet(key)
        self.passwords = {}
        self._save()
        return True

    def unlock(self, pin: str) -> bool:
        if not self.vault_exists():
            return False

        salt = self.salt_file.read_bytes()
        key = self._derive_key(pin, salt)
        self.fernet = Fernet(key)

        try:
            self._load()
            return True
        except Exception:
            self.fernet = None
            return False

    def _save(self):
        if not self.fernet:
            raise RuntimeError("Vault is locked")
        data = json.dumps(self.passwords).encode()
        self.data_file.write_bytes(self.fernet.encrypt(data))

    def _load(self):
        if not self.fernet:
            raise RuntimeError("Vault is locked")
        encrypted = self.data_file.read_bytes()
        self.passwords = json.loads(self.fernet.decrypt(encrypted).decode())

    def add_password(self, name: str, username: str, password: str, notes: str = ""):
        self.passwords[name.lower()] = {
            "name": name,
            "username": username,
            "password": password,
            "notes": notes
        }
        self._save()

    def get_password(self, name: str) -> dict | None:
        return self.passwords.get(name.lower())

    def delete_password(self, name: str) -> bool:
        if name.lower() in self.passwords:
            del self.passwords[name.lower()]
            self._save()
            return True
        return False

    def search(self, query: str) -> list:
        query = query.lower()
        return [
            entry for key, entry in self.passwords.items()
            if query in key or query in entry.get("username", "").lower()
        ]

    def get_all(self) -> list:
        return list(self.passwords.values())

    def change_pin(self, new_pin: str) -> bool:
        if len(new_pin) != 4 or not new_pin.isdigit():
            return False

        salt = os.urandom(16)
        self.salt_file.write_bytes(salt)
        key = self._derive_key(new_pin, salt)
        self.fernet = Fernet(key)
        self._save()
        return True


def generate_password(length: int = 16) -> str:
    alphabet = string.ascii_letters + string.digits + string.punctuation
    return ''.join(secrets.choice(alphabet) for _ in range(length))


class ThemedDialog(tk.Toplevel):
    """Base class for themed dialogs."""

    def __init__(self, parent, title: str, theme: ThemeColors):
        super().__init__(parent)
        self.theme = theme
        self.title(title)
        self.transient(parent)
        self.grab_set()
        self.resizable(False, False)

        self.configure(bg=theme.bg)

        # Apply dark title bar
        self.update_idletasks()
        set_window_dark_mode(self.winfo_id(), theme.dark_mode)

    def center_on_parent(self, width: int, height: int):
        self.geometry(f"{width}x{height}")
        self.update_idletasks()

        parent = self.master
        px = parent.winfo_x()
        py = parent.winfo_y()
        pw = parent.winfo_width()
        ph = parent.winfo_height()

        x = px + (pw - width) // 2
        y = py + (ph - height) // 2
        self.geometry(f"+{x}+{y}")


class PinDialog(ThemedDialog):
    """Dialog for PIN entry."""

    def __init__(self, parent, title: str, theme: ThemeColors, confirm: bool = False):
        super().__init__(parent, title, theme)
        self.pin = None
        self.confirm = confirm

        self.create_widgets()
        self.center_on_parent(280, 180 if not confirm else 240)

        self.pin_entry.focus_set()
        self.wait_window(self)

    def create_widgets(self):
        frame = tk.Frame(self, bg=self.theme.bg, padx=20, pady=20)
        frame.pack(fill=tk.BOTH, expand=True)

        tk.Label(
            frame, text="Enter 4-digit PIN:",
            bg=self.theme.bg, fg=self.theme.fg,
            font=("Segoe UI", 10)
        ).pack(pady=(0, 8))

        self.pin_entry = tk.Entry(
            frame, show="*",
            font=("Segoe UI", 16), justify="center", width=8,
            bg=self.theme.entry_bg, fg=self.theme.entry_fg,
            insertbackground=self.theme.fg,
            relief="flat", highlightthickness=1,
            highlightbackground=self.theme.border,
            highlightcolor=self.theme.select_bg
        )
        self.pin_entry.pack(pady=5, ipady=4)
        self.pin_entry.bind("<Return>", lambda e: self.on_submit())
        self.pin_entry.bind("<KeyRelease>", self.validate_input)

        if self.confirm:
            tk.Label(
                frame, text="Confirm PIN:",
                bg=self.theme.bg, fg=self.theme.fg,
                font=("Segoe UI", 10)
            ).pack(pady=(12, 8))

            self.confirm_entry = tk.Entry(
                frame, show="*",
                font=("Segoe UI", 16), justify="center", width=8,
                bg=self.theme.entry_bg, fg=self.theme.entry_fg,
                insertbackground=self.theme.fg,
                relief="flat", highlightthickness=1,
                highlightbackground=self.theme.border,
                highlightcolor=self.theme.select_bg
            )
            self.confirm_entry.pack(pady=5, ipady=4)
            self.confirm_entry.bind("<Return>", lambda e: self.on_submit())
            self.confirm_entry.bind("<KeyRelease>", self.validate_input)

        btn = tk.Button(
            frame, text="Unlock",
            font=("Segoe UI", 9),
            bg=self.theme.status_bg, fg=self.theme.status_fg,
            activebackground=self.theme.select_bg,
            activeforeground=self.theme.select_fg,
            relief="flat", cursor="hand2",
            command=self.on_submit
        )
        btn.pack(pady=(16, 0), ipadx=20, ipady=4)

    def validate_input(self, event):
        entry = event.widget
        value = entry.get()
        filtered = ''.join(c for c in value if c.isdigit())[:4]
        if value != filtered:
            entry.delete(0, tk.END)
            entry.insert(0, filtered)

    def on_submit(self):
        pin = self.pin_entry.get()

        if len(pin) != 4 or not pin.isdigit():
            messagebox.showerror("Error", "PIN must be exactly 4 digits", parent=self)
            return

        if self.confirm:
            confirm_pin = self.confirm_entry.get()
            if pin != confirm_pin:
                messagebox.showerror("Error", "PINs do not match", parent=self)
                return

        self.pin = pin
        self.destroy()


class AddEditDialog(ThemedDialog):
    """Dialog for adding/editing password entries."""

    def __init__(self, parent, theme: ThemeColors, entry: dict = None):
        self.entry = entry
        self.result = None
        title = "Edit Entry" if entry else "Add Entry"
        super().__init__(parent, title, theme)

        self.create_widgets()
        self.center_on_parent(400, 380)

        self.name_entry.focus_set()
        self.wait_window(self)

    def create_widgets(self):
        frame = tk.Frame(self, bg=self.theme.bg, padx=20, pady=16)
        frame.pack(fill=tk.BOTH, expand=True)

        # Name
        tk.Label(
            frame, text="Name:", anchor="w",
            bg=self.theme.bg, fg=self.theme.fg,
            font=("Segoe UI", 9)
        ).pack(fill=tk.X)

        self.name_entry = tk.Entry(
            frame, font=("Segoe UI", 10),
            bg=self.theme.entry_bg, fg=self.theme.entry_fg,
            insertbackground=self.theme.fg,
            relief="flat", highlightthickness=1,
            highlightbackground=self.theme.border,
            highlightcolor=self.theme.select_bg
        )
        self.name_entry.pack(fill=tk.X, pady=(2, 10), ipady=4)

        # Username
        tk.Label(
            frame, text="Username / Email:", anchor="w",
            bg=self.theme.bg, fg=self.theme.fg,
            font=("Segoe UI", 9)
        ).pack(fill=tk.X)

        self.username_entry = tk.Entry(
            frame, font=("Segoe UI", 10),
            bg=self.theme.entry_bg, fg=self.theme.entry_fg,
            insertbackground=self.theme.fg,
            relief="flat", highlightthickness=1,
            highlightbackground=self.theme.border,
            highlightcolor=self.theme.select_bg
        )
        self.username_entry.pack(fill=tk.X, pady=(2, 10), ipady=4)

        # Password
        tk.Label(
            frame, text="Password:", anchor="w",
            bg=self.theme.bg, fg=self.theme.fg,
            font=("Segoe UI", 9)
        ).pack(fill=tk.X)

        pw_frame = tk.Frame(frame, bg=self.theme.bg)
        pw_frame.pack(fill=tk.X, pady=(2, 6))

        self.password_entry = tk.Entry(
            pw_frame, font=("Segoe UI", 10), show="*",
            bg=self.theme.entry_bg, fg=self.theme.entry_fg,
            insertbackground=self.theme.fg,
            relief="flat", highlightthickness=1,
            highlightbackground=self.theme.border,
            highlightcolor=self.theme.select_bg
        )
        self.password_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=4)

        gen_btn = tk.Button(
            pw_frame, text="Generate",
            font=("Segoe UI", 9),
            bg=self.theme.button_bg, fg=self.theme.button_fg,
            activebackground=self.theme.border,
            relief="flat", cursor="hand2",
            command=self.generate_pw
        )
        gen_btn.pack(side=tk.RIGHT, padx=(8, 0), ipady=2)

        # Show password checkbox
        self.show_pw_var = tk.BooleanVar()
        show_cb = tk.Checkbutton(
            frame, text="Show password",
            variable=self.show_pw_var,
            command=self.toggle_password,
            bg=self.theme.bg, fg=self.theme.fg,
            activebackground=self.theme.bg,
            activeforeground=self.theme.fg,
            selectcolor=self.theme.entry_bg,
            font=("Segoe UI", 9)
        )
        show_cb.pack(anchor="w", pady=(0, 10))

        # Notes
        tk.Label(
            frame, text="Notes:", anchor="w",
            bg=self.theme.bg, fg=self.theme.fg,
            font=("Segoe UI", 9)
        ).pack(fill=tk.X)

        self.notes_text = tk.Text(
            frame, font=("Segoe UI", 10), height=4,
            bg=self.theme.entry_bg, fg=self.theme.entry_fg,
            insertbackground=self.theme.fg,
            relief="flat", highlightthickness=1,
            highlightbackground=self.theme.border,
            highlightcolor=self.theme.select_bg
        )
        self.notes_text.pack(fill=tk.X, pady=(2, 16))

        # Buttons
        btn_frame = tk.Frame(frame, bg=self.theme.bg)
        btn_frame.pack(fill=tk.X)

        cancel_btn = tk.Button(
            btn_frame, text="Cancel",
            font=("Segoe UI", 9),
            bg=self.theme.button_bg, fg=self.theme.button_fg,
            activebackground=self.theme.border,
            relief="flat", cursor="hand2",
            command=self.destroy
        )
        cancel_btn.pack(side=tk.RIGHT, ipadx=12, ipady=4)

        save_btn = tk.Button(
            btn_frame, text="Save",
            font=("Segoe UI", 9),
            bg=self.theme.status_bg, fg=self.theme.status_fg,
            activebackground=self.theme.select_bg,
            relief="flat", cursor="hand2",
            command=self.on_save
        )
        save_btn.pack(side=tk.RIGHT, padx=(0, 8), ipadx=16, ipady=4)

        # Populate if editing
        if self.entry:
            self.name_entry.insert(0, self.entry.get("name", ""))
            self.username_entry.insert(0, self.entry.get("username", ""))
            self.password_entry.insert(0, self.entry.get("password", ""))
            self.notes_text.insert("1.0", self.entry.get("notes", ""))

    def toggle_password(self):
        self.password_entry.config(show="" if self.show_pw_var.get() else "*")

    def generate_pw(self):
        self.password_entry.delete(0, tk.END)
        self.password_entry.insert(0, generate_password())

    def on_save(self):
        name = self.name_entry.get().strip()
        if not name:
            messagebox.showerror("Error", "Name is required", parent=self)
            return

        self.result = {
            "name": name,
            "username": self.username_entry.get().strip(),
            "password": self.password_entry.get(),
            "notes": self.notes_text.get("1.0", tk.END).strip()
        }
        self.destroy()


class PasswordKrakenGUI:
    """Main application window."""

    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Password Kraken")
        self.root.geometry("750x500")
        self.root.minsize(600, 400)

        # Detect theme and set colors
        self.dark_mode = is_windows_dark_mode()
        self.theme = ThemeColors(self.dark_mode)

        # Load icon
        self.load_icon()

        # Configure root
        self.root.configure(bg=self.theme.bg)

        # Apply dark title bar after window is mapped
        self.root.after(10, self.apply_title_bar_theme)

        self.kraken = PasswordKraken()
        self.setup_styles()
        self.create_widgets()
        self.bind_shortcuts()

        # Center on screen
        self.center_window()

        # Prompt for PIN after window appears
        self.root.after(100, self.prompt_for_pin)

    def bind_shortcuts(self):
        """Bind keyboard shortcuts."""
        self.root.bind("<Control-c>", lambda e: self.copy_password())
        self.root.bind("<Control-n>", lambda e: self.add_entry())
        self.root.bind("<Delete>", lambda e: self.delete_entry())
        self.root.bind("<Return>", lambda e: self.edit_entry())
        self.root.bind("<Control-f>", lambda e: self.search_entry.focus_set())

    def load_icon(self):
        icon_path = get_script_dir() / "kraken.ico"
        if icon_path.exists():
            try:
                self.root.iconbitmap(str(icon_path))
            except Exception:
                pass

    def apply_title_bar_theme(self):
        hwnd = ctypes.windll.user32.GetParent(self.root.winfo_id())
        set_window_dark_mode(hwnd, self.dark_mode)

    def center_window(self):
        self.root.update_idletasks()
        w = self.root.winfo_width()
        h = self.root.winfo_height()
        x = (self.root.winfo_screenwidth() - w) // 2
        y = (self.root.winfo_screenheight() - h) // 2
        self.root.geometry(f"+{x}+{y}")

    def setup_styles(self):
        style = ttk.Style()

        # Use clam theme as base for customization
        style.theme_use("clam")

        # Treeview styling
        style.configure(
            "Treeview",
            background=self.theme.treeview_bg,
            foreground=self.theme.treeview_fg,
            fieldbackground=self.theme.treeview_bg,
            rowheight=28,
            font=("Segoe UI", 10)
        )
        style.configure(
            "Treeview.Heading",
            background=self.theme.button_bg,
            foreground=self.theme.fg,
            font=("Segoe UI", 9, "bold")
        )
        style.map(
            "Treeview",
            background=[("selected", self.theme.treeview_select_bg)],
            foreground=[("selected", self.theme.treeview_select_fg)]
        )
        style.map(
            "Treeview.Heading",
            background=[("active", self.theme.border)]
        )

        # Scrollbar styling
        style.configure(
            "Vertical.TScrollbar",
            background=self.theme.button_bg,
            troughcolor=self.theme.bg,
            borderwidth=0,
            arrowcolor=self.theme.fg
        )
        style.map(
            "Vertical.TScrollbar",
            background=[("active", self.theme.border)]
        )

    def create_widgets(self):
        # Main container
        main = tk.Frame(self.root, bg=self.theme.bg, padx=12, pady=12)
        main.pack(fill=tk.BOTH, expand=True)

        # Header
        header = tk.Frame(main, bg=self.theme.bg)
        header.pack(fill=tk.X, pady=(0, 12))

        tk.Label(
            header, text="Password Kraken",
            bg=self.theme.bg, fg=self.theme.fg,
            font=("Segoe UI", 14, "bold")
        ).pack(side=tk.LEFT)

        # Search
        search_frame = tk.Frame(header, bg=self.theme.bg)
        search_frame.pack(side=tk.RIGHT)

        tk.Label(
            search_frame, text="Search:",
            bg=self.theme.bg, fg=self.theme.fg,
            font=("Segoe UI", 9)
        ).pack(side=tk.LEFT, padx=(0, 6))

        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", lambda *args: self.on_search())

        self.search_entry = tk.Entry(
            search_frame, textvariable=self.search_var,
            font=("Segoe UI", 10), width=25,
            bg=self.theme.entry_bg, fg=self.theme.entry_fg,
            insertbackground=self.theme.fg,
            relief="flat", highlightthickness=1,
            highlightbackground=self.theme.border,
            highlightcolor=self.theme.select_bg
        )
        self.search_entry.pack(side=tk.LEFT, ipady=3)

        # Toolbar
        toolbar = tk.Frame(main, bg=self.theme.bg)
        toolbar.pack(fill=tk.X, pady=(0, 8))

        btn_style = {
            "font": ("Segoe UI", 9),
            "bg": self.theme.button_bg,
            "fg": self.theme.button_fg,
            "activebackground": self.theme.border,
            "activeforeground": self.theme.fg,
            "relief": "flat",
            "cursor": "hand2"
        }

        tk.Button(toolbar, text="+ Add", command=self.add_entry, **btn_style).pack(side=tk.LEFT, padx=(0, 4), ipadx=8, ipady=3)
        tk.Button(toolbar, text="Edit", command=self.edit_entry, **btn_style).pack(side=tk.LEFT, padx=(0, 4), ipadx=8, ipady=3)
        tk.Button(toolbar, text="Delete", command=self.delete_entry, **btn_style).pack(side=tk.LEFT, padx=(0, 4), ipadx=8, ipady=3)
        tk.Button(toolbar, text="Copy Password", command=self.copy_password, **btn_style).pack(side=tk.LEFT, padx=(0, 4), ipadx=8, ipady=3)
        tk.Button(toolbar, text="Import", command=self.import_passwords, **btn_style).pack(side=tk.LEFT, padx=(0, 4), ipadx=8, ipady=3)
        tk.Button(toolbar, text="Export", command=self.export_passwords, **btn_style).pack(side=tk.LEFT, padx=(0, 4), ipadx=8, ipady=3)
        tk.Button(toolbar, text="Change PIN", command=self.change_pin, **btn_style).pack(side=tk.RIGHT, ipadx=8, ipady=3)

        # Password list
        list_frame = tk.Frame(main, bg=self.theme.bg)
        list_frame.pack(fill=tk.BOTH, expand=True)

        columns = ("name", "username", "notes")
        self.tree = ttk.Treeview(list_frame, columns=columns, show="headings", selectmode="browse")

        self.tree.heading("name", text="Name", anchor="w")
        self.tree.heading("username", text="Username / Email", anchor="w")
        self.tree.heading("notes", text="Notes", anchor="w")

        self.tree.column("name", width=150, minwidth=100)
        self.tree.column("username", width=220, minwidth=150)
        self.tree.column("notes", width=300, minwidth=100)

        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)

        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.tree.bind("<Double-1>", lambda e: self.edit_entry())

        # Status bar
        self.status_var = tk.StringVar(value="Locked")
        status = tk.Label(
            main, textvariable=self.status_var,
            bg=self.theme.status_bg, fg=self.theme.status_fg,
            font=("Segoe UI", 9), anchor="w", padx=8, pady=4
        )
        status.pack(fill=tk.X, pady=(8, 0))

    def prompt_for_pin(self):
        if self.kraken.vault_exists():
            attempts = 3
            while attempts > 0:
                dialog = PinDialog(self.root, "Unlock Vault", self.theme)
                if dialog.pin is None:
                    self.root.destroy()
                    return

                if self.kraken.unlock(dialog.pin):
                    self.status_var.set(f"Unlocked  |  {len(self.kraken.passwords)} entries")
                    self.refresh_list()
                    return
                else:
                    attempts -= 1
                    if attempts > 0:
                        messagebox.showerror("Error", f"Invalid PIN. {attempts} attempts remaining.")
                    else:
                        messagebox.showerror("Error", "Too many failed attempts.")
                        self.root.destroy()
                        return
        else:
            messagebox.showinfo(
                "Welcome",
                "No vault found. Let's create one!\n\nYou'll need to set a 4-digit PIN."
            )
            dialog = PinDialog(self.root, "Create PIN", self.theme, confirm=True)

            if dialog.pin is None:
                self.root.destroy()
                return

            if self.kraken.setup(dialog.pin):
                self.status_var.set("Vault created  |  0 entries")
                messagebox.showinfo("Success", "Password vault created successfully!")
            else:
                messagebox.showerror("Error", "Failed to create vault")
                self.root.destroy()

    def refresh_list(self, entries=None):
        self.tree.delete(*self.tree.get_children())

        if entries is None:
            entries = self.kraken.get_all()

        for entry in sorted(entries, key=lambda x: x.get("name", "").lower()):
            notes_preview = entry.get("notes", "")[:50]
            if len(entry.get("notes", "")) > 50:
                notes_preview += "..."

            self.tree.insert("", tk.END, values=(
                entry.get("name", ""),
                entry.get("username", ""),
                notes_preview
            ))

        total = len(self.kraken.passwords)
        showing = len(entries)
        if showing == total:
            self.status_var.set(f"Unlocked  |  {total} entries")
        else:
            self.status_var.set(f"Showing {showing} of {total} entries")

    def on_search(self):
        query = self.search_var.get().strip()
        if query:
            self.refresh_list(self.kraken.search(query))
        else:
            self.refresh_list()

    def get_selected_entry(self) -> dict | None:
        selection = self.tree.selection()
        if not selection:
            return None
        item = self.tree.item(selection[0])
        return self.kraken.get_password(item["values"][0])

    def add_entry(self):
        dialog = AddEditDialog(self.root, self.theme)
        if dialog.result:
            self.kraken.add_password(
                dialog.result["name"],
                dialog.result["username"],
                dialog.result["password"],
                dialog.result["notes"]
            )
            self.refresh_list()

    def edit_entry(self):
        entry = self.get_selected_entry()
        if not entry:
            messagebox.showwarning("Warning", "Please select an entry to edit")
            return

        old_name = entry["name"]
        dialog = AddEditDialog(self.root, self.theme, entry)

        if dialog.result:
            if dialog.result["name"].lower() != old_name.lower():
                self.kraken.delete_password(old_name)

            self.kraken.add_password(
                dialog.result["name"],
                dialog.result["username"],
                dialog.result["password"],
                dialog.result["notes"]
            )
            self.refresh_list()

    def delete_entry(self):
        entry = self.get_selected_entry()
        if not entry:
            messagebox.showwarning("Warning", "Please select an entry to delete")
            return

        if messagebox.askyesno("Confirm", f"Delete '{entry['name']}'?"):
            self.kraken.delete_password(entry["name"])
            self.refresh_list()

    def copy_password(self):
        entry = self.get_selected_entry()
        if not entry:
            messagebox.showwarning("Warning", "Please select an entry")
            return

        self.root.clipboard_clear()
        self.root.clipboard_append(entry["password"])
        self.status_var.set(f"Password for '{entry['name']}' copied to clipboard")

        # Clear clipboard after 30 seconds
        self.root.after(30000, self.clear_clipboard)

    def clear_clipboard(self):
        try:
            self.root.clipboard_clear()
        except tk.TclError:
            pass

    def change_pin(self):
        dialog = PinDialog(self.root, "New PIN", self.theme, confirm=True)
        if dialog.pin:
            if self.kraken.change_pin(dialog.pin):
                messagebox.showinfo("Success", "PIN changed successfully!")
            else:
                messagebox.showerror("Error", "Failed to change PIN")

    def import_passwords(self):
        """Import passwords from CSV (Chrome/Firefox) or JSON file."""
        file_path = filedialog.askopenfilename(
            title="Import Passwords",
            filetypes=[
                ("CSV files (Chrome/Firefox)", "*.csv"),
                ("JSON files", "*.json"),
                ("All files", "*.*")
            ],
            initialdir=str(Path.home() / "Downloads")
        )

        if not file_path:
            return

        try:
            entries = []
            file_ext = Path(file_path).suffix.lower()

            if file_ext == ".csv":
                entries = self._parse_csv_import(file_path)
            elif file_ext == ".json":
                entries = self._parse_json_import(file_path)
            else:
                messagebox.showerror("Error", "Unsupported file format. Use CSV or JSON.")
                return

            if not entries:
                messagebox.showinfo("Import", "No entries found to import.")
                return

            imported = 0
            skipped = 0
            overwrite_all = False
            skip_all = False

            for entry in entries:
                name = entry.get("name", "").strip()
                if not name:
                    skipped += 1
                    continue

                existing = self.kraken.get_password(name)
                if existing:
                    if skip_all:
                        skipped += 1
                        continue
                    if not overwrite_all:
                        result = self._ask_duplicate_action(name)
                        if result == "cancel":
                            break
                        elif result == "skip":
                            skipped += 1
                            continue
                        elif result == "skip_all":
                            skip_all = True
                            skipped += 1
                            continue
                        elif result == "overwrite_all":
                            overwrite_all = True

                self.kraken.add_password(
                    name,
                    entry.get("username", ""),
                    entry.get("password", ""),
                    entry.get("notes", "")
                )
                imported += 1

            self.refresh_list()
            messagebox.showinfo(
                "Import Complete",
                f"Imported: {imported}\nSkipped: {skipped}"
            )

        except Exception as e:
            messagebox.showerror("Error", f"Import failed: {e}")

    def _parse_csv_import(self, file_path: str) -> list:
        """Parse CSV file (Chrome/Firefox format)."""
        entries = []
        with open(file_path, "r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            headers = [h.lower() for h in (reader.fieldnames or [])]

            for row in reader:
                # Normalize keys to lowercase
                row_lower = {k.lower(): v for k, v in row.items()}

                # Chrome format: name, url, username, password
                # Firefox format: url, username, password, httpRealm, formActionOrigin, guid, timeCreated, timeLastUsed, timePasswordChanged
                # 1Password: Title, Url, Username, Password, Notes, OTPAuth
                # LastPass: url, username, password, totp, extra, name, grouping, fav

                # Try to extract name (use URL domain as fallback)
                name = (row_lower.get("name") or
                        row_lower.get("title") or
                        self._extract_domain(row_lower.get("url", "")))

                username = (row_lower.get("username") or
                           row_lower.get("login") or
                           row_lower.get("email") or "")

                password = (row_lower.get("password") or "")

                notes = (row_lower.get("notes") or
                        row_lower.get("extra") or
                        row_lower.get("note") or "")

                # Add URL to notes if present
                url = row_lower.get("url", "")
                if url and url not in notes:
                    notes = f"{url}\n{notes}".strip() if notes else url

                if name and (username or password):
                    entries.append({
                        "name": name,
                        "username": username,
                        "password": password,
                        "notes": notes
                    })

        return entries

    def _extract_domain(self, url: str) -> str:
        """Extract domain name from URL for use as entry name."""
        if not url:
            return ""
        # Remove protocol
        url = url.replace("https://", "").replace("http://", "")
        # Remove path
        url = url.split("/")[0]
        # Remove www.
        url = url.replace("www.", "")
        return url

    def _parse_json_import(self, file_path: str) -> list:
        """Parse JSON file."""
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        if isinstance(data, list):
            return data
        elif isinstance(data, dict) and "entries" in data:
            return data["entries"]
        else:
            return []

    def _ask_duplicate_action(self, name: str) -> str:
        """Ask user how to handle duplicate entry."""
        dialog = tk.Toplevel(self.root)
        dialog.title("Duplicate Entry")
        dialog.transient(self.root)
        dialog.grab_set()
        dialog.resizable(False, False)
        dialog.configure(bg=self.theme.bg)

        result = {"action": "skip"}

        frame = tk.Frame(dialog, bg=self.theme.bg, padx=20, pady=15)
        frame.pack()

        tk.Label(
            frame,
            text=f"'{name}' already exists.",
            bg=self.theme.bg, fg=self.theme.fg,
            font=("Segoe UI", 10)
        ).pack(pady=(0, 15))

        btn_style = {
            "font": ("Segoe UI", 9),
            "bg": self.theme.button_bg,
            "fg": self.theme.button_fg,
            "relief": "flat",
            "cursor": "hand2"
        }

        btn_frame = tk.Frame(frame, bg=self.theme.bg)
        btn_frame.pack()

        def set_result(action):
            result["action"] = action
            dialog.destroy()

        tk.Button(btn_frame, text="Overwrite", command=lambda: set_result("overwrite"), **btn_style).pack(side=tk.LEFT, padx=2, ipadx=6, ipady=3)
        tk.Button(btn_frame, text="Overwrite All", command=lambda: set_result("overwrite_all"), **btn_style).pack(side=tk.LEFT, padx=2, ipadx=6, ipady=3)
        tk.Button(btn_frame, text="Skip", command=lambda: set_result("skip"), **btn_style).pack(side=tk.LEFT, padx=2, ipadx=6, ipady=3)
        tk.Button(btn_frame, text="Skip All", command=lambda: set_result("skip_all"), **btn_style).pack(side=tk.LEFT, padx=2, ipadx=6, ipady=3)
        tk.Button(btn_frame, text="Cancel", command=lambda: set_result("cancel"), **btn_style).pack(side=tk.LEFT, padx=2, ipadx=6, ipady=3)

        # Center on parent
        dialog.update_idletasks()
        x = self.root.winfo_x() + (self.root.winfo_width() - dialog.winfo_width()) // 2
        y = self.root.winfo_y() + (self.root.winfo_height() - dialog.winfo_height()) // 2
        dialog.geometry(f"+{x}+{y}")

        dialog.wait_window()
        return result["action"]

    def export_passwords(self):
        """Export passwords to a JSON file."""
        file_path = filedialog.asksaveasfilename(
            title="Export Passwords",
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
            initialdir=get_script_dir(),
            initialfile="passwords_export.json"
        )

        if not file_path:
            return

        try:
            entries = []
            for entry in self.kraken.get_all():
                entries.append({
                    "name": entry.get("name", ""),
                    "username": entry.get("username", ""),
                    "password": entry.get("password", ""),
                    "notes": entry.get("notes", "")
                })

            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(entries, f, indent=2, ensure_ascii=False)

            messagebox.showinfo("Success", f"Exported {len(entries)} entries to:\n{file_path}")

        except Exception as e:
            messagebox.showerror("Error", f"Export failed: {e}")

    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    app = PasswordKrakenGUI()
    app.run()
