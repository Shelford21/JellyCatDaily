import streamlit as st
from supabase import create_client
from streamlit_autorefresh import st_autorefresh
from datetime import datetime
from PIL import Image, ImageOps
from io import BytesIO
import time
import re
import os


# =========================================================
# PAGE CONFIG
# =========================================================

st.set_page_config(
    page_title="Jellycat Daily",
    layout="wide",
    initial_sidebar_state="collapsed"
)


# =========================================================
# CONSTANTS
# =========================================================

TOP_MARGIN = 0
EDIT_TIMEOUT = 60
SLIDE_INTERVAL = 15

TARGET_SIZE = (1920, 1080)


# =========================================================
# SESSION STATE
# =========================================================

if "manual_mode" not in st.session_state:
    st.session_state.manual_mode = False

if "manual_index" not in st.session_state:
    st.session_state.manual_index = 0

if "last_manual_action" not in st.session_state:
    st.session_state.last_manual_action = 0

if "last_activity" not in st.session_state:
    st.session_state.last_activity = time.time()


# =========================================================
# CUSTOM CSS
# =========================================================

def load_css():
    try:
        with open("styles.css", "r", encoding="utf-8") as f:
            st.markdown(
                f"<style>{f.read()}</style>",
                unsafe_allow_html=True
            )
    except FileNotFoundError:
        pass


load_css()


st.markdown(
    f"""
    <style>

    #MainMenu {{
        visibility: hidden;
    }}

    header {{
        visibility: hidden;
    }}

    footer {{
        visibility: hidden;
    }}

    .block-container {{
        padding-top: {TOP_MARGIN}px !important;
        padding-left: 0 !important;
        padding-right: 0 !important;
        padding-bottom: 0 !important;
        max-width: 100% !important;
    }}

    </style>
    """,
    unsafe_allow_html=True
)


# =========================================================
# SUPABASE
# =========================================================

supabase = create_client(
    st.secrets["SUPABASE_URL"],
    st.secrets["SUPABASE_KEY"]
)

BUCKET = st.secrets["SUPABASE_BUCKET"]


# =========================================================
# AUTO REFRESH
# =========================================================

# Refresh every second.
# This controls the editing timeout and slideshow timer.
st_autorefresh(
    interval=1000,
    key="jellycat_clock"
)


# =========================================================
# HELPER FUNCTIONS
# =========================================================

def touch():
    """
    Reset editing timeout.
    """
    st.session_state.last_activity = time.time()


def list_images():
    """
    Get all image files from Supabase Storage.
    """
    try:
        files = supabase.storage.from_(BUCKET).list()
    except Exception as e:
        st.error(f"Failed to load images from Supabase: {e}")
        return []

    images = []

    for f in files:
        name = f.get("name", "")

        if not name:
            continue

        lower = name.lower()

        if lower.endswith((".jpg", ".jpeg", ".png", ".webp")):

            try:
                url = supabase.storage.from_(BUCKET).get_public_url(name)

                images.append(
                    {
                        "name": name,
                        "url": url
                    }
                )

            except Exception:
                continue

    # Alphabetical order
    images.sort(
        key=lambda x: x["name"].lower()
    )

    return images


def create_safe_filename(original_name):
    """
    Create a safe filename for Supabase Storage.
    """

    base_name = os.path.splitext(original_name)[0]

    safe_name = re.sub(
        r"[^a-zA-Z0-9_-]",
        "_",
        base_name
    )

    timestamp = datetime.now().strftime(
        "%Y%m%d_%H%M%S"
    )

    return f"{safe_name}_{timestamp}.jpg"


def process_image(uploaded_file):
    """
    Convert uploaded image into 1920x1080 JPEG.
    Image is contained inside the canvas without cropping.
    """

    img = Image.open(uploaded_file)

    # Convert image to RGB
    if img.mode != "RGB":
        img = img.convert("RGB")

    # Fit image inside 1920x1080
    img = ImageOps.contain(
        img,
        TARGET_SIZE,
        Image.Resampling.LANCZOS
    )

    # Create white background
    canvas = Image.new(
        "RGB",
        TARGET_SIZE,
        (255, 255, 255)
    )

    # Center image
    x = (TARGET_SIZE[0] - img.width) // 2
    y = (TARGET_SIZE[1] - img.height) // 2

    canvas.paste(
        img,
        (x, y)
    )

    # Save to memory
    buffer = BytesIO()

    canvas.save(
        buffer,
        format="JPEG",
        quality=95
    )

    buffer.seek(0)

    return buffer


# =========================================================
# LOAD IMAGES
# =========================================================

images = list_images()


# =========================================================
# HANDLE KEYBOARD / MOUSE NAVIGATION
# =========================================================
#
# IMPORTANT:
# This block is AFTER images = list_images()
# so the navigation logic never tries to use images
# before the variable exists.
#

if len(images) > 0:

    params = st.query_params

    if "nav" in params:

        nav = params["nav"]

        if nav == "next":

            st.session_state.manual_mode = True

            st.session_state.manual_index = (
                st.session_state.manual_index + 1
            ) % len(images)

            st.session_state.last_manual_action = time.time()

        elif nav == "prev":

            st.session_state.manual_mode = True

            st.session_state.manual_index = (
                st.session_state.manual_index - 1
            ) % len(images)

            st.session_state.last_manual_action = time.time()

        # Remove navigation parameter
        st.query_params.clear()


# =========================================================
# CALCULATE EDIT MODE
# =========================================================

elapsed = (
    time.time()
    - st.session_state.last_activity
)

edit_mode = elapsed < EDIT_TIMEOUT


# =========================================================
# EDIT MODE
# =========================================================

