"""
Tkinter Desktop Application for Fabric/Power BI Downloader
Standalone desktop app using Fabric CLI

Run with: python tkinter_app.py

Features:
    - Native desktop UI
    - Download semantic models and reports
    - Browse workspaces and items
    - Save files to local disk
    - Can be packaged as .exe with PyInstaller
    - No PowerShell dependencies
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import sys
from pathlib import Path
import logging
import threading
import traceback

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from src.services.fabric_cli_wrapper import FabricCLIWrapper, FabricItem


class FabricDownloaderGUI:
    """Tkinter-based desktop application for Fabric downloads"""
    
    def __init__(self):
        """Initialize the GUI application"""
        self.root = tk.Tk()
        self.root.title("Fabric/Power BI Downloader")
        self.root.geometry("1000x700")
        
        # Configure logging
        self.setup_logging()
        
        # Client state
        self.client = None
        self.authenticated = False
        self.workspaces = []
        self.current_items = []
        
        # Build UI
        self.create_menu()
        self.create_widgets()
        
        # Center window
        self.center_window()
    
    def setup_logging(self):
        """Configure logging to GUI text widget"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s [%(levelname)s] %(message)s',
            datefmt='%H:%M:%S'
        )
        self.logger = logging.getLogger(__name__)
    
    def center_window(self):
        """Center the window on screen"""
        self.root.update_idletasks()
        width = self.root.winfo_width()
        height = self.root.winfo_height()
        x = (self.root.winfo_screenwidth() // 2) - (width // 2)
        y = (self.root.winfo_screenheight() // 2) - (height // 2)
        self.root.geometry(f'{width}x{height}+{x}+{y}')
    
    def create_menu(self):
        """Create application menu bar"""
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)
        
        # File menu
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="Exit", command=self.root.quit)
        
        # Help menu
        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Help", menu=help_menu)
        help_menu.add_command(label="About", command=self.show_about)
    
    def create_widgets(self):
        """Create main UI widgets"""
        
        # Main container with padding
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(3, weight=1)
        
        # Authentication section
        auth_frame = ttk.LabelFrame(main_frame, text="Authentication", padding="10")
        auth_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        auth_frame.columnconfigure(1, weight=1)
        
        # Auth method selection
        ttk.Label(auth_frame, text="Method:").grid(row=0, column=0, sticky=tk.W, padx=(0, 5))
        self.auth_method = tk.StringVar(value="interactive")
        ttk.Radiobutton(auth_frame, text="Interactive Browser", 
                       variable=self.auth_method, value="interactive").grid(row=0, column=1, sticky=tk.W)
        ttk.Radiobutton(auth_frame, text="Service Principal", 
                       variable=self.auth_method, value="service_principal").grid(row=0, column=2, sticky=tk.W)
        
        # Service principal fields (hidden by default)
        self.sp_frame = ttk.Frame(auth_frame)
        self.sp_frame.grid(row=1, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(5, 0))
        self.sp_frame.columnconfigure(1, weight=1)
        
        ttk.Label(self.sp_frame, text="Tenant ID:").grid(row=0, column=0, sticky=tk.W, padx=(0, 5))
        self.tenant_id_entry = ttk.Entry(self.sp_frame, show="*")
        self.tenant_id_entry.grid(row=0, column=1, sticky=(tk.W, tk.E), pady=2)
        
        ttk.Label(self.sp_frame, text="Client ID:").grid(row=1, column=0, sticky=tk.W, padx=(0, 5))
        self.client_id_entry = ttk.Entry(self.sp_frame, show="*")
        self.client_id_entry.grid(row=1, column=1, sticky=(tk.W, tk.E), pady=2)
        
        ttk.Label(self.sp_frame, text="Client Secret:").grid(row=2, column=0, sticky=tk.W, padx=(0, 5))
        self.client_secret_entry = ttk.Entry(self.sp_frame, show="*")
        self.client_secret_entry.grid(row=2, column=1, sticky=(tk.W, tk.E), pady=2)
        
        # Login button
        self.login_btn = ttk.Button(auth_frame, text="🔑 Login", command=self.login)
        self.login_btn.grid(row=2, column=0, columnspan=3, pady=(10, 0))
        
        self.auth_status_label = ttk.Label(auth_frame, text="Not authenticated", foreground="red")
        self.auth_status_label.grid(row=3, column=0, columnspan=3, pady=(5, 0))
        
        # Workspace section
        workspace_frame = ttk.LabelFrame(main_frame, text="Workspaces", padding="10")
        workspace_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        workspace_frame.columnconfigure(0, weight=1)
        
        # Workspace controls
        ws_controls = ttk.Frame(workspace_frame)
        ws_controls.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 5))
        
        ttk.Button(ws_controls, text="🔄 Refresh Workspaces", 
                  command=self.load_workspaces).pack(side=tk.LEFT, padx=(0, 5))
        
        ttk.Label(ws_controls, text="Select Workspace:").pack(side=tk.LEFT, padx=(10, 5))
        self.workspace_combo = ttk.Combobox(ws_controls, state="readonly", width=50)
        self.workspace_combo.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.workspace_combo.bind('<<ComboboxSelected>>', self.on_workspace_selected)
        
        # Items section
        items_frame = ttk.LabelFrame(main_frame, text="Workspace Items", padding="10")
        items_frame.grid(row=2, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        items_frame.columnconfigure(0, weight=1)
        
        # Items controls
        items_controls = ttk.Frame(items_frame)
        items_controls.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 5))
        
        ttk.Button(items_controls, text="📋 Load Items", 
                  command=self.load_workspace_items).pack(side=tk.LEFT, padx=(0, 5))
        
        ttk.Label(items_controls, text="Filter by:").pack(side=tk.LEFT, padx=(10, 5))
        self.item_type_filter = ttk.Combobox(items_controls, 
                                            values=["All", "SemanticModel", "Report", "Dashboard"],
                                            state="readonly", width=15)
        self.item_type_filter.set("All")
        self.item_type_filter.pack(side=tk.LEFT)
        self.item_type_filter.bind('<<ComboboxSelected>>', self.apply_item_filter)
        
        # Items tree view
        items_tree_frame = ttk.Frame(items_frame)
        items_tree_frame.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        items_frame.rowconfigure(1, weight=1)
        
        self.items_tree = ttk.Treeview(items_tree_frame, 
                                       columns=("Name", "Type", "ID"),
                                       show="headings", height=8)
        self.items_tree.heading("Name", text="Name")
        self.items_tree.heading("Type", text="Type")
        self.items_tree.heading("ID", text="ID")
        self.items_tree.column("Name", width=300)
        self.items_tree.column("Type", width=150)
        self.items_tree.column("ID", width=300)
        
        # Scrollbar for tree
        items_scrollbar = ttk.Scrollbar(items_tree_frame, orient=tk.VERTICAL, 
                                       command=self.items_tree.yview)
        self.items_tree.configure(yscrollcommand=items_scrollbar.set)
        
        self.items_tree.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        items_scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        items_tree_frame.columnconfigure(0, weight=1)
        items_tree_frame.rowconfigure(0, weight=1)
        
        # Download controls
        download_controls = ttk.Frame(items_frame)
        download_controls.grid(row=2, column=0, sticky=(tk.W, tk.E), pady=(5, 0))
        
        ttk.Label(download_controls, text="Format:").pack(side=tk.LEFT, padx=(0, 5))
        self.download_format = ttk.Combobox(download_controls, 
                                           values=["TMDL", "PBIP"],
                                           state="readonly", width=10)
        self.download_format.set("TMDL")
        self.download_format.pack(side=tk.LEFT, padx=(0, 10))
        
        ttk.Button(download_controls, text="⬇️ Download Selected", 
                  command=self.download_selected_item).pack(side=tk.LEFT)
        
        # Log section
        log_frame = ttk.LabelFrame(main_frame, text="Activity Log", padding="10")
        log_frame.grid(row=3, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)
        
        self.log_text = scrolledtext.ScrolledText(log_frame, height=10, state='disabled')
        self.log_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
    
    def log(self, message, level="INFO"):
        """Add message to log widget"""
        self.log_text.configure(state='normal')
        self.log_text.insert(tk.END, f"[{level}] {message}\n")
        self.log_text.see(tk.END)
        self.log_text.configure(state='disabled')
        self.logger.info(message)
    
    def login(self):
        """Authenticate to Microsoft Fabric"""
        self.log("Authenticating to Microsoft Fabric...")
        
        def auth_thread():
            try:
                method = self.auth_method.get()
                
                if method == "interactive":
                    self.client = FabricCLIWrapper()
                    self.client.login(interactive=True)
                else:
                    tenant_id = self.tenant_id_entry.get()
                    client_id = self.client_id_entry.get()
                    client_secret = self.client_secret_entry.get()
                    
                    if not all([tenant_id, client_id, client_secret]):
                        self.root.after(0, lambda: messagebox.showwarning(
                            "Missing Credentials",
                            "Please provide all service principal credentials"
                        ))
                        return
                    
                    self.client = FabricCLIWrapper(
                        tenant_id=tenant_id,
                        client_id=client_id,
                        client_secret=client_secret
                    )
                    self.client.login(interactive=False)
                
                self.authenticated = True
                self.root.after(0, self.on_login_success)
                
            except ImportError as e:
                self.root.after(0, lambda: self.on_login_error(
                    f"{str(e)}\n\nInstall with: pip install ms-fabric-cli"
                ))
            except Exception as e:
                self.root.after(0, lambda: self.on_login_error(str(e)))
        
        # Run in background thread
        thread = threading.Thread(target=auth_thread, daemon=True)
        thread.start()
    
    def on_login_success(self):
        """Handle successful authentication"""
        self.log("✓ Successfully authenticated", "SUCCESS")
        self.auth_status_label.config(text="✓ Authenticated", foreground="green")
        self.login_btn.config(state="disabled")
        messagebox.showinfo("Success", "Successfully authenticated to Microsoft Fabric!")
    
    def on_login_error(self, error_msg):
        """Handle authentication error"""
        self.log(f"✗ Authentication failed: {error_msg}", "ERROR")
        messagebox.showerror("Authentication Failed", error_msg)
    
    def load_workspaces(self):
        """Load list of workspaces"""
        if not self.authenticated:
            messagebox.showwarning("Not Authenticated", "Please login first")
            return
        
        self.log("Loading workspaces...")
        
        def load_thread():
            try:
                self.workspaces = self.client.list_workspaces()
                self.root.after(0, self.on_workspaces_loaded)
            except Exception as e:
                self.root.after(0, lambda: self.on_load_error(f"Failed to load workspaces: {str(e)}"))
        
        thread = threading.Thread(target=load_thread, daemon=True)
        thread.start()
    
    def on_workspaces_loaded(self):
        """Handle workspaces loaded"""
        workspace_names = [
            f"{ws.get('displayName', ws.get('name', 'Unnamed'))} ({ws['id']})"
            for ws in self.workspaces
        ]
        self.workspace_combo['values'] = workspace_names
        self.log(f"✓ Loaded {len(self.workspaces)} workspaces", "SUCCESS")
    
    def on_workspace_selected(self, event):
        """Handle workspace selection"""
        self.log(f"Selected workspace: {self.workspace_combo.get()}")
    
    def load_workspace_items(self):
        """Load items from selected workspace"""
        if not self.workspace_combo.get():
            messagebox.showwarning("No Workspace", "Please select a workspace first")
            return
        
        # Extract workspace ID from combo box selection
        selected = self.workspace_combo.get()
        workspace_id = selected.split('(')[-1].rstrip(')')
        
        self.log(f"Loading items from workspace {workspace_id}...")
        
        def load_thread():
            try:
                self.current_items = self.client.list_workspace_items(workspace_id)
                self.root.after(0, self.on_items_loaded)
            except Exception as e:
                self.root.after(0, lambda: self.on_load_error(f"Failed to load items: {str(e)}"))
        
        thread = threading.Thread(target=load_thread, daemon=True)
        thread.start()
    
    def on_items_loaded(self):
        """Handle items loaded"""
        self.apply_item_filter()
        self.log(f"✓ Loaded {len(self.current_items)} items", "SUCCESS")
    
    def apply_item_filter(self, event=None):
        """Filter items by type"""
        # Clear tree
        for item in self.items_tree.get_children():
            self.items_tree.delete(item)
        
        # Apply filter
        filter_type = self.item_type_filter.get()
        filtered_items = self.current_items if filter_type == "All" else [
            item for item in self.current_items if item.type == filter_type
        ]
        
        # Populate tree
        for item in filtered_items:
            self.items_tree.insert("", tk.END, values=(item.name, item.type, item.id))
    
    def download_selected_item(self):
        """Download the selected item"""
        selection = self.items_tree.selection()
        if not selection:
            messagebox.showwarning("No Selection", "Please select an item to download")
            return
        
        # Get selected item details
        item_values = self.items_tree.item(selection[0])['values']
        item_name, item_type, item_id = item_values
        
        # Find the full item object
        item = next((i for i in self.current_items if i.id == item_id), None)
        if not item:
            messagebox.showerror("Error", "Could not find selected item")
            return
        
        # Ask for save location
        default_ext = self.download_format.get().lower()
        filename = filedialog.asksaveasfilename(
            title="Save As",
            initialfile=f"{item_name}.{default_ext}",
            defaultextension=f".{default_ext}",
            filetypes=[
                (f"{default_ext.upper()} files", f"*.{default_ext}"),
                ("All files", "*.*")
            ]
        )
        
        if not filename:
            return  # User cancelled
        
        self.log(f"Downloading {item_name}...")
        
        def download_thread():
            try:
                result_path = self.client.download_item(
                    workspace_id=item.workspace_id,
                    item_id=item.id,
                    item_type=item.type,
                    local_path=filename,
                    format=self.download_format.get()
                )
                self.root.after(0, lambda: self.on_download_success(result_path))
            except Exception as e:
                self.root.after(0, lambda: self.on_download_error(str(e)))
        
        thread = threading.Thread(target=download_thread, daemon=True)
        thread.start()
    
    def on_download_success(self, path):
        """Handle successful download"""
        self.log(f"✓ Downloaded to {path}", "SUCCESS")
        messagebox.showinfo("Download Complete", f"Successfully downloaded to:\n{path}")
    
    def on_download_error(self, error_msg):
        """Handle download error"""
        self.log(f"✗ Download failed: {error_msg}", "ERROR")
        messagebox.showerror("Download Failed", error_msg)
    
    def on_load_error(self, error_msg):
        """Handle generic load error"""
        self.log(f"✗ {error_msg}", "ERROR")
        messagebox.showerror("Error", error_msg)
    
    def show_about(self):
        """Show about dialog"""
        messagebox.showinfo(
            "About",
            "Fabric/Power BI Downloader\n\n"
            "Desktop application for downloading items from\n"
            "Microsoft Fabric and Power BI workspaces.\n\n"
            "Uses ms-fabric-cli Python package.\n"
            "No PowerShell dependencies.\n\n"
            "Build with PyInstaller:\n"
            "pyinstaller --onefile --windowed tkinter_app.py"
        )
    
    def run(self):
        """Start the application"""
        self.log("Application started")
        self.root.mainloop()


if __name__ == "__main__":
    app = FabricDownloaderGUI()
    app.run()
