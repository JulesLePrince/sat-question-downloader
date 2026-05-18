import streamlit as st
import os
import random
import pandas as pd
from pypdf import PdfWriter
import io

# Constants
BASE_DIR = "data"  # Data directory contains the subject folders
SUBJECTS = ["math", "reading_writing"]

st.set_page_config(page_title="SAT Question Compiler", layout="wide")

# --- Custom CSS to hide "Deploy" button and clean up UI ---
st.markdown("""
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    .stAppDeployButton {display:none;}
    header {visibility: hidden;}
    /* Adjust spacing around the content */
    .block-container {
        padding-top: 3rem;
        padding-bottom: 10rem;
        padding-left: 5rem;
        padding-right: 5rem;
    }
    /* Hide the hash link icon next to headers */
    .viewerBadge_container__1QSob {display:none;}
    a.top-level-anchor {display:none;}
    .st-emotion-cache-15zrgzn {display:none;}
    /* Streamlit 1.28+ anchor hiding */
    [data-testid="stHeaderActionElements"] {display:none;}
    .st-emotion-cache-1v0vkay {display:none;}
    /* Ensure header is completely gone and takes no space */
    [data-testid="stHeader"] {
        display: none;
        height: 0;
    }
    </style>
    """, unsafe_allow_html=True)

@st.cache_data
def load_questions():
    questions = []
    
    for subject in SUBJECTS:
        subject_path = os.path.join(BASE_DIR, subject)
        if not os.path.exists(subject_path):
            continue
            
        # Areas (e.g., algebra, craft_and_structure)
        for area in os.listdir(subject_path):
            area_path = os.path.join(subject_path, area)
            if not os.path.isdir(area_path):
                continue
                
            # Topics (e.g., linear_equations_in_one_variable)
            for topic in os.listdir(area_path):
                topic_path = os.path.join(area_path, topic)
                if not os.path.isdir(topic_path):
                    continue
                    
                # Difficulty (e.g., level_1_easy)
                for difficulty in os.listdir(topic_path):
                    diff_path = os.path.join(topic_path, difficulty)
                    if not os.path.isdir(diff_path):
                        continue
                    
                    # Question Files
                    files = os.listdir(diff_path)
                    # Extract unique IDs
                    ids = set()
                    for f in files:
                        if f.endswith("_dry.pdf"):
                            ids.add(f.replace("_dry.pdf", ""))
                    
                    for q_id in ids:
                        dry_file = f"{q_id}_dry.pdf"
                        ans_file = f"{q_id}_answers.pdf"
                        
                        if dry_file in files and ans_file in files:
                            questions.append({
                                "id": q_id,
                                "subject": subject,
                                "area": area,
                                "topic": topic,
                                "difficulty": difficulty,
                                "dry_path": os.path.join(diff_path, dry_file),
                                "ans_path": os.path.join(diff_path, ans_file)
                            })
                            
    return pd.DataFrame(questions)

st.title("📚 SAT Question Compiler", anchor=False)
st.markdown("Select your criteria, and I'll generate a custom PDF of SAT questions and an answer key for you.")

df = load_questions()

if df.empty:
    st.error("No questions found. Please check the directory structure.")
    st.stop()

# --- Helper Functions ---
def format_label(text):
    """Converts 'area_and_volume' to 'Area And Volume'"""
    return text.replace("_", " ").title()

def reset_generation():
    """Clears generated PDFs from session state when inputs change"""
    if 'dry_pdf' in st.session_state:
        del st.session_state['dry_pdf']
    if 'ans_pdf' in st.session_state:
        del st.session_state['ans_pdf']
    if 'sample_size' in st.session_state:
        del st.session_state['sample_size']

# --- Step-by-Step Selection ---
st.subheader("Step 1: Define your search criteria", anchor=False)
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.markdown("**1. Subject**")
    subjects = sorted(df['subject'].unique())
    selected_subjects = st.multiselect(
        "Filter by Subject", 
        options=subjects, 
        default=subjects,
        format_func=format_label,
        label_visibility="collapsed",
        on_change=reset_generation
    )
    filtered_df = df[df['subject'].isin(selected_subjects)]

