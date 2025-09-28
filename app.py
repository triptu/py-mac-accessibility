#!/usr/bin/env python3
"""
Streamlit web UI for browsing macOS applications and their accessibility data.
"""

from PIL.ImageFile import ImageFile
import streamlit as st
import json
import subprocess
import time
from io import BytesIO
from macapptree import get_tree_screenshot, get_app_bundle
from streamlit.delta_generator import DeltaGenerator
from typing import NamedTuple, Any


@st.cache_data(ttl=5)  # Cache for 5 seconds to avoid too frequent updates
def get_running_apps() -> list[str]:
    """Get list of running applications using AppleScript."""
    try:
        # Use AppleScript to get running apps
        script = '''
        tell application "System Events"
            set appList to {}
            set runningApps to every application process whose background only is false
            repeat with anApp in runningApps
                set end of appList to name of anApp
            end repeat
            return appList
        end tell
        '''

        result = subprocess.run(
            ["osascript", "-e", script],
            capture_output=True,
            text=True,
            check=True
        )

        apps_string = result.stdout.strip()
        if apps_string:
            apps_list = apps_string.strip('{}').split(', ')
            # Clean up app names (remove quotes and spaces)
            apps_list = [app.strip(' "') for app in apps_list if app.strip()]
            return sorted(apps_list)
        return []
    except subprocess.CalledProcessError as e:
        st.error(f"Error getting running apps: {e}")
        return []
    except Exception as e:
        st.error(f"Unexpected error: {e}")
        return []

class AppAccessibilityData(NamedTuple):
    tree: dict[str, Any] | None
    screenshot: ImageFile | None
    segmented: ImageFile | None
    error: str | None

def get_accessibility_data(app_name: str) -> AppAccessibilityData:
    """Get accessibility tree and screenshots for an app."""
    try:
        # Get app bundle
        bundle = get_app_bundle(app_name)
        if not bundle:
            return AppAccessibilityData(None, None, None, f"Could not find bundle for {app_name}")

        # Get tree and screenshots
        tree, screenshot, segmented = get_tree_screenshot(bundle)

        return AppAccessibilityData(tree, screenshot, segmented, None)
    except Exception as e:
        return AppAccessibilityData(None, None, None, str(e))


def display_tree_structure(tree: dict[str, Any], max_depth: int=3, current_depth: int=0):
    """Display accessibility tree in a structured format."""
    if current_depth > max_depth or not tree:
        return

    role: str = tree.get('role', 'Unknown')
    title: str = tree.get('title', '')
    value = tree.get('value', '')

    # Create expandable sections for tree nodes
    with st.expander(f"📱 {role}" + (f" - {title}" if title else ""), expanded=(current_depth < 2)):
        col1, col2 = st.columns(2)

        with col1:
            if title:
                st.text(f"Title: {title}")
            if value and str(value) != title:
                st.text(f"Value: {value}")
            if tree.get('bounds'):
                st.text(f"Bounds: {tree['bounds']}")
            if tree.get('enabled') is not None:
                st.text(f"Enabled: {tree['enabled']}")

        with col2:
            if tree.get('description'):
                st.text(f"Description: {tree['description']}")
            if tree.get('help'):
                st.text(f"Help: {tree['help']}")
            if tree.get('subrole'):
                st.text(f"Subrole: {tree['subrole']}")

        # Show children
        children = tree.get('children', [])
        if children:
            st.text(f"Children: {len(children)}")
            for i, child in enumerate(children):
                display_tree_structure(child, max_depth, current_depth + 1)

class AppOptions(NamedTuple):
    selected_app: str | None
    max_tree_depth: int
    show_json: bool
    auto_refresh: bool

def render_sidebar() -> AppOptions:
    '''Render the sidebar with app selection and options.'''
    with st.sidebar:
        st.header("Select Application")

        # Refresh button
        if st.button("Refresh Apps"):
            st.cache_data.clear()

        # Get running apps
        with st.spinner("Loading running applications..."):
            apps = get_running_apps()

        if not apps:
            st.error("No applications found. Make sure you have accessibility permissions.")
            st.stop()

        selected_app = st.selectbox(
            "Choose an app:",
            apps,
            index=0 if apps else None,
            help="Select an application to analyze its accessibility structure"
        )

        # Options
        st.header("Options")
        max_tree_depth = st.slider("Max tree depth", 1, 5, 3, help="Maximum depth to display in tree structure")
        show_json = st.checkbox("Show raw JSON", help="Display the raw accessibility JSON data")
        auto_refresh = st.checkbox("Auto refresh (5s)", help="Automatically refresh data every 5 seconds")
        return AppOptions(selected_app, max_tree_depth, show_json, auto_refresh)

