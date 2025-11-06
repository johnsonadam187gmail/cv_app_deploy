import streamlit as st
import base64
import time
import io
import os
from pydantic import BaseModel
from openai import OpenAI
from PyPDF2 import PdfReader
# NOTE: The actual 'markdown_to_docx' and 'packages.utils' are omitted for simplicity and single-file constraint.

# --- Global Configuration and Mock Dependencies ---

# NOTE: Since the prompts.py file is not included, we define the required templates here.
PROMPT_TEMPLATES = {
    'cv_system_prompt': (
        "You are an expert resume and cover letter generator. "
        "Create a single, cohesive, professional document set based on the user's provided files, "
        "explicitly tailoring it to the job description. The resume MUST be separated from the "
        "cover letter by the exact delimiter: ---COVER LETTER---."
    ),
    'cv_user_prompt_template': (
        "Name: {name}\n\n"
        "Personal Summary: {summary_file}\n\n"
        "LinkedIn/Resume Text: {linkedin_file}\n\n"
        "Job Description: {job_description}\n\n"
        "Previous Output (for iteration): {previous}\n\n"
        "Feedback from Evaluation: {feedback}\n\n"
        "Generate the tailored resume and cover letter now, using the required delimiter."
    ),
    'evaluation_system_prompt_template': (
        "You are an objective evaluation agent. Assess the provided document against the Job Description: {job_description}. "
        "Determine if the document is perfectly tailored and ready to be submitted. Respond ONLY in the requested JSON format."
    ),
    'evaluation_user_prompt_template': "The document to evaluate is:\n\n---\n\n{response}"
}

def load_keys():
    """Loads API key from Streamlit secrets."""
    # Ensure 'OPENROUTER_API_KEY' is set in your Streamlit secrets.toml file
    api_key = st.secrets.get("OPENROUTER_API_KEY", os.environ.get("OPENROUTER_API_KEY"))
    if api_key:
        return True, api_key
    return False, None

def pdf_reader(pdf_file_bytes):
    """
    Reads the content of the PDF file bytes.
    The bytes are wrapped in io.BytesIO to provide a file-like object for PdfReader.
    """
    if pdf_file_bytes is None:
        # This handles the case where no file was uploaded (optional upload)
        return "" 

    try:
        # Crucial fix: Wrap raw bytes in io.BytesIO to create a file-like object
        pdf_file_object = io.BytesIO(pdf_file_bytes)
        text_out = ""
        
        # Initialize PdfReader with the file-like object
        reader = PdfReader(pdf_file_object)
        
        for page in reader.pages:
            text = page.extract_text()
            if text:
                text_out += text + "\n"
        
        return text_out
    
    except Exception as e:
        st.error(f"Error parsing PDF file: {e}")
        # Return an empty string or a descriptive error message to the LLM
        return f"Error: Could not read LinkedIn PDF. Error details: {e}"
        
    

# Structured outputs are necessary to ensure specific outputs from the llm.
class StructuredOutput(BaseModel):
    is_acceptable: bool
    feedback: str

# --- LLM Agent Functions ---

def cv_agent(summary_file, linkedin_file, job_description, feedback, previous = '', name= "Adam Johnson"):
    key_test, api_key = load_keys()
    if not key_test:
        raise ValueError("API Key not found in Streamlit secrets.")

    # FIX: Removed the non-breaking space (U+00A0) after api_key)
    client = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=api_key)
    
    cv_system_prompt = PROMPT_TEMPLATES['cv_system_prompt']

    cv_user_prompt = PROMPT_TEMPLATES['cv_user_prompt_template'].format(
        name=name,
        summary_file=summary_file,
        linkedin_file=linkedin_file,
        job_description=job_description,
        feedback=feedback,
        previous=previous
    )

    messages = [{"role": "system", "content": cv_system_prompt},{"role": "user", "content": cv_user_prompt}]
    
    response = client.chat.completions.create(
        model="openai/gpt-4o-mini", 
        messages=messages
    )
    return response.choices[0].message.content


