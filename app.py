import tkinter as tk
from tkinter import scrolledtext
import datetime

class MessengerApp:
    """
    Простой мессенджер на tkinter без серверной части.
    Позволяет отправлять сообщения от имени 'Вы' и 'Собеседник'.
    """

    def __init__(self, root):
        self.root = root
        self.root.title("Мессенджер")
        self.root.geometry("500x400")

        # --- Область отображения сообщений (только для чтения) ---
        self.messages_area = scrolledtext.ScrolledText(
            root,
            state='normal',      # временно разрешаем вставку
            height=15,
            wrap=tk.WORD
        )
        self.messages_area.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)
        self.messages_area.config(state='disabled')  # запрещаем редактирование

        # --- Поле ввода нового сообщения ---
        self.entry = tk.Entry(root, width=40)
        self.entry.pack(side=tk.LEFT, padx=(10, 0), pady=10, fill=tk.X, expand=True)

        # --- Кнопки управления ---
        self.send_btn = tk.Button(root, text="Отправить", command=self.on_send)
        self.send_btn.pack(side=tk.LEFT, padx=5, pady=10)

        self.reply_btn = tk.Button(root, text="Ответить", command=self.on_reply)
        self.reply_btn.pack(side=tk.LEFT, padx=5, pady=10)

        self.clear_btn = tk.Button(root, text="Очистить", command=self.clear_chat)
        self.clear_btn.pack(side=tk.LEFT, padx=5, pady=10)

        # --- Привязка клавиши Enter к отправке ---
        self.entry.bind('<Return>', lambda event: self.on_send())

    def add_message(self, sender: str, text: str) -> None:
        """
        Добавляет сообщение в чат с временной меткой и именем отправителя.
        """
        if not text.strip():
            return  # игнорируем пустые сообщения

        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        message = f"[{timestamp}] {sender}: {text}\n"

        self.messages_area.config(state='normal')
        self.messages_area.insert(tk.END, message)
        self.messages_area.see(tk.END)       # прокрутка вниз
        self.messages_area.config(state='disabled')

    def on_send(self) -> None:
        """Отправляет сообщение от имени 'Вы'."""
        text = self.entry.get()
        self.add_message("Вы", text)
        self.entry.delete(0, tk.END)

    def on_reply(self) -> None:
        """Отправляет сообщение от имени 'Собеседник' (имитация ответа)."""
        text = self.entry.get()
        self.add_message("Собеседник", text)
        self.entry.delete(0, tk.END)

    def clear_chat(self) -> None:
        """Очищает всю историю сообщений."""
        self.messages_area.config(state='normal')
        self.messages_area.delete(1.0, tk.END)
        self.messages_area.config(state='disabled')


if __name__ == "__main__":
    root = tk.Tk()
    app = MessengerApp(root)
    root.mainloop()
