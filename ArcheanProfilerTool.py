import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import csv
import os
import sys

def resource_path(relative_path):
    """Obtenir le chemin absolu vers une ressource, que ce soit en mode script ou exécutable PyInstaller."""
    try:
        # PyInstaller crée un attribut _MEIPASS pour stocker les fichiers temporaires
        base_path = sys._MEIPASS
    except AttributeError:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)

class TreeNode:
    def __init__(self, name):
        self.name = name
        self.data = None  # Data associated with this node
        self.children = {}  # Dictionary of child nodes
        self.tag = None  # Color tag (e.g., 'worst', 'bad')

class ArcheanProfilerTool:
    def __init__(self, root):
        self.root = root
        self.root.geometry("1280x720")
        self.root.title("Archean Profiler Tool")
        
        # Obtenir le chemin absolu vers l'icône
        icon_path = resource_path(os.path.join('img', 'archeanIcon.ico'))
        
        # Vérifier si le fichier existe avant de le définir
        if os.path.exists(icon_path):
            try:
                self.root.iconbitmap(icon_path)
            except Exception as e:
                messagebox.showwarning("Chargement de l'icône échoué", f"Échec du chargement de l'icône : {e}")
        else:
            messagebox.showwarning("Icône manquante", f"Fichier d'icône introuvable à : {icon_path}")
        
        self.create_widgets()
        self.data = []
        self.root_node = TreeNode('Root')
        self.build_menu()
        self.sort_column = 'Avg'  # Tri par défaut sur 'Avg'
        self.sort_reverse = False
        self.filter_text = ''

    def create_widgets(self):
        # Créer un cadre pour contenir le Treeview, la scrollbar et les boutons
        frame = ttk.Frame(self.root)
        frame.pack(fill='both', expand=True)

        # Créer le Treeview
        columns = ('Count', 'TotalTime', 'Min', 'Max', 'Avg')
        self.tree = ttk.Treeview(frame, columns=columns, selectmode="browse")
        self.tree.heading('#0', text='Profile', command=lambda: self.sort_tree('Profile', False))
        for col in columns:
            self.tree.heading(col, text=col, command=lambda c=col: self.sort_tree(c, True))
            self.tree.column(col, width=150, anchor='e')

        # Ajouter la scrollbar
        scrollbar = ttk.Scrollbar(frame, orient='vertical', command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)

        # Placer le Treeview et la scrollbar
        self.tree.grid(row=0, column=0, sticky='nsew')
        scrollbar.grid(row=0, column=1, sticky='ns')

        # Rendre la fenêtre redimensionnable
        frame.rowconfigure(0, weight=1)
        frame.columnconfigure(0, weight=1)

        # Taille du texte
        style = ttk.Style()
        style.configure('Treeview', font=('Helvetica', 12))
        style.configure('Treeview.Heading', font=('Helvetica', 12))

        # Créer les boutons "Expand All" et "Collapse All"
        button_frame = ttk.Frame(self.root)
        button_frame.pack(fill='x', padx=10, pady=10)

        expand_all_btn = ttk.Button(button_frame, text="Expand All", command=self.expand_all)
        expand_all_btn.pack(side='left', padx=5)

        collapse_all_btn = ttk.Button(button_frame, text="Collapse All", command=self.collapse_all)
        collapse_all_btn.pack(side='left', padx=5)

        # Ajouter une barre de recherche
        search_label = ttk.Label(button_frame, text="Search:")
        search_label.pack(side='left', padx=(20, 5))
        self.search_var = tk.StringVar()
        search_entry = ttk.Entry(button_frame, textvariable=self.search_var)
        search_entry.pack(side='left', padx=5)
        self.search_var.trace('w', self.update_filter)

    def build_menu(self):
        menubar = tk.Menu(self.root)
        # Menu Fichier
        filemenu = tk.Menu(menubar, tearoff=0)
        filemenu.add_command(label="Open", command=self.open_file)
        filemenu.add_separator()
        filemenu.add_command(label="Exit", command=self.root.quit)
        menubar.add_cascade(label="File", menu=filemenu)
        # Menu Aide
        helpmenu = tk.Menu(menubar, tearoff=0)
        helpmenu.add_command(label="Color System Help", command=self.show_help)
        menubar.add_cascade(label="Help", menu=helpmenu)
        self.root.config(menu=menubar)

    def show_help(self):
        help_text = (
            "Color System Explanation:\n\n"
            "- For each parent node, the children are analyzed based on their 'Avg' values.\n"
            "- The top 3 highest 'Avg' values among the direct children are highlighted in light red.\n"
            "- The next 3 highest 'Avg' values are highlighted in light orange.\n"
            "- This color system helps you quickly identify performance bottlenecks at each hierarchy level."
        )
        messagebox.showinfo("Color System Help", help_text)

    def open_file(self):
        file_path = filedialog.askopenfilename()
        if file_path:
            self.data = self.parse_csv(file_path)
            self.build_tree()
            self.sort_tree(self.sort_column or 'Profile', numeric=True)

    def parse_csv(self, file_path):
        data = []
        with open(file_path, 'r', newline='', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                # Build hierarchy based on 'Profile' field
                hierarchy = row['Profile'].split('->')
                # Convert numeric fields to floats
                for key in ['Count', 'TotalTime', 'Min', 'Max', 'Avg']:
                    try:
                        row[key] = float(row[key])
                    except ValueError:
                        row[key] = 0.0
                # Store the hierarchy and the row data
                data.append({'hierarchy': hierarchy, 'data': row})
        return data

    def build_tree(self):
        # Build the tree structure from self.data
        self.root_node = TreeNode('Root')
        for entry in self.data:
            hierarchy = entry['hierarchy']
            data = entry['data']
            current_node = self.root_node
            for idx, level in enumerate(hierarchy):
                if level not in current_node.children:
                    current_node.children[level] = TreeNode(level)
                current_node = current_node.children[level]
                if idx == len(hierarchy) - 1:
                    # This is a leaf node
                    current_node.data = data
        # After building the tree, color the nodes
        self.color_rows()

    def populate_treeview(self):
        # Clear the existing tree
        self.tree.delete(*self.tree.get_children())

        # Recursively insert nodes into the treeview
        def insert_nodes(parent_item, node):
            matches_filter = self.filter_text.lower() in node.name.lower()
            # Collect matching children
            child_items = []
            for child_name in node.children:
                child_node = node.children[child_name]
                child_item_id = insert_nodes(None, child_node)
                if child_item_id:
                    child_items.append((child_node, child_item_id))
            if matches_filter or child_items:
                # Use empty string '' if parent_item is None
                parent = parent_item if parent_item else ''
                if node == self.root_node:
                    # Do not insert the root node itself
                    item_id = None
                else:
                    item_id = self.tree.insert(parent, 'end', text=node.name)
                    if node.tag:
                        self.tree.item(item_id, tags=(node.tag,))
                    if node.data:
                        self.set_item_values(item_id, node.data)
                # Now reparent matching children under this node
                for child_node, child_item_id in child_items:
                    if item_id:
                        self.tree.move(child_item_id, item_id, 'end')
                    else:
                        # If current node is root_node, we keep children at root level
                        pass
                return item_id if item_id else parent_item
            else:
                return None

        # Start inserting from children of root_node
        for child_name in self.root_node.children:
            child_node = self.root_node.children[child_name]
            insert_nodes('', child_node)

        # Configure the tags for coloring
        self.tree.tag_configure('worst', background='lightcoral')
        self.tree.tag_configure('bad', background='lightsalmon')  # Correction du nom de couleur

    def set_item_values(self, item_id, data):
        # Format numeric values
        formatted_data = {}
        for k in ['TotalTime', 'Min', 'Max', 'Avg']:
            formatted_data[k] = "{:,.6f} ms".format(data[k]).replace(",", "'")
        # Insert values into columns
        self.tree.set(item_id, 'Count', int(data['Count']))
        self.tree.set(item_id, 'TotalTime', formatted_data['TotalTime'])
        self.tree.set(item_id, 'Min', formatted_data['Min'])
        self.tree.set(item_id, 'Max', formatted_data['Max'])
        self.tree.set(item_id, 'Avg', formatted_data['Avg'])

    def color_rows(self):
        # Apply coloring based on performance levels
        def color_node(node):
            # Get direct children with data
            children = []
            for child_name in node.children:
                child_node = node.children[child_name]
                if child_node.data:
                    avg = child_node.data['Avg']
                    children.append((child_node, avg))
                # Recursively call for children
                color_node(child_node)
            # Sort children by 'Avg' in descending order
            children.sort(key=lambda x: x[1], reverse=True)
            # Assign tags based on unfiltered data
            for i, (child_node, _) in enumerate(children):
                if i < 3:
                    child_node.tag = 'worst'
                elif i < 6:
                    child_node.tag = 'bad'
                else:
                    child_node.tag = child_node.tag or None

        # Apply coloring from the root
        color_node(self.root_node)

    def sort_tree(self, col, numeric):
        if col is None:
            return
        self.sort_column = col
        reverse = False
        if hasattr(self, 'sort_reverse') and self.sort_column == col:
            reverse = not self.sort_reverse
        else:
            reverse = False
        self.sort_reverse = reverse

        # Recursively sort the tree
        def sort_node(node):
            if node.children:
                # Sort children
                children = list(node.children.values())
                if numeric:
                    # For numeric sorting, get the value or 0 if no data
                    children.sort(
                        key=lambda x: x.data[col] if x.data and col in x.data else 0,
                        reverse=reverse)
                else:
                    children.sort(key=lambda x: x.name, reverse=reverse)
                # Rebuild the children dictionary
                node.children = {child.name: child for child in children}
                # Recursively sort their children
                for child in node.children.values():
                    sort_node(child)
        sort_node(self.root_node)
        # Rebuild the treeview
        self.populate_treeview()

    def expand_all(self):
        # Recursively expand all nodes
        def expand_node(item):
            self.tree.item(item, open=True)
            children = self.tree.get_children(item)
            for child in children:
                expand_node(child)

        for item in self.tree.get_children():
            expand_node(item)

    def collapse_all(self):
        # Recursively collapse all nodes
        def collapse_node(item):
            self.tree.item(item, open=False)
            children = self.tree.get_children(item)
            for child in children:
                collapse_node(child)

        for item in self.tree.get_children():
            collapse_node(item)

    def update_filter(self, *args):
        self.filter_text = self.search_var.get()
        self.populate_treeview()
        self.expand_all()  # Automatically expand all nodes on search

def main():
    root = tk.Tk()
    app = ArcheanProfilerTool(root)
    root.mainloop()

if __name__ == '__main__':
    main()