def evaluataion_agent(response_text, job_description):
    key_test, api_key = load_keys()
    if not key_test:
        raise ValueError("API Key not found in Streamlit secrets.")

    # FIX: Removed the non-breaking space (U+00A0) after api_key)
    client = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=api_key)
    
    evaluation_system_prompt = PROMPT_TEMPLATES['evaluation_system_prompt_template'].format(
        job_description=job_description
    )

    evaluation_user_prompt = PROMPT_TEMPLATES['evaluation_user_prompt_template'].format(
        response=response_text
    )
    
    messages = [
        {"role": "system", "content": evaluation_system_prompt}, 
        {"role": "user", "content": evaluation_user_prompt}
    ]
    
    # NOTE: The original code uses client.beta.chat.completions.parse which is specific
    # to OpenRouter or a custom wrapper. We are mimicking structured output using
    # the standard OpenAI/OpenRouter JSON format, assuming the model supports it.
    response = client.chat.completions.create(
        model="openai/gpt-4o-mini", # Changed model to match the other agent for consistency
        messages=messages,
        response_format={"type": "json_object"} # Standard way to request JSON output
    )
    
    # Parse the response text into the StructuredOutput model
    import json
    try:
        json_output = json.loads(response.choices[0].message.content)
        return StructuredOutput(**json_output)
    except Exception as e:
        st.error(f"Failed to parse structured LLM response: {e}")
        # Return default non-acceptable state on failure
        return StructuredOutput(is_acceptable=False, feedback="Error parsing LLM evaluation response.")


def llm_run_loop(summary, linkedin, job_description, name="Adam Johnson"):
    """Runs the iterative CV generation and evaluation loop."""
    start_time = time.perf_counter()
    counter = 1
    is_accepted = False
    feedback = "N/A"
    previous_cv = ""
    cv_full_output = ""
    
    max_iterations = 10 # Prevent endless loops in a web environment
    
    with st.empty(): # Use an empty container to display real-time status
        while not is_accepted and counter <= max_iterations:
            st.info(f"Iteration {counter}: Generating document and running evaluation...")
            
            # Generate the document (CV and Cover Letter combined)
            cv_full_output = cv_agent(summary, linkedin, job_description, feedback, previous=previous_cv, name=name)
            
            # Evaluate the document
            eval_result = evaluataion_agent(cv_full_output, job_description)
            
            is_accepted = eval_result.is_acceptable
            feedback = eval_result.feedback
            previous_cv = cv_full_output # Store the current output for the next iteration
            
            st.text(f"Evaluation Feedback: {feedback}")
            
            if is_accepted:
                st.success(f"Document accepted after {counter} iterations!")
            elif counter == max_iterations:
                st.warning(f"Max iterations ({max_iterations}) reached. Outputting final version.")

            counter += 1
            check_timer = time.perf_counter()
            if check_timer - start_time > 900: # 15 minutes max
                st.error("Max time reached, exiting loop.")
                break
                
    end_time = time.perf_counter()
    run_time = end_time - start_time
    
    return cv_full_output, eval_result, run_time, counter - 1 # return actual iteration count

# --- Utility Function for Downloadable Content ---
def get_download_link(file_content, filename, link_text):
    """Generates a link for downloading the provided text content as a file."""
    b64 = base64.b64encode(file_content.encode()).decode()
    href = f'<a href="data:file/txt;base64,{b64}" download="{filename}">{link_text}</a>'
    return href

# --- Main Streamlit Application Layout ---

