"""
Streamlit Web App for Fabric/Power BI Downloader
Pure Python web application using Fabric CLI

Run with: streamlit run streamlit_app.py

Features:
    - Web-based UI for Fabric workspace browsing
    - Download semantic models and reports
    - Interactive authentication
    - File download to browser
    - No PowerShell dependencies
"""

import streamlit as st
import sys
from pathlib import Path
import logging
import traceback

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.services.fabric_cli_wrapper import FabricCLIWrapper, FabricItem

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Page configuration
st.set_page_config(
    page_title="Fabric/Power BI Downloader",
    page_icon="📊",
    layout="wide"
)

# Custom CSS
st.markdown("""
    <style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #0078D4;
        margin-bottom: 1rem;
    }
    .success-box {
        padding: 1rem;
        border-radius: 0.5rem;
        background-color: #D4EDDA;
        border: 1px solid #C3E6CB;
        color: #155724;
        margin: 1rem 0;
    }
    .info-box {
        padding: 1rem;
        border-radius: 0.5rem;
        background-color: #D1ECF1;
        border: 1px solid #BEE5EB;
        color: #0C5460;
        margin: 1rem 0;
    }
    </style>
""", unsafe_allow_html=True)


def initialize_client():
    """Initialize and authenticate Fabric CLI client"""
    if 'client' not in st.session_state or st.session_state.client is None:
        with st.spinner("Initializing Fabric CLI client..."):
            try:
                # Check if service principal credentials are in session state
                use_sp = st.session_state.get('use_service_principal', False)
                
                if use_sp:
                    client = FabricCLIWrapper(
                        tenant_id=st.session_state.get('tenant_id'),
                        client_id=st.session_state.get('client_id'),
                        client_secret=st.session_state.get('client_secret')
                    )
                    client.login(interactive=False)
                else:
                    client = FabricCLIWrapper()
                    client.login(interactive=True)
                
                st.session_state.client = client
                st.session_state.authenticated = True
                return True
                
            except ImportError as e:
                st.error(f"❌ {str(e)}")
                st.info("Install with: `pip install ms-fabric-cli`")
                return False
            except Exception as e:
                st.error(f"❌ Authentication failed: {str(e)}")
                logger.error(f"Auth error: {traceback.format_exc()}")
                return False
    return True


def authentication_sidebar():
    """Sidebar for authentication options"""
    with st.sidebar:
        st.header("🔐 Authentication")
        
        auth_method = st.radio(
            "Select authentication method:",
            ["Interactive Browser", "Service Principal"],
            key="auth_method"
        )
        
        if auth_method == "Service Principal":
            st.session_state.use_service_principal = True
            st.session_state.tenant_id = st.text_input(
                "Tenant ID",
                type="password",
                help="Azure AD Tenant ID"
            )
            st.session_state.client_id = st.text_input(
                "Client ID",
                type="password",
                help="Service Principal Client ID"
            )
            st.session_state.client_secret = st.text_input(
                "Client Secret",
                type="password",
                help="Service Principal Secret"
            )
        else:
            st.session_state.use_service_principal = False
        
        st.divider()
        
        if st.session_state.get('authenticated', False):
            st.success("✓ Authenticated")
            if st.button("🔄 Logout"):
                st.session_state.client = None
                st.session_state.authenticated = False
                st.rerun()
        else:
            if st.button("🔑 Login", type="primary"):
                initialize_client()
                st.rerun()


