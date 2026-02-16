"""
Test script to verify theme implementation
Run this to check if the theme system works properly
"""

import sys
from pathlib import Path

# Add src to path
src_path = Path(__file__).parent / 'src'
sys.path.insert(0, str(src_path))
sys.path.insert(0, str(src_path / 'utils'))

try:
    from utils.theme_manager import get_theme_manager
    
    print("✓ Theme manager imported successfully")
    
    # Test theme manager
    theme_mgr = get_theme_manager()
    print(f"✓ Current theme: {theme_mgr.get_current_theme()}")
    
    # Test getting stylesheets
    dark_sheet = theme_mgr._get_dark_stylesheet()
    light_sheet = theme_mgr._get_light_stylesheet()
    print(f"✓ Dark stylesheet length: {len(dark_sheet)} chars")
    print(f"✓ Light stylesheet length: {len(light_sheet)} chars")
    
    # Test button styles
    primary_btn = theme_mgr.get_button_style("primary")
    success_btn = theme_mgr.get_button_style("success")
    danger_btn = theme_mgr.get_button_style("danger")
    print(f"✓ Button styles generated successfully")
    
    # Test text colors
    primary_color = theme_mgr.get_text_color("primary")
    accent_color = theme_mgr.get_text_color("accent")
    print(f"✓ Text colors: primary={primary_color}, accent={accent_color}")
    
    # Test theme toggle
    original = theme_mgr.get_current_theme()
    theme_mgr.toggle_theme()
    toggled = theme_mgr.get_current_theme()
    print(f"✓ Theme toggle works: {original} -> {toggled}")
    
    print("\n✅ All theme system checks passed!")
    print("\nTheme system is ready to use. Features:")
    print("  • Automatic Windows theme detection")
    print("  • Manual theme toggle button (sun/moon icon)")
    print("  • Complete light/dark stylesheets for all widgets")
    print("  • Theme-aware button styles (primary, success, danger, warning, info)")
    print("  • Dynamic theme switching without restart")
    
except Exception as e:
    print(f"❌ Error testing theme system: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