st.set_page_config(
    page_title="AI Resume & Letter Tailor",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.title("📄 AI Document Tailoring App")
st.markdown("Upload your information, paste the job advertisement, and generate a perfectly tailored resume and cover letter.")

# --------------------------
# 1. User Input Section
# --------------------------

st.header("Step 1: Provide Your Information")

# Column layout for inputs
col1, col2 = st.columns(2)

# Initialize content variables
personal_info_content = ""
job_ad_content = ""
linkedin_pdf_bytes = None # Will store the PDF content as bytes

with col1:
    st.subheader("Personal Statement/Bio")
    # Option to write or upload the personal statement
    input_choice = st.radio(
        "Choose input method for your personal information:",
        ("Write directly", "Upload a .txt file"),
        key="personal_input_choice"
    )

    if input_choice == "Write directly":
        personal_info_content = st.text_area(
            "Paste your personal statement, background, or professional summary here (required):",
            height=300,
            key="personal_statement_text"
        )
    else:
        uploaded_txt = st.file_uploader(
            "Upload your personal statement (.txt or .md):",
            type=["txt", "md"],
            key="personal_statement_file"
        )
        if uploaded_txt is not None:
            # Read file content (assuming text file for simplicity)
            personal_info_content = uploaded_txt.read().decode("utf-8")
            st.success("Personal statement uploaded successfully.")
        else:
            st.info("Please upload a file to proceed.")

with col2:
    st.subheader("Job Advertisement")
    job_ad_content = st.text_area(
        "Paste the full job advertisement or description here (required):",
        height=300,
        key="job_ad_text"
    )

st.subheader("LinkedIn Profile PDF")
linkedin_pdf = st.file_uploader(
    "Upload your LinkedIn profile PDF export (or any relevant resume PDF):",
    type=["pdf"],
    key="linkedin_pdf_upload"
)

# --------------------------------------------------------------------------------------------------
# INSERTION POINT 1: PDF DATA PROCESSING
# --------------------------------------------------------------------------------------------------
if linkedin_pdf is not None:
    # Read the file content as bytes
    linkedin_pdf_bytes = linkedin_pdf.read()
# --------------------------------------------------------------------------------------------------


# --------------------------
# 2. LLM Execution Button
# --------------------------

st.markdown("---")
st.header("Step 2: Generate Documents")

# Simple check to ensure required fields have content before running
is_ready = (personal_info_content and len(personal_info_content.strip()) > 50) and \
           (job_ad_content and len(job_ad_content.strip()) > 50) and \
           (linkedin_pdf is not None)

if st.button("Generate Tailored Documents", disabled=not is_ready):

    # --------------------------------------------------------------------------------------------------
    # INSERTION POINT 2: BACKEND LLM FUNCTION CALL
    # --------------------------------------------------------------------------------------------------
    try:
        # 1. Prepare inputs: Convert PDF bytes to text content
        linkedin_text = pdf_reader(linkedin_pdf_bytes)
        
        # 2. Call the main iterative function
        full_document, evaluation_result, run_time, iterations = llm_run_loop(
            summary=personal_info_content, 
            linkedin=linkedin_text, 
            job_description=job_ad_content
        )
        
        # 3. Split the single document output into resume and letter
        if "---COVER LETTER---" in full_document:
            resume, letter = full_document.split("---COVER LETTER---", 1)
        else:
            resume = full_document
            letter = "Error: Could not find '---COVER LETTER---' delimiter in the output."
            st.error("LLM output format error: Missing document separator.")
        
        # 4. Store the results in session state
        st.session_state['resume'] = resume.strip()
        st.session_state['letter'] = letter.strip()
        st.session_state['stats'] = f"Completed in {run_time:.2f} seconds over {iterations} iterations."
        
        st.success("✅ Generation Complete! Review your documents below.")
        st.info(st.session_state['stats'])
        
    except ValueError as ve:
        st.error(f"Configuration Error: {ve}")
    except Exception as e:
        st.error(f"An unexpected error occurred during generation: {e}")
        # Ensure session state is cleared on failure to prevent stale output
        if 'resume' in st.session_state: del st.session_state['resume']
        if 'letter' in st.session_state: del st.session_state['letter']
    # --------------------------------------------------------------------------------------------------


# --------------------------
# 3. Output and Export Section (No changes needed here)
# --------------------------

if 'resume' in st.session_state and 'letter' in st.session_state:
    st.markdown("---")
    st.header("Step 3: Review and Export")
    
    # Display stats if available
    if 'stats' in st.session_state:
        st.text(st.session_state['stats'])

    tab1, tab2 = st.tabs(["📄 Tailored Resume", "✉️ Cover Letter"])

    with tab1:
        st.subheader("Tailored Resume")
        # Display the resume in an editable text area for easy copying
        st.text_area(
            "Generated Resume (Copy/Paste Friendly):",
            st.session_state['resume'],
            height=600,
            key="final_resume_display"
        )
        # Download button for the resume
        st.markdown(
            get_download_link(st.session_state['resume'], "tailored_resume.txt", "⬇️ Download Resume as TXT (For Word/Docs)"),
            unsafe_allow_html=True
        )

    with tab2:
        st.subheader("Cover Letter")
        # Display the letter in an editable text area for easy copying
        st.text_area(
            "Generated Cover Letter (Copy/Paste Friendly):",
            st.session_state['letter'],
            height=400,
            key="final_letter_display"
        )
        # Download button for the letter
        st.markdown(
            get_download_link(st.session_state['letter'], "tailored_cover_letter.txt", "⬇️ Download Cover Letter as TXT (For Word/Docs)"),
            unsafe_allow_html=True
        )

# Footer for context
st.markdown("---")
st.markdown("💡 *The downloadable .txt files contain clean text, which can be easily copied and pasted into Microsoft Word or Google Docs for final formatting.*")

# Add Firebase configuration placeholders for completeness in a Streamlit context, although not used here
if 'db_initialized' not in st.session_state:
    try:
        # We are using st.secrets here because this is Streamlit code, but the placeholder
        # prevents errors in the canvas environment.
        if 'FIREBASE_CONFIG' in locals():
            st.session_state['db_initialized'] = True
    except Exception:
        pass # Ignore if not running in the Canvas environment