if edit_mode:

    remaining = max(
        0,
        int(EDIT_TIMEOUT - elapsed)
    )

    st.title("Image Manager")

    st.info(
        f"Editing Mode - slideshow starts in {remaining} seconds"
    )


    # -----------------------------------------------------
    # UPLOAD
    # -----------------------------------------------------

    uploaded = st.file_uploader(
        "Upload Image",
        type=[
            "jpg",
            "jpeg",
            "png",
            "webp"
        ],
        key="image_uploader"
    )


    if uploaded is not None:

        upload_key = (
            f"uploaded_{uploaded.name}_{uploaded.size}"
        )

        if upload_key not in st.session_state:

            st.session_state[upload_key] = True

            try:

                # Create filename
                filename = create_safe_filename(
                    uploaded.name
                )

                # Process image
                buffer = process_image(
                    uploaded
                )

                # Upload to Supabase
                supabase.storage.from_(BUCKET).upload(
                    path=filename,
                    file=buffer.getvalue()
                )

                # Reset timer
                touch()

                # Reset uploader state
                st.session_state.manual_mode = False

                # Refresh application
                st.rerun()

            except Exception as e:

                st.error(
                    f"Upload failed: {e}"
                )


    # -----------------------------------------------------
    # EXISTING IMAGES
    # -----------------------------------------------------

    st.subheader("Uploaded Images")


    if len(images) == 0:

        st.info(
            "No images uploaded yet."
        )

    else:

        for img in images:

            col1, col2 = st.columns(
                [8, 1]
            )

            with col1:

                st.write(
                    img["name"]
                )

            with col2:

                if st.button(
                    "Delete",
                    key=f"delete_{img['name']}"
                ):

                    try:

                        supabase.storage.from_(
                            BUCKET
                        ).remove(
                            [img["name"]]
                        )

                        touch()

                        st.rerun()

                    except Exception as e:

                        st.error(
                            f"Delete failed: {e}"
                        )


# =========================================================
# SLIDESHOW MODE
# =========================================================

else:

    # -----------------------------------------------------
    # NO IMAGES
    # -----------------------------------------------------

    if len(images) == 0:

        st.warning(
            "No images uploaded."
        )

        st.stop()


    # -----------------------------------------------------
    # MANUAL MODE TIMEOUT
    # -----------------------------------------------------

    if st.session_state.manual_mode:

        inactive_seconds = (
            time.time()
            - st.session_state.last_manual_action
        )

        # After 60 seconds, return to automatic slideshow
        if inactive_seconds > 60:

            st.session_state.manual_mode = False

            # Reset automatic slideshow timing
            st.rerun()


    # -----------------------------------------------------
    # AUTOMATIC SLIDESHOW INDEX
    # -----------------------------------------------------

    slide_tick = int(
        (elapsed - EDIT_TIMEOUT)
        // SLIDE_INTERVAL
    )

    current_index = (
        slide_tick
        % len(images)
    )


    # -----------------------------------------------------
    # NAVIGATION BUTTONS
    # -----------------------------------------------------

    col1, col2 = st.columns(2)


    with col1:

        if st.button(
            "⬅ Previous",
            use_container_width=True
        ):

            st.session_state.manual_mode = True

            st.session_state.manual_index = (
                st.session_state.manual_index - 1
            ) % len(images)

            st.session_state.last_manual_action = (
                time.time()
            )

            st.rerun()


    with col2:

        if st.button(
            "Next ➡",
            use_container_width=True
        ):

            st.session_state.manual_mode = True

            st.session_state.manual_index = (
                st.session_state.manual_index + 1
            ) % len(images)

            st.session_state.last_manual_action = (
                time.time()
            )

            st.rerun()


    # -----------------------------------------------------
    # DETERMINE CURRENT IMAGE
    # -----------------------------------------------------

    if st.session_state.manual_mode:

        current = images[
            st.session_state.manual_index
        ]

    else:

        current = images[
            current_index
        ]


    # =====================================================
    # KEYBOARD + MOUSE CONTROLS
    # =====================================================
    #
    # st.iframe() replaces the deprecated
    # st.components.v1.html().
    #
    # Left Arrow  -> Previous
    # Right Arrow -> Next
    # Left Click  -> Next
    # Right Click -> Previous
    #
    # =====================================================

    st.iframe(
        f"""
        <!DOCTYPE html>

        <html>

        <head>

            <meta charset="UTF-8">

            <style>

                html,
                body {{
                    margin: 0;
                    padding: 0;
                    width: 100%;
                    height: 1px;
                    overflow: hidden;
                    background: transparent;
                }}

            </style>

        </head>

        <body>

        <script>

            // ==========================================
            // KEYBOARD
            // ==========================================

            document.addEventListener(
                "keydown",
                function(event) {{

                    if (event.key === "ArrowLeft") {{

                        event.preventDefault();

                        window.parent.location.search =
                            "?nav=prev";
                    }}

                    if (event.key === "ArrowRight") {{

                        event.preventDefault();

                        window.parent.location.search =
                            "?nav=next";
                    }}

                }}
            );


            // ==========================================
            // LEFT CLICK
            // ==========================================

            document.addEventListener(
                "click",
                function(event) {{

                    window.parent.location.search =
                        "?nav=next";

                }}
            );


            // ==========================================
            // RIGHT CLICK
            // ==========================================

            document.addEventListener(
                "contextmenu",
                function(event) {{

                    event.preventDefault();

                    window.parent.location.search =
                        "?nav=prev";

                }}
            );

        </script>

        </body>

        </html>
        """,
        height=1
    )


    # =====================================================
    # DISPLAY IMAGE
    # =====================================================

       st.image(
        current["url"],
        use_container_width=True
    )
