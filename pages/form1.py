import streamlit as st
from io import BytesIO
from pypdf import PdfReader, PdfWriter
import fitz  # PyMuPDF

st.set_page_config(page_title="PDF Personalizer", layout="centered")
st.title("PDF Personalizer (Name & Affiliation)")

# ---------------- UI ----------------
tmpl = st.file_uploader("Upload your PDF template", type=["pdf"])
method = st.radio("Choose method", ["Fill PDF form fields (AcroForm)", "Overlay text at coordinates"])

col1, col2 = st.columns(2)
with col1:
    name = st.text_input("Name", value="Jane Doe")
with col2:
    aff  = st.text_input("Affiliation", value="English Dept., GNU")

# If overlay method, ask for positions / style
if method == "Overlay text at coordinates":
    st.caption("Coordinates in points (1 pt = 1/72 inch). Origin is top-left.")
    c1, c2 = st.columns(2)
    with c1:
        x_name = st.number_input("Name X", min_value=0, max_value=5000, value=72, step=1)
        x_aff  = st.number_input("Affiliation X", min_value=0, max_value=5000, value=72, step=1)
        fontsize = st.slider("Font size", 8, 48, value=14)
    with c2:
        y_name = st.number_input("Name Y", min_value=0, max_value=5000, value=150, step=1)
        y_aff  = st.number_input("Affiliation Y", min_value=0, max_value=5000, value=180, step=1)
    all_pages = st.checkbox("Apply to all pages", value=False)

go = st.button("Generate PDF", type="primary", disabled=(tmpl is None))

# --------------- ACTION ---------------
if go:
    bytes_in = tmpl.read()
    if method == "Fill PDF form fields (AcroForm)":
        # Read and list fields
        reader = PdfReader(BytesIO(bytes_in))
        fields = reader.get_fields() or {}
        if not fields:
            st.warning("No form fields found. Switch to 'Overlay text at coordinates', or use a form-enabled template.")
        # Fill fields (update here to match your actual field names)
        # Try common names; show hints to user
        st.info("Available form field names: " + (", ".join(fields.keys()) if fields else "none"))
        data = {
            # CHANGE these keys to match your template (exact field names)
            "name": name,
            "Name": name,
            "full_name": name,
            "affiliation": aff,
            "Affiliation": aff,
            "org": aff,
        }
        # Keep only keys that exist in the template
        data = {k: v for k, v in data.items() if k in fields}

        if not data:
            st.error("Could not match any field names. Check the field names in your template.")
        else:
            writer = PdfWriter()
            writer.clone_document_from_reader(reader)
            # Fill each page’s fields (safe for multi-page)
            for page in writer.pages:
                writer.update_page_form_field_values(page, data)
            # Make sure values render
            if "/AcroForm" in writer._root_object:
                writer._root_object["/AcroForm"].update({"/NeedAppearances": True})

            out = BytesIO()
            writer.write(out)
            out.seek(0)
            st.success("PDF generated.")
            st.download_button("Download filled PDF", out, file_name="filled.pdf", mime="application/pdf")

    else:
        # Overlay text at coordinates using PyMuPDF
        doc = fitz.open(stream=bytes_in, filetype="pdf")
        pages_to_edit = range(len(doc)) if all_pages else [0]
        for pno in pages_to_edit:
            page = doc[pno]
            # Draw black text; fontname 'helv' is built-in Helvetica
            page.insert_text((x_name, y_name), name, fontname="helv", fontsize=fontsize, fill=(0, 0, 0))
            page.insert_text((x_aff,  y_aff),  aff,  fontname="helv", fontsize=fontsize, fill=(0, 0, 0))

        out = BytesIO()
        doc.save(out)
        doc.close()
        out.seek(0)
        st.success("PDF generated.")
        st.download_button("Download personalized PDF", out, file_name="personalized.pdf", mime="application/pdf")
