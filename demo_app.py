"""Demo application for cjm-fasthtml-web-audio library.

Demonstrates multi-buffer Web Audio API playback with parallel decode.
Serves test audio segments and provides play/stop controls.

Run with: python demo_app.py
"""

import json
from pathlib import Path

from fasthtml.common import (
    fast_app, Div, H1, H2, P, Span, Button, Script,
    APIRouter, FileResponse,
)

# DaisyUI components
from cjm_fasthtml_daisyui.core.resources import get_daisyui_headers
from cjm_fasthtml_daisyui.core.testing import create_theme_persistence_script
from cjm_fasthtml_daisyui.components.actions.button import btn, btn_sizes, btn_colors, btn_styles
from cjm_fasthtml_daisyui.utilities.semantic_colors import bg_dui, text_dui

# Tailwind utilities
from cjm_fasthtml_tailwind.utilities.spacing import p, m
from cjm_fasthtml_tailwind.utilities.sizing import w, h, max_w, container
from cjm_fasthtml_tailwind.utilities.typography import font_size, font_weight, font_family
from cjm_fasthtml_tailwind.utilities.flexbox_and_grid import (
    flex_display, flex_direction, items, gap, grow, flex_wrap,
)
from cjm_fasthtml_tailwind.core.base import combine_classes

# App core
from cjm_fasthtml_app_core.core.routing import register_routes
from cjm_fasthtml_app_core.core.htmx import handle_htmx_request

# Web Audio library
from cjm_fasthtml_web_audio.models import WebAudioConfig
from cjm_fasthtml_web_audio.components import render_audio_urls_input, render_web_audio_script


# =============================================================================
# Configuration
# =============================================================================

SEGMENTS_DIR = Path(__file__).parent / "test_files" / "segments"
AUDIO_SRC_PREFIX = "/audio/src"

# Demo config — basic playback (no speed/replay/auto-nav)
DEMO_CONFIG = WebAudioConfig(
    namespace="demo",
    indicator_selector=".demo-playing-indicator",
)


# =============================================================================
# Demo Page Renderer
# =============================================================================

def render_demo_page(audio_files, audio_urls):
    """Create the demo page content factory."""

    def page_content():
        """Render the demo page with multi-buffer playback test."""

        # Build segment cards for testing
        segment_cards = []
        for i, audio_file in enumerate(audio_files):
            card = Div(
                Div(
                    Span(f"Segment {i}", cls=combine_classes(font_weight.bold)),
                    Span(
                        audio_file.name,
                        cls=combine_classes(font_size.sm, text_dui.base_content.opacity(60), font_family.mono),
                    ),
                    Span(
                        "playing",
                        cls=combine_classes(
                            "demo-playing-indicator", font_size.xs, text_dui.success,
                        ),
                        style="visibility:hidden;",
                    ),
                    cls=combine_classes(flex_display, items.center, gap(3)),
                ),
                Button(
                    "Play 5s",
                    cls=combine_classes(btn, btn_colors.primary, btn_sizes.sm),
                    onclick=f"window.playDemoSegment({i}, 0, 5, this.closest('.demo-card').querySelector('.demo-playing-indicator'))",
                ),
                Button(
                    "Play Full",
                    cls=combine_classes(btn, btn_styles.ghost, btn_sizes.sm),
                    onclick=f"window.playDemoSegment({i}, 0, 999, this.closest('.demo-card').querySelector('.demo-playing-indicator'))",
                ),
                cls=combine_classes(
                    "demo-card",
                    flex_display, items.center, gap(4),
                    p(3), bg_dui.base_200, "rounded-lg",
                ),
                data_audio_file_index=str(i),
                data_start_time="0",
                data_end_time="5",
            )
            segment_cards.append(card)

        # Limit display to first 10 segments for readability
        display_cards = segment_cards[:10]
        if len(segment_cards) > 10:
            display_cards.append(
                P(f"... and {len(segment_cards) - 10} more segments",
                  cls=combine_classes(font_size.sm, text_dui.base_content.opacity(50), p(3)))
            )

        return Div(
            H1("Web Audio API Multi-Buffer Demo",
               cls=combine_classes(font_size._3xl, font_weight.bold, m.b(2))),
            P(f"{len(audio_files)} audio segments available for parallel decode.",
              cls=combine_classes(text_dui.base_content.opacity(70), m.b(4))),

            # Controls
            Div(
                Button(
                    "Load All Audio",
                    cls=combine_classes(btn, btn_colors.primary),
                    onclick="window.initDemoAudio()",
                ),
                Button(
                    "Stop",
                    cls=combine_classes(btn, btn_styles.ghost),
                    onclick="window.stopDemoAudio()",
                ),
                cls=combine_classes(flex_display, items.center, gap(3), m.b(6)),
            ),

            # Segment cards
            H2("Segments", cls=combine_classes(font_size.xl, font_weight.bold, m.b(3))),
            Div(
                *display_cards,
                cls=combine_classes(flex_display, flex_direction.col, gap(2), m.b(6)),
            ),

            # Audio infrastructure
            render_audio_urls_input(DEMO_CONFIG, audio_urls),
            render_web_audio_script(
                DEMO_CONFIG,
                focus_input_id="demo-focus-input",
                card_stack_id="demo-card-stack",
            ),

            # Enable debug logging
            Script("window.DEBUG_DEMO_AUDIO = true;"),

            cls=combine_classes(container, max_w._4xl, m.x.auto, p(6)),
        )

    return page_content


