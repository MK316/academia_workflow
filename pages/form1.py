# requirements: streamlit, pypdf, pymupdf
import os
from io import BytesIO
from datetime import datetime

import streamlit as st
from pypdf import PdfReader, PdfWriter
import fitz  # PyMuPDF

st.set_page_config(page_title="PDF 이름/소속 입력", layout="centered")
st.title("📄 PDF 템플릿에 이름·소속 입력")

st.markdown("템플릿 PDF(예: 증명서)를 업로드하고, 이름/소속을 입력한 뒤 생성하세요.")

tmpl = st.file_uploader("① 템플릿 PDF 업로드", type=["pdf"])

c1, c2 = st.columns(2)
with c1:
    name = st.text_input("이름", value="홍길동")
with c2:
    aff = st.text_input("소속", value="영어교육과")

method = st.radio("② 방법 선택", ["PDF 폼 채우기(있으면 권장)", "좌표 덧씌우기(폼 없을 때)"])

# ---------- Helpers ----------
def fill_form_fields(pdf_bytes: bytes, data_map: dict) -> BytesIO | None:
    reader = PdfReader(BytesIO(pdf_bytes))
    fields = reader.get_fields() or {}
    st.info("감지된 폼 필드: " + (", ".join(fields.keys()) if fields else "없음"))
    if not fields:
        st.warning("폼이 없는 PDF 같습니다. '좌표 덧씌우기' 방법을 사용하세요.")
        return None

    # 템플릿에 실제로 존재하는 필드만 남김
    data = {k: v for k, v in data_map.items() if k in fields}
    if not data:
        st.error("입력하려는 항목 이름이 템플릿 필드와 일치하지 않습니다. 필드명을 확인하세요.")
        return None

    writer = PdfWriter()
    writer.clone_document_from_reader(reader)
    for page in writer.pages:
        writer.update_page_form_field_values(page, data)
    # 값이 보이도록
    if "/AcroForm" in writer._root_object:
        writer._root_object["/AcroForm"].update({"/NeedAppearances": True})

    out = BytesIO()
    writer.write(out); out.seek(0)
    return out

def overlay_text(pdf_bytes: bytes,
                 name: str, aff: str,
                 name_pos: tuple[float, float], aff_pos: tuple[float, float],
                 fontsize: int, font_path: str | None, all_pages: bool) -> BytesIO:
    """
    name_pos, aff_pos are percentages (0~100) of page width/height (easier to align).
    """
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    pages = range(len(doc)) if all_pages else [0]

    for pno in pages:
        page = doc[pno]
        w, h = page.rect.width, page.rect.height
        nx = w * (name_pos[0] / 100.0)
        ny = h * (name_pos[1] / 100.0)
        ax = w * (aff_pos[0] / 100.0)
        ay = h * (aff_pos[1] / 100.0)

        # Use a Korean font if provided; otherwise PDF default (may not render Hangul)
        page.insert_text((nx, ny), name, fontname="KRFont", fontfile=font_path,
                         fontsize=fontsize, fill=(0, 0, 0))
        page.insert_text((ax, ay),  aff,  fontname="KRFont", fontfile=font_path,
                         fontsize=fontsize, fill=(0, 0, 0))

    out = BytesIO(); doc.save(out); doc.close(); out.seek(0)
    return out

# ---------- UI for each method ----------
if method == "PDF 폼 채우기(있으면 권장)":
    st.caption("템플릿에 실제 폼 필드(예: 성명, 소속)가 있을 때 사용합니다.")
    st.markdown("- **PDF 내 폼 필드 이름**이 무엇인지 모르면, 바로 아래 ‘생성’ 후 표시되는 목록을 보고 이름을 맞춰 주세요.")

else:
    st.caption("폼이 없을 때 화면 위치를 잡아 텍스트를 그려 넣습니다.")
    with st.expander("폰트(한글) & 위치 설정", expanded=True):
        colA, colB = st.columns(2)
        with colA:
            name_x = st.slider("이름 X(%)", 0.0, 100.0, 20.0, 0.1)
            name_y = st.slider("이름 Y(%)", 0.0, 100.0, 35.0, 0.1)
            fontsize = st.slider("폰트 크기", 8, 48, 16)
        with colB:
            aff_x = st.slider("소속 X(%)", 0.0, 100.0, 20.0, 0.1)
            aff_y = st.slider("소속 Y(%)", 0.0, 100.0, 42.0, 0.1)
            all_pages = st.checkbox("모든 페이지에 적용", valu_
