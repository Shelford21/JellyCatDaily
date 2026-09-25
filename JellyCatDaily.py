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
# CSS
# =========================================================

def load_css():

    try:

        with open(
            "styles.css",
            "r",
            encoding="utf-8"
        ) as f:

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
# REFRESH
# =========================================================

st_autorefresh(
    interval=1000,
    key="jellycat_clock"
)


# =========================================================
# FUNCTIONS
# =========================================================

def touch():

    st.session_state.last_activity = time.time()


def list_images():

    try:

        files = supabase.storage.from_(
            BUCKET
        ).list()

    except Exception as e:

        st.error(
            f"Failed to access Supabase Storage: {e}"
        )

        return []


    images = []


    for file in files:

        name = file.get("name", "")

        if not name:
            continue

        lower = name.lower()

        if lower.endswith(
            (
                ".jpg",
                ".jpeg",
                ".png",
                ".webp"
            )
        ):

            try:

                url = supabase.storage.from_(
                    BUCKET
                ).get_public_url(name)

                images.append(
                    {
                        "name": name,
                        "url": url
                    }
                )

            except Exception:

                continue


    images.sort(
        key=lambda x: x["name"].lower()
    )

    return images


def create_filename(original_name):

    base_name = os.path.splitext(
        original_name
    )[0]

    safe_name = re.sub(
        r"[^a-zA-Z0-9_-]",
        "_",
        base_name
    )

    timestamp = datetime.now().strftime(
        "%Y%m%d_%H%M%S_%f"
    )

    return f"{safe_name}_{timestamp}.jpg"


def process_image(uploaded_file):

    img = Image.open(
        uploaded_file
    )

    # Convert to RGB
    if img.mode != "RGB":

        img = img.convert("RGB")


    # Resize while keeping aspect ratio
    img = ImageOps.contain(
        img,
        TARGET_SIZE,
        Image.Resampling.LANCZOS
    )


    # Create 1920x1080 white canvas
    canvas = Image.new(
        "RGB",
        TARGET_SIZE,
        (255, 255, 255)
    )


    # Center image
    x = (
        TARGET_SIZE[0]
        - img.width
    ) // 2

    y = (
        TARGET_SIZE[1]
        - img.height
    ) // 2


    canvas.paste(
        img,
        (x, y)
    )


    # Convert to JPEG bytes
    buffer = BytesIO()

    canvas.save(
        buffer,
        format="JPEG",
        quality=95
    )

    buffer.seek(0)

    return buffer.getvalue()


# =========================================================
# LOAD IMAGES
# =========================================================

images = list_images()


# =========================================================
# EDIT MODE
# =========================================================

elapsed = (
    time.time()
    - st.session_state.last_activity
)

edit_mode = elapsed < EDIT_TIMEOUT


if edit_mode:

    remaining = max(
        0,
        int(EDIT_TIMEOUT - elapsed)
    )


    st.title(
        "Image Manager"
    )


    st.info(
        f"Editing Mode - slideshow starts in "
        f"{remaining} seconds"
    )


    # =====================================================
    # UPLOAD
    # =====================================================

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
            f"uploaded_"
            f"{uploaded.name}_"
            f"{uploaded.size}"
        )


        if upload_key not in st.session_state:

            try:

                # -----------------------------------------
                # Mark upload as processed
                # -----------------------------------------

                st.session_state[
                    upload_key
                ] = True


                # -----------------------------------------
                # Create filename
                # -----------------------------------------

                filename = create_filename(
                    uploaded.name
                )


                # -----------------------------------------
                # Convert image
                # -----------------------------------------

                image_bytes = process_image(
                    uploaded
                )


                st.info(
                    f"Uploading `{filename}`..."
                )


                # -----------------------------------------
                # UPLOAD TO SUPABASE STORAGE
                # -----------------------------------------

                result = supabase.storage.from_(
                    BUCKET
                ).upload(
                    path=filename,
                    file=image_bytes,
                    file_options={
                        "content-type": "image/jpeg",
                        "cache-control": "3600",
                        "upsert": "false"
                    }
                )


                # -----------------------------------------
                # SHOW SUPABASE RESPONSE
                # -----------------------------------------

                st.write(
                    "Supabase upload response:",
                    result
                )


                # -----------------------------------------
                # VERIFY FILE EXISTS
                # -----------------------------------------

                verify_files = (
                    supabase
                    .storage
                    .from_(BUCKET)
                    .list()
                )


                uploaded_names = [
                    f.get("name")
                    for f in verify_files
                ]


                if filename in uploaded_names:

                    st.success(
                        f"Successfully uploaded: "
                        f"{filename}"
                    )

                    touch()

                    time.sleep(1)

                    st.rerun()

                else:

                    st.error(
                        "Upload request completed, "
                        "but the file was not found "
                        "inside the Supabase bucket."
                    )


            except Exception as e:

                st.error(
                    "SUPABASE UPLOAD ERROR"
                )

                st.exception(e)

                # Allow retry
                if upload_key in st.session_state:

                    del st.session_state[
                        upload_key
                    ]


    # =====================================================
    # EXISTING IMAGES
    # =====================================================

    st.subheader(
        "Uploaded Images"
    )


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

                        result = (
                            supabase
                            .storage
                            .from_(BUCKET)
                            .remove(
                                [img["name"]]
                            )
                        )


                        st.write(
                            "Delete response:",
                            result
                        )


                        touch()

                        st.rerun()


                    except Exception as e:

                        st.error(
                            "DELETE ERROR"
                        )

                        st.exception(e)


# =========================================================
# SLIDESHOW
# =========================================================

else:

    if len(images) == 0:

        st.warning(
            "No images uploaded."
        )

        st.stop()


    # =====================================================
    # MANUAL MODE TIMEOUT
    # =====================================================

    if st.session_state.manual_mode:

        inactive_seconds = (
            time.time()
            - st.session_state.last_manual_action
        )


        if inactive_seconds > 60:

            st.session_state.manual_mode = False

            st.rerun()


    # =====================================================
    # AUTOMATIC SLIDESHOW
    # =====================================================

    slide_tick = int(
        (elapsed - EDIT_TIMEOUT)
        // SLIDE_INTERVAL
    )


    current_index = (
        slide_tick
        % len(images)
    )


    # =====================================================
    # BUTTONS
    # =====================================================

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


    # =====================================================
    # CURRENT IMAGE
    # =====================================================

    if st.session_state.manual_mode:

        current = images[
            st.session_state.manual_index
        ]

    else:

        current = images[
            current_index
        ]


    # =====================================================
    # KEYBOARD CONTROL
    # =====================================================

    st.iframe(
        """
        <!DOCTYPE html>

        <html>

        <body>

        <script>

        document.addEventListener(
            "keydown",
            function(event) {

                if (event.key === "ArrowLeft") {

                    event.preventDefault();

                    window.parent.location.search =
                        "?nav=prev";

                }

                if (event.key === "ArrowRight") {

                    event.preventDefault();

                    window.parent.location.search =
                        "?nav=next";

                }

            }
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

    st.markdown(
        f"""
        <div
            style="
                width:100vw;
                height:calc(100vh - 50px);
                display:flex;
                justify-content:center;
                align-items:center;
                overflow:hidden;
                background:white;
            "
        >

            <img
                src="{current['url']}"
                style="
                    width:100vw;
                    height:100%;
                    object-fit:cover;
                    display:block;
                    user-select:none;
                    -webkit-user-drag:none;
                "
                draggable="false"
            >

        </div>
        """,
        unsafe_allow_html=True
    )