with col2:
    st.markdown("**2. Area**")
    areas = sorted(filtered_df['area'].unique())
    selected_areas = st.multiselect(
        "Filter by Area", 
        options=areas,
        format_func=format_label,
        label_visibility="collapsed",
        on_change=reset_generation
    )
    if selected_areas:
        filtered_df = filtered_df[filtered_df['area'].isin(selected_areas)]

with col3:
    st.markdown("**3. Topic**")
    topics = sorted(filtered_df['topic'].unique())
    selected_topics = st.multiselect(
        "Filter by Topic", 
        options=topics,
        format_func=format_label,
        label_visibility="collapsed",
        on_change=reset_generation
    )
    if selected_topics:
        filtered_df = filtered_df[filtered_df['topic'].isin(selected_topics)]

with col4:
    st.markdown("**4. Difficulty**")
    diffs = sorted(filtered_df['difficulty'].unique())
    selected_diffs = st.multiselect(
        "Filter by Difficulty", 
        options=diffs,
        format_func=format_label,
        label_visibility="collapsed",
        on_change=reset_generation
    )
    if selected_diffs:
        filtered_df = filtered_df[filtered_df['difficulty'].isin(selected_diffs)]

# Step 2: Question Count
st.divider()
st.subheader("Step 2: Choose quantity", anchor=False)

# Show prominent match count here
st.metric("Total Questions Matching Your Criteria", len(filtered_df))

num_questions = st.slider(
    "How many questions would you like to pick?", 
    min_value=1, 
    max_value=20, 
    value=10,
    on_change=reset_generation
)

# Step 3: Generation
st.divider()
st.subheader("Step 3: Generate and Download", anchor=False)
if st.button("🚀 Generate PDFs", type="primary", use_container_width=True):
    if filtered_df.empty:
        st.warning("No questions match your current selection.")
    else:
        # Sample questions
        available_count = len(filtered_df)
        sample_size = min(num_questions, available_count)
        
        if sample_size < num_questions:
            st.info(f"Only {available_count} questions match your criteria. Using all of them.")
            
        sampled_questions = filtered_df.sample(n=sample_size)
        
        # Merge PDFs
        dry_writer = PdfWriter()
        ans_writer = PdfWriter()
        
        progress_bar = st.progress(0)
        for i, (idx, row) in enumerate(sampled_questions.iterrows()):
            dry_writer.append(row['dry_path'])
            ans_writer.append(row['ans_path'])
            progress_bar.progress((i + 1) / sample_size)
        
        # Save to memory
        dry_output = io.BytesIO()
        ans_output = io.BytesIO()
        
        dry_writer.write(dry_output)
        ans_writer.write(ans_output)
        
        # Store in session state to persist across reruns (like clicks on download buttons)
        st.session_state['dry_pdf'] = dry_output.getvalue()
        st.session_state['ans_pdf'] = ans_output.getvalue()
        st.session_state['sample_size'] = sample_size
        
        st.success(f"Successfully generated PDFs with {sample_size} questions!")

# Display download buttons if PDFs have been generated
if 'dry_pdf' in st.session_state:
    col_dl1, col_dl2 = st.columns(2)
    sample_size = st.session_state['sample_size']
    with col_dl1:
        st.download_button(
            label="📥 Download Questions (Dry)",
            data=st.session_state['dry_pdf'],
            file_name=f"SAT_Questions_{sample_size}.pdf",
            mime="application/pdf",
            key="download_dry"
        )
    with col_dl2:
        st.download_button(
            label="📥 Download Answer Key",
            data=st.session_state['ans_pdf'],
            file_name=f"SAT_Answers_{sample_size}.pdf",
            mime="application/pdf",
            key="download_ans"
        )
