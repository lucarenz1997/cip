import tkinter as tk
from tkinter import messagebox, ttk


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

    @staticmethod
    def show_selection_window_dropdown(objects, title):
        selected_categories = []
        category_map = {}  # Dictionary to store mapping of TreeView item IDs to Category objects

        # Function to handle item clicks (simulates checkbox-like behavior)
        def toggle_selection(event):
            item_id = tree.focus()
            if item_id in selected_items:
                selected_items.remove(item_id)
                tree.item(item_id, tags=('deselected',))
            else:
                selected_items.add(item_id)
                tree.item(item_id, tags=('selected',))

        def on_ok():
            nonlocal selected_categories
            for item_id in selected_items:
                category_object = category_map[item_id]  # Retrieve the Category object from the map
                selected_categories.append(category_object)
            root.destroy()

        root = tk.Tk()  # Initialize the Tkinter window
        root.title(title)
        window_height = int(root.winfo_screenheight() * 0.4)
        root.geometry(f"400x{window_height}")

        frame = tk.Frame(root)
        frame.pack(fill=tk.BOTH, expand=True)

        # Create a Treeview widget with no selection mode so we handle clicks manually
        tree = ttk.Treeview(frame, selectmode="none")
        tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Add a scrollbar to the Treeview
        scrollbar = tk.Scrollbar(frame, orient="vertical", command=tree.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        tree.config(yscrollcommand=scrollbar.set)

        # Style to simulate selection (toggle background colors)
        tree.tag_configure('selected', background='lightblue')
        tree.tag_configure('deselected', background='white')

        selected_items = set()  # Keep track of selected items

        # Insert categories and subcategories into the tree, storing only the name,
        # but using the dictionary to keep a reference to the actual object
        for category in objects:
            parent_id = tree.insert("", "end", text=category.name, tags=('deselected',))
            category_map[parent_id] = category  # Map the TreeView item ID to the Category object

            if category.subcategory:
                for subcat in category.subcategory:
                    subcat_id = tree.insert(parent_id, "end", text=subcat.name, tags=('deselected',))
                    category_map[subcat_id] = subcat  # Map the subcategory ID to the Subcategory object

        # Bind the click event to the TreeView for toggling selection
        tree.bind("<ButtonRelease-1>", toggle_selection)

        # Add an "OK" button to confirm selection
        ok_button = tk.Button(root, text="OK", command=on_ok)
        ok_button.pack(pady=10)

        # Make sure to start the Tkinter event loop
        root.mainloop()

        # Return the list of selected Category (or Subcategory) objects
        return selected_categories