def main():
    """Main application"""
    
    # Header
    st.markdown('<div class="main-header">📊 Fabric/Power BI Downloader</div>', unsafe_allow_html=True)
    st.markdown("Download semantic models and reports from Microsoft Fabric workspaces")
    
    # Authentication sidebar
    authentication_sidebar()
    
    # Check authentication
    if not st.session_state.get('authenticated', False):
        st.markdown("""
        <div class="info-box">
            <h3>👋 Welcome!</h3>
            <p>Please authenticate using the sidebar to get started.</p>
            <ul>
                <li><strong>Interactive Browser:</strong> Opens browser for user authentication</li>
                <li><strong>Service Principal:</strong> Use Azure AD app credentials</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)
        return
    
    # Ensure client is initialized
    if not initialize_client():
        return
    
    client = st.session_state.client
    
    # Main interface tabs
    tab1, tab2, tab3 = st.tabs(["📁 Workspaces", "📥 Download Items", "📚 About"])
    
    with tab1:
        st.header("Workspaces")
        
        if st.button("🔄 Refresh Workspaces", key="refresh_workspaces"):
            with st.spinner("Loading workspaces..."):
                try:
                    workspaces = client.list_workspaces()
                    st.session_state.workspaces = workspaces
                except Exception as e:
                    st.error(f"Failed to load workspaces: {str(e)}")
        
        if 'workspaces' in st.session_state:
            workspaces = st.session_state.workspaces
            st.info(f"Found {len(workspaces)} workspaces")
            
            # Display workspaces in a table
            if workspaces:
                for ws in workspaces:
                    with st.expander(f"🗂️ {ws.get('displayName', ws.get('name', 'Unnamed'))}"):
                        st.write(f"**ID:** `{ws['id']}`")
                        if 'description' in ws and ws['description']:
                            st.write(f"**Description:** {ws['description']}")
                        
                        # Button to load items from this workspace
                        if st.button(f"View Items", key=f"load_{ws['id']}"):
                            st.session_state.selected_workspace_id = ws['id']
                            st.session_state.selected_workspace_name = ws.get('displayName', ws.get('name'))
    
    with tab2:
        st.header("Download Items")
        
        # Workspace selection
        col1, col2 = st.columns([2, 1])
        
        with col1:
            workspace_id = st.text_input(
                "Workspace ID",
                value=st.session_state.get('selected_workspace_id', ''),
                help="Enter the Fabric workspace ID"
            )
        
        with col2:
            if st.button("📋 List Items", type="primary"):
                if workspace_id:
                    with st.spinner("Loading items..."):
                        try:
                            items = client.list_workspace_items(workspace_id)
                            st.session_state.workspace_items = items
                            st.session_state.current_workspace_id = workspace_id
                        except Exception as e:
                            st.error(f"Failed to load items: {str(e)}")
                else:
                    st.warning("Please enter a workspace ID")
        
        # Display items if loaded
        if 'workspace_items' in st.session_state:
            items = st.session_state.workspace_items
            
            if items:
                st.success(f"Found {len(items)} items")
                
                # Filter by type
                item_types = list(set(item.type for item in items))
                selected_type = st.selectbox("Filter by type:", ["All"] + item_types)
                
                filtered_items = items if selected_type == "All" else [
                    item for item in items if item.type == selected_type
                ]
                
                # Display items
                for item in filtered_items:
                    with st.expander(f"{item.type}: {item.name}"):
                        st.write(f"**ID:** `{item.id}`")
                        st.write(f"**Type:** {item.type}")
                        if item.description:
                            st.write(f"**Description:** {item.description}")
                        
                        # Download section
                        col_a, col_b, col_c = st.columns([2, 1, 1])
                        
                        with col_a:
                            download_format = st.selectbox(
                                "Format",
                                ["TMDL", "PBIP"] if item.type == "SemanticModel" else ["PBIP"],
                                key=f"format_{item.id}"
                            )
                        
                        with col_b:
                            local_filename = st.text_input(
                                "Filename",
                                value=f"{item.name}.{download_format.lower()}",
                                key=f"filename_{item.id}"
                            )
                        
                        with col_c:
                            if st.button("⬇️ Download", key=f"download_{item.id}"):
                                download_path = Path("./downloads") / local_filename
                                download_path.parent.mkdir(parents=True, exist_ok=True)
                                
                                with st.spinner(f"Downloading {item.name}..."):
                                    try:
                                        result_path = client.download_item(
                                            workspace_id=item.workspace_id,
                                            item_id=item.id,
                                            item_type=item.type,
                                            local_path=str(download_path),
                                            format=download_format
                                        )
                                        
                                        st.success(f"✓ Downloaded to {result_path}")
                                        
                                        # Offer file download to browser if it's a file
                                        if result_path.is_file():
                                            with open(result_path, "rb") as f:
                                                st.download_button(
                                                    label="💾 Download to Browser",
                                                    data=f.read(),
                                                    file_name=local_filename,
                                                    mime="application/octet-stream",
                                                    key=f"browser_download_{item.id}"
                                                )
                                    except Exception as e:
                                        st.error(f"Download failed: {str(e)}")
                                        logger.error(traceback.format_exc())
            else:
                st.info("No items found in this workspace")
    
    with tab3:
        st.header("About")
        st.markdown("""
        ### Fabric/Power BI Downloader Web App
        
        This application uses the **Microsoft Fabric CLI Python API** to provide:
        
        - 🌐 **Web-based interface** - No desktop software required
        - 🔒 **Secure authentication** - Interactive or service principal
        - 📥 **Direct downloads** - Semantic models and reports in PBIP/TMDL format
        - 🚀 **Pure Python** - No PowerShell dependencies
        - 🎯 **Cross-platform** - Works on Windows, Linux, Mac
        
        #### Requirements
        ```
        pip install streamlit ms-fabric-cli
        ```
        
        #### Run
        ```bash
        streamlit run streamlit_app.py
        ```
        
        #### Features
        - Browse all accessible Fabric workspaces
        - List items in each workspace
        - Download semantic models (TMDL or PBIP format)
        - Download Power BI reports (PBIP format)
        - Direct download to browser
        
        #### Authentication Methods
        
        **Interactive Browser:**
        - Opens browser for user authentication
        - Best for personal use
        - Requires user interaction
        
        **Service Principal:**
        - Uses Azure AD app credentials
        - Best for automation
        - Requires tenant admin setup
        
        ---
        
        **Documentation:** See `FABRIC_CLI_INTEGRATION.md` for more details
        """)


if __name__ == "__main__":
    main()
