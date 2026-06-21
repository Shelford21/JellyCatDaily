import streamlit as st
from supabase import create_client
from streamlit_autorefresh import st_autorefresh
from datetime import datetime
import uuid
import base64
# from streamlit_autorefresh import st_autorefresh

# st_autorefresh(
#         interval=5 * 1000,
#         key="datarefresh"
# )

def load_css():
    with open("styles.css") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

load_css()



# =========================
# SETTINGS
# =========================

TOP_MARGIN = 0
EDIT_TIMEOUT = 60          # seconds
SLIDE_INTERVAL = 15        # seconds

# =========================
# PAGE
# =========================

st.set_page_config(
    page_title="Jellycat Daily",
    layout="wide"
)

st.markdown(f"""
<style>

#MainMenu {{
    visibility:hidden;
}}

header {{
    visibility:hidden;
}}

footer {{
    visibility:hidden;
}}

.block-container {{
    padding-top:{TOP_MARGIN}px !important;
    padding-left:0 !important;
    padding-right:0 !important;
    padding-bottom:0 !important;
    max-width:100% !important;
}}

</style>
""", unsafe_allow_html=True)

# =========================
# SUPABASE
# =========================

supabase = create_client(
    st.secrets["SUPABASE_URL"],
    st.secrets["SUPABASE_KEY"]
)

BUCKET = st.secrets["SUPABASE_BUCKET"]

# =========================
# SESSION
# =========================

if "last_activity" not in st.session_state:
    st.session_state.last_activity = datetime.now()

if "slide_index" not in st.session_state:
    st.session_state.slide_index = 0

# refresh every second
st_autorefresh(interval=1000, key="clock")

# =========================
# HELPERS
# =========================

def touch():
    st.session_state.last_activity = datetime.now()

def list_images():
    files = supabase.storage.from_(BUCKET).list()

    images = []

    for f in files:
        name = f["name"]

        lower = name.lower()

        if (
            lower.endswith(".jpg")
            or lower.endswith(".jpeg")
            or lower.endswith(".png")
            or lower.endswith(".webp")
        ):
            url = supabase.storage.from_(BUCKET).get_public_url(name)

            images.append({
                "name": name,
                "url": url
            })

    images.sort(key=lambda x: x["name"])

    return images

# =========================
# DATA
# =========================

images = list_images()

elapsed = (
    datetime.now()
    - st.session_state.last_activity
).total_seconds()

edit_mode = elapsed < EDIT_TIMEOUT

# =========================
# EDIT MODE
# =========================

if edit_mode:

    remaining = int(EDIT_TIMEOUT - elapsed)

    st.title("Image Manager")

    st.info(
        f"Editing Mode - slideshow starts in {remaining} seconds"
    )

    uploaded = st.file_uploader(
        "Upload Image",
        type=["jpg", "jpeg", "png", "webp"]
    )

    if uploaded:

        ext = uploaded.name.split(".")[-1]

        filename = f"{uuid.uuid4()}.{ext}"

        try:
            result = supabase.storage.from_(BUCKET).upload(
                path=filename,
                file=uploaded.getvalue()
            )
        
            st.success("Upload success")
            st.write(result)
        
        except Exception as e:
            st.error(str(e))
            st.stop()

        touch()
        st.rerun()

    st.subheader("Uploaded Images")

    for img in images:

        col1, col2 = st.columns([8, 1])

        with col1:
            st.write(img["name"])

        with col2:

            if st.button(
                "Delete",
                key=img["name"]
            ):

                supabase.storage.from_(BUCKET).remove(
                    [img["name"]]
                )

                touch()
                st.rerun()

# =========================
# SLIDESHOW MODE
# =========================

else:

    if len(images) == 0:
        st.warning("No images uploaded.")
        st.stop()

    slide_tick = int(
        (elapsed - EDIT_TIMEOUT)
        // SLIDE_INTERVAL
    )

    current_index = (
        slide_tick % len(images)
    )

    current = images[current_index]

    st.markdown(
        f"""
        <div style="
        width:100%;
        text-align:center;
        ">
            <img
            src="{current['url']}"
            style="
            width:100%;
            height:auto;
            ">
        </div>
        """,
        unsafe_allow_html=True
    )
