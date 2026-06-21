import streamlit as st
from supabase import create_client
from streamlit_autorefresh import st_autorefresh
from datetime import datetime
import uuid
import base64
from PIL import Image, ImageOps
from io import BytesIO


import time

if "manual_mode" not in st.session_state:
    st.session_state.manual_mode = False

if "manual_index" not in st.session_state:
    st.session_state.manual_index = 0

if "last_manual_action" not in st.session_statei
    st.session_state.last_manual_action = 0


params = st.query_params

if "nav" in params:

    if params["nav"] == "next":
        st.session_state.manual_index = (
            st.session_state.manual_index + 1
        ) % len(images)

    elif params["nav"] == "prev":
        st.session_state.manual_index = (
            st.session_state.manual_index - 1
        ) % len(images)

    st.query_params.clear()
    
st.components.v1.html("""
<script>

document.addEventListener('keydown', function(e) {

    if (e.key === 'ArrowLeft') {
        window.parent.location.search='?nav=prev';
    }

    if (e.key === 'ArrowRight') {
        window.parent.location.search='?nav=next';
    }

});

</script>
""", height=0)


st.components.v1.html("""
<script>

document.addEventListener("click", function() {
    window.parent.postMessage({
        type: "next"
    }, "*");
});

document.addEventListener("contextmenu", function(e) {
    e.preventDefault();

    window.parent.postMessage({
        type: "prev"
    }, "*");
});

</script>
""", height=0)



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

import time

if "last_activity" not in st.session_state:
    st.session_state.last_activity = time.time()

if "slide_index" not in st.session_state:
    st.session_state.slide_index = 0

# refresh every second
st_autorefresh(interval=1000, key="clock")

# =========================
# HELPERS
# =========================

def touch():
    st.session_state.last_activity = time.time()

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

elapsed = time.time() - st.session_state.last_activity

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
        
    if uploaded is not None:
        
        upload_key = f"uploaded_{uploaded.name}_{uploaded.size}"
        
        if upload_key not in st.session_state:
        
            st.session_state[upload_key] = True
        
            ext = uploaded.name.split(".")[-1]
            from datetime import datetime
            import re
            import os
            
            base_name = os.path.splitext(uploaded.name)[0]
            
            safe_name = re.sub(
                r'[^a-zA-Z0-9_-]',
                '_',
                base_name
            )
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            filename = f"{safe_name}_{timestamp}.jpg"
        
            # TARGET_WIDTH = 3064
            # TARGET_HEIGHT = 1610
            from PIL import Image, ImageOps

            # TARGET = (3064, 1610)
            TARGET = (1920, 1080)
            img = Image.open(uploaded)
            
            img = ImageOps.contain(
                img,
                TARGET,
                Image.Resampling.LANCZOS
            )
            
            canvas = Image.new(
                "RGB",
                TARGET,
                (255,255,255)  # white background
            )
            
            x = (TARGET[0] - img.width) // 2
            y = (TARGET[1] - img.height) // 2
            
            canvas.paste(img, (x, y))
            
            img = canvas
            
            img = img.convert("RGB")
            
            buffer = BytesIO()
            
            img.save(
                buffer,
                format="JPEG",
                quality=95
            )
            
            buffer.seek(0)
            
            from datetime import datetime
            import re
            import os
            
            base_name = os.path.splitext(uploaded.name)[0]
            
            safe_name = re.sub(
                r'[^a-zA-Z0-9_-]',
                '_',
                base_name
            )
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            filename = f"{safe_name}_{timestamp}.jpg"
            
            supabase.storage.from_(BUCKET).upload(
                path=filename,
                file=buffer.getvalue()
            )
            
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

     if st.session_state.manual_mode:

        inactive_seconds = (
            time.time()
            - st.session_state.last_manual_action
        )

        if inactive_seconds > 60:
    
            st.session_state.manual_mode = False




    
    if "manual_index" not in st.session_state:
        st.session_state.manual_index = 0
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("⬅ Previous"):

            st.session_state.manual_mode = True
        
            st.session_state.manual_index = (
                st.session_state.manual_index - 1
            ) % len(images)
        
            st.session_state.last_manual_action = time.time()
    
    with col2:
        if st.button("Next ➡"):

            st.session_state.manual_mode = True
        
            st.session_state.manual_index = (
                st.session_state.manual_index + 1
            ) % len(images)
        
            st.session_state.last_manual_action = time.time()
            
    # current = images[st.session_state.manual_index]
    # current = images[current_index]

   
        
    if st.session_state.manual_mode:

        current = images[
            st.session_state.manual_index
        ]
    
    else:
    
        current = images[
            current_index
        ]
    
    
        
    st.markdown(
        f"""
        <div style="
            width:100vw;
            height:100vh;
            display:flex;
            justify-content:center;
            align-items:center;
            overflow:hidden;
        ">
            <img
                src="{current['url']}"
                style="
                    width:100vw;
                    height:100vh;
                    object-fit:cover;
                "
            >
        </div>
        """,
        unsafe_allow_html=True
    )    

    
