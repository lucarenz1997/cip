import tkinter as tk
from tkinter import messagebox


class UIUtils:
    @staticmethod
    def ask_interactive_mode():
        root = tk.Tk()
        root.withdraw()
        result = messagebox.askquestion("Interactive Mode", "Do you want to scrape in interactive mode?",
                                        icon='warning')
        root.destroy()
        return result

    @staticmethod
    def show_selection_window(objects, title):
        selected_objects = []

        def on_ok():
            nonlocal selected_objects
            selected_indices = listbox.curselection()
            selected_objects = [objects[i] for i in selected_indices]
            root.destroy()

        root = tk.Tk()
        root.title(title)
        window_height = int(root.winfo_screenheight() * 0.4)
        root.geometry(f"400x{window_height}")

        frame = tk.Frame(root)
        frame.pack(fill=tk.BOTH, expand=True)

        scrollbar = tk.Scrollbar(frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        listbox = tk.Listbox(frame, selectmode=tk.MULTIPLE, height=window_height // 20, yscrollcommand=scrollbar.set)
        for obj in objects:
            listbox.insert(tk.END, f"{obj.name} ({obj.article_count})" if hasattr(obj, 'article_count') else obj.name)
        listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        scrollbar.config(command=listbox.yview)

        ok_button = tk.Button(root, text="OK", command=on_ok)
        ok_button.pack(pady=10)

        root.mainloop()
        return selected_objects
