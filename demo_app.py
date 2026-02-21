"""Demo application for cjm-fasthtml-web-audio library.

Demonstrates multi-buffer Web Audio API playback with parallel decode
and namespace isolation between two independent instances on the same page.

Run with: python demo_app.py
"""

import json
from pathlib import Path

from fasthtml.common import (
    fast_app, Div, H1, H2, H3, P, Span, Button, Script, Select, Option, Input, Label,
    APIRouter, FileResponse,
)

# DaisyUI components
from cjm_fasthtml_daisyui.core.resources import get_daisyui_headers
from cjm_fasthtml_daisyui.core.testing import create_theme_persistence_script
from cjm_fasthtml_daisyui.components.actions.button import btn, btn_sizes, btn_colors, btn_styles
from cjm_fasthtml_daisyui.components.data_display.badge import badge, badge_styles, badge_sizes, badge_colors
from cjm_fasthtml_daisyui.utilities.semantic_colors import bg_dui, text_dui, border_dui

# Tailwind utilities
from cjm_fasthtml_tailwind.utilities.spacing import p, m
from cjm_fasthtml_tailwind.utilities.sizing import w, h, max_w, container
from cjm_fasthtml_tailwind.utilities.typography import font_size, font_weight, font_family
from cjm_fasthtml_tailwind.utilities.borders import border
from cjm_fasthtml_tailwind.utilities.flexbox_and_grid import (
    flex_display, flex_direction, items, gap, grow, justify,
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

# Instance 1: Basic playback (simulates alignment)
BASIC_CONFIG = WebAudioConfig(
    namespace="basic",
    indicator_selector=".basic-playing-indicator",
)

# Instance 2: Full features (simulates review)
REVIEW_CONFIG = WebAudioConfig(
    namespace="review",
    indicator_selector=".review-playing-indicator",
    enable_speed=True,
    enable_replay=True,
    enable_auto_nav=True,
)


# =============================================================================
# Segment Card Builders
# =============================================================================

def build_segment_card(i, audio_file, namespace):
    """Build a single segment card for a given instance namespace."""
    ns = namespace.capitalize()
    indicator_cls = f"{namespace}-playing-indicator"

    return Div(
        Div(
            Span(f"#{i}", cls=combine_classes(font_weight.bold, font_family.mono)),
            Span(
                audio_file.name,
                cls=combine_classes(font_size.sm, text_dui.base_content.opacity(60), font_family.mono),
            ),
            Span(
                "playing",
                cls=combine_classes(indicator_cls, font_size.xs, text_dui.success),
                style="visibility:hidden;",
            ),
            cls=combine_classes(flex_display, items.center, gap(3), grow()),
        ),
        Button(
            "Play 5s",
            cls=combine_classes(btn, btn_colors.primary, btn_sizes.xs),
            onclick=f"window.play{ns}Segment({i}, 0, 5, "
                    f"this.closest('.{namespace}-card').querySelector('.{indicator_cls}'))",
        ),
        Button(
            "Full",
            cls=combine_classes(btn, btn_styles.ghost, btn_sizes.xs),
            onclick=f"window.play{ns}Segment({i}, 0, 999, "
                    f"this.closest('.{namespace}-card').querySelector('.{indicator_cls}'))",
        ),
        cls=combine_classes(
            f"{namespace}-card",
            flex_display, items.center, gap(3),
            p(2), bg_dui.base_200, "rounded-lg",
        ),
        data_audio_file_index=str(i),
        data_start_time="0",
        data_end_time="5",
    )


def build_segment_list(audio_files, namespace, max_display=6):
    """Build a list of segment cards, truncated to max_display."""
    cards = [build_segment_card(i, f, namespace) for i, f in enumerate(audio_files)]
    display = cards[:max_display]
    if len(cards) > max_display:
        display.append(
            P(f"... and {len(cards) - max_display} more",
              cls=combine_classes(font_size.xs, text_dui.base_content.opacity(50), p(2)))
        )
    return Div(*display, cls=combine_classes(flex_display, flex_direction.col, gap(1)))


# =============================================================================
# Demo Page Renderer
# =============================================================================

def render_demo_page(audio_files, audio_urls):
    """Create the demo page content factory."""

    def page_content():
        """Render the demo page with two independent audio instances."""

        # ----- Instance 1: Basic -----
        basic_section = Div(
            Div(
                H3("Instance 1: Basic", cls=combine_classes(font_weight.bold)),
                Span("basic", cls=combine_classes(badge, badge_styles.outline, badge_sizes.sm)),
                cls=combine_classes(flex_display, items.center, gap(2), m.b(2)),
            ),
            P("No speed/replay/auto-nav. Simulates alignment playback.",
              cls=combine_classes(font_size.sm, text_dui.base_content.opacity(60), m.b(3))),
            Div(
                Button("Load Audio", cls=combine_classes(btn, btn_colors.primary, btn_sizes.sm),
                       onclick="window.initBasicAudio()"),
                Button("Stop", cls=combine_classes(btn, btn_styles.ghost, btn_sizes.sm),
                       onclick="window.stopBasicAudio()"),
                cls=combine_classes(flex_display, items.center, gap(2), m.b(3)),
            ),
            build_segment_list(audio_files, "basic"),
            render_audio_urls_input(BASIC_CONFIG, audio_urls),
            render_web_audio_script(BASIC_CONFIG, focus_input_id="basic-focus", card_stack_id="basic-cs"),
            Script("window.DEBUG_BASIC_AUDIO = true;"),
            cls=combine_classes(p(4), bg_dui.base_100, border(1), border_dui.base_300, "rounded-lg"),
        )

        # ----- Instance 2: Review (full features) -----
        speed_select = Select(
            *[Option(f"{s}x", value=str(s), selected=(s == 1.0))
              for s in [0.5, 0.75, 1.0, 1.25, 1.5, 2.0, 3.0]],
            cls=combine_classes("select select-bordered select-xs"),
            onchange="window.setReviewSpeed(parseFloat(this.value))",
        )

        review_section = Div(
            Div(
                H3("Instance 2: Review", cls=combine_classes(font_weight.bold)),
                Span("review", cls=combine_classes(badge, badge_colors.primary, badge_sizes.sm)),
                cls=combine_classes(flex_display, items.center, gap(2), m.b(2)),
            ),
            P("Speed control, replay, auto-navigate enabled. Simulates review playback.",
              cls=combine_classes(font_size.sm, text_dui.base_content.opacity(60), m.b(3))),
            Div(
                Button("Load Audio", cls=combine_classes(btn, btn_colors.primary, btn_sizes.sm),
                       onclick="window.initReviewAudio()"),
                Button("Stop", cls=combine_classes(btn, btn_styles.ghost, btn_sizes.sm),
                       onclick="window.stopReviewAudio()"),
                Button("Replay", cls=combine_classes(btn, btn_colors.secondary, btn_sizes.sm),
                       onclick="window.replayReviewSegment()"),
                Span("Speed:", cls=combine_classes(font_size.sm, m.l(2))),
                speed_select,
                Label(
                    Input(type="checkbox", cls="checkbox checkbox-xs",
                          onchange="window.setReviewAutoNavigate(this.checked)"),
                    Span("Auto-nav", cls=font_size.sm),
                    cls=combine_classes(flex_display, items.center, gap(1), m.l(2)),
                ),
                cls=combine_classes(flex_display, items.center, gap(2), m.b(3)),
            ),
            build_segment_list(audio_files, "review"),
            render_audio_urls_input(REVIEW_CONFIG, audio_urls),
            render_web_audio_script(
                REVIEW_CONFIG, focus_input_id="review-focus", card_stack_id="review-cs",
                nav_down_btn_id="review-nav-down",
            ),
            Script("window.DEBUG_REVIEW_AUDIO = true;"),
            cls=combine_classes(p(4), bg_dui.base_100, border(1), border_dui.base_300, "rounded-lg"),
        )

        return Div(
            H1("Web Audio API — Dual Instance Demo",
               cls=combine_classes(font_size._3xl, font_weight.bold, m.b(2))),
            P(f"{len(audio_files)} audio segments. Two independent instances with separate namespaces.",
              cls=combine_classes(text_dui.base_content.opacity(70), m.b(6))),

            # Two-column layout
            Div(
                basic_section,
                review_section,
                cls=combine_classes(
                    "grid grid-cols-1 lg:grid-cols-2",
                    gap(4), m.b(6),
                ),
            ),

            cls=combine_classes(container, max_w._6xl, m.x.auto, p(6)),
        )

    return page_content


# =============================================================================
# Main Application
# =============================================================================

def main():
    """Initialize the demo and start the server."""
    print("\n" + "=" * 70)
    print("Initializing cjm-fasthtml-web-audio Demo (Dual Instance)")
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
    print("Namespace Isolation Test:")
    print("  Instance 1 (basic): initBasicAudio, playBasicSegment, stopBasicAudio")
    print("  Instance 2 (review): initReviewAudio, playReviewSegment, stopReviewAudio")
    print("  + setReviewSpeed, replayReviewSegment, setReviewAutoNavigate")
    print()
    print("  Verify: Playing on one instance does not affect the other")
    print("  Open browser console to see debug logs from both instances")
    print()

    timer = threading.Timer(1.5, lambda: webbrowser.open(f"http://localhost:{port}"))
    timer.daemon = True
    timer.start()

    uvicorn.run(app, host=host, port=port)