def render_tab_screenshots(
    tab: DeltaGenerator,
    selected_app: str,
    screenshot: ImageFile | None,
    segmented: ImageFile | None
):
    with tab:
        st.subheader("Application Screenshots")

        col_original, col_segmented = st.columns(2)

        with col_original:
            if screenshot:
                st.markdown("**📷 Original Screenshot**")
                st.image(screenshot, caption=f"{selected_app} - Original", use_container_width=True)

                # Download button for original
                img_buffer = BytesIO()
                screenshot.save(img_buffer, format='PNG')
                st.download_button(
                    label="⬇️ Download Original",
                    data=img_buffer.getvalue(),
                    file_name=f"{selected_app}_original.png",
                    mime="image/png"
                )
            else:
                st.warning("No screenshot available")

        with col_segmented:
            if segmented:
                st.markdown("**🎯 Segmented Screenshot**")
                st.image(segmented, caption=f"{selected_app} - UI Elements Highlighted", use_container_width=True)

                # Download button for segmented
                img_buffer = BytesIO()
                segmented.save(img_buffer, format='PNG')
                st.download_button(
                    label="⬇️ Download Segmented",
                    data=img_buffer.getvalue(),
                    file_name=f"{selected_app}_segmented.png",
                    mime="image/png"
                )
            else:
                st.warning("No segmented screenshot available")

def render_tab_tree(tab: DeltaGenerator, tree: dict[str, Any] | None, max_depth: int):
    with tab:
        st.subheader("Accessibility Tree Structure")

        if tree:
            st.markdown("🌳 **Interactive Tree Explorer**")
            st.info("Expand/collapse sections to explore the UI hierarchy")
            display_tree_structure(tree, max_depth)
        else:
            st.warning("No accessibility tree available")

def render_raw_json(tab: DeltaGenerator, tree: dict[str, Any] | None, selected_app: str, show_json: bool):
    with tab:
        st.subheader("Raw JSON Data")

        if tree and show_json:
            json_str = json.dumps(tree, indent=2, default=str)
            st.code(json_str, language='json')

            st.download_button(
                label="⬇️ Download JSON",
                data=json_str,
                file_name=f"{selected_app}_accessibility.json",
                mime="application/json"
            )
        elif not show_json:
            st.info("Enable 'Show raw JSON' in the sidebar to view the raw data")
        else:
            st.warning("No JSON data available")

 # Count elements by role
def count_elements(node: dict[str, Any], counts: dict[str, int]| None=None):
    if counts is None:
        counts = {}

    if isinstance(node, dict):
        role: str = node.get('role', 'Unknown')
        counts[role] = counts.get(role, 0) + 1

        for child in node.get('children', []):
            count_elements(child, counts)

    return counts

def render_tab_summary(tab: DeltaGenerator, tree: dict[str, Any] | None, screenshot: ImageFile | None):
    with tab:
        st.subheader("Application Summary")
        if tree:
            element_counts = count_elements(tree)
            col_element_stats, col_element_types = st.columns(2)

            with col_element_stats:
                st.markdown("**📊 Element Statistics**")
                st.metric("Total Elements", sum(element_counts.values()))
                st.metric("Unique Roles", len(element_counts))

                if screenshot:
                    st.metric("Screenshot Size", f"{screenshot.size[0]}×{screenshot.size[1]}")

            with col_element_types:
                st.markdown("**🏷️ Top Element Types(roles)**")
                # Sort by count and show top 5
                sorted_elements = sorted(element_counts.items(), key=lambda x: x[1], reverse=True)
                for role, count in sorted_elements[:8]:
                    st.text(f"{role}: {count}")

            # Show element distribution chart
            if len(element_counts) > 1:
                st.markdown("**📈 Element Distribution**")
                st.bar_chart(element_counts)

        else:
            st.warning("No summary data available")

def render_main_content(selected_app: str | None, settings: AppOptions):
    if not selected_app:
        st.info("Select an application from the sidebar to view its accessibility data.")
        return

    st.header(f"App: '{selected_app}'")

    # Get accessibility data
    with st.spinner(f"Analyzing {selected_app}..."):
        tree, screenshot, segmented, error = get_accessibility_data(selected_app)

    if error:
        if "returned non-zero exit status 1" in error:
            print(f"Error analyzing '{selected_app}': {error}")
            error = "Make sure there is a visible app window."
        st.error(f"Error analyzing '{selected_app}': {error}")
        st.info("""
        **Troubleshooting tips:**
        - Make sure the app has visible windows
        - Grant accessibility permissions in System Preferences > Security & Privacy > Privacy > Accessibility
        - Try selecting a different visible application
        """)
    else:
        # Create tabs for different views
        tab1, tab2, tab3, tab4 = st.tabs(["📸 Screenshots", "🌳 Tree Structure", "📄 Raw JSON", "ℹ️ Summary"])
        render_tab_screenshots(tab1, selected_app, screenshot, segmented)
        render_tab_tree(tab2, tree, settings.max_tree_depth)
        render_raw_json(tab3, tree, selected_app, settings.show_json)
        render_tab_summary(tab4, tree, screenshot)

def render_footer():
    st.markdown("---")
    st.markdown("Built by [Tushar](https://tushar.ai)")

def main():
    st.set_page_config(
        page_title="macOS App Accessibility Browser",
        page_icon="🖥️",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    st.title("MacOS App Accessibility Browser")
    st.markdown("Browse running macOS applications and explore their accessibility trees")

    settings = render_sidebar()

    if settings.auto_refresh: # immediately refresh once
        time.sleep(0.1)  # Small delay to avoid too frequent refreshes
        st.rerun()

    render_main_content(settings.selected_app, settings)
    render_footer()


if __name__ == "__main__":
    main()