# =============================================================================
# Main Application
# =============================================================================

def main():
    """Initialize the demo and start the server."""
    print("\n" + "=" * 70)
    print("Initializing cjm-fasthtml-web-audio Demo")
    print("=" * 70)

    # Find audio segments
    if SEGMENTS_DIR.exists():
        audio_files = sorted(SEGMENTS_DIR.glob("*.mp3"))
    else:
        audio_files = []
        print(f"  Warning: No segments dir at {SEGMENTS_DIR}")

    print(f"  Found {len(audio_files)} audio segments")

    # Build audio URLs
    audio_urls = [f"{AUDIO_SRC_PREFIX}?path={f}" for f in audio_files]

    # Initialize FastHTML app
    app, rt = fast_app(
        pico=False,
        hdrs=[*get_daisyui_headers(), create_theme_persistence_script()],
        title="Web Audio Demo",
        htmlkw={'data-theme': 'light'},
    )

    router = APIRouter(prefix="")
    audio_router = APIRouter(prefix="/audio")

    # -------------------------------------------------------------------------
    # Audio Serving Route
    # -------------------------------------------------------------------------

    @audio_router
    def src(request, path: str):
        """Serve audio file by path."""
        file_path = Path(path)
        if file_path.is_file():
            return FileResponse(str(file_path), media_type="audio/mpeg")
        return "Audio file not found", 404

    # -------------------------------------------------------------------------
    # Page Route
    # -------------------------------------------------------------------------

    page_content = render_demo_page(audio_files, audio_urls)

    @router
    def index(request):
        """Demo homepage."""
        return handle_htmx_request(request, page_content)

    # -------------------------------------------------------------------------
    # Register routes
    # -------------------------------------------------------------------------
    register_routes(app, router, audio_router)

    # Debug output
    print("\n" + "=" * 70)
    print("Registered Routes:")
    print("=" * 70)
    for route in app.routes:
        if hasattr(route, 'path'):
            print(f"  {route.path}")
    print("=" * 70)
    print("Demo App Ready!")
    print("=" * 70 + "\n")

    return app


if __name__ == "__main__":
    import uvicorn
    import webbrowser
    import threading

    app = main()

    port = 5035
    host = "0.0.0.0"
    display_host = 'localhost' if host in ['0.0.0.0', '127.0.0.1'] else host

    print(f"Server: http://{display_host}:{port}")
    print()
    print("Controls:")
    print("  Click 'Load All Audio' to fetch and decode all segments in parallel")
    print("  Click 'Play 5s' on any segment to play first 5 seconds")
    print("  Click 'Play Full' to play the entire segment")
    print("  Click 'Stop' to stop current playback")
    print("  Open browser console to see debug logs")
    print()

    timer = threading.Timer(1.5, lambda: webbrowser.open(f"http://localhost:{port}"))
    timer.daemon = True
    timer.start()

    uvicorn.run(app, host=host, port=port)
