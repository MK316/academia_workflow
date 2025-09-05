# requirements: streamlit, pypdf, pymupdf
import os
import tempfile
from io import BytesIO
from datetime import datetime

import streamlit as st
from pypdf import PdfReader, PdfWriter
import fitz  # PyMuPDF

st.set_page_config(page_title="PDF Input (KR/EN)", layout="centered")
st.title("PDF 템플릿에 이름/소속 입력")

st.markdown("템플릿 PDF를 업로드하고, 이름/소속을 입력한 뒤 생성하세요.")

tmpl = st.file_uploader("1) 템플릿 PDF 업로드", type=["pdf"])

c1, c2 = st.columns(2)
with c1:
    name = st.text_input("이름 (Name)", value="홍길동")
with c2:
    aff = st.text_input("소속 (Affiliation)", value="영어교육과")

method = st.radio("2) 방법 선택", ["PDF 폼 채우기(권장: 폼 있을 때)", "좌표에 텍스트 덧씌우기(폼 없을 때)"])

# --------- Helpers (no type-hints to avoid parser issues) ---------
def fill_form_fields(pdf_bytes, data_map):
    reader = PdfReader(BytesIO(pdf_bytes))
    fields = reader.get_fields() or {}
    st.info("감지된 폼 필드: " + (", ".join(fields.keys()) if fields else "없음"))
    if not fields:
        st.warning("폼이 없는 PDF 같습니다. '좌표에 텍스트 덧씌우기'를 사용하세요.")
        return None

    # 템플릿에 존재하는 필드만 남김
    data = {k: v for k, v in data_map.items() if k in fields}
    if not data:
        st.error("입력하려는 항목 이름이 템플릿 필드와 일치하지 않습니다. 필드명을 확인하세요.")
        return None

    writer = PdfWriter()
    writer.clone_document_from_reader(reader)
    for page in writer.pages:
        writer.update_page_form_field_values(page, data)

    # 값 렌더 강제
    if "/AcroForm" in writer._root_object:
        writer._root_object["/AcroForm"].update({"/NeedAppearances": True})

    out = BytesIO()
    writer.write(out)
    out.seek(0)
    return out

def overlay_text(pdf_bytes,
                 name_text, aff_text,
                 name_pos_pct, aff_pos_pct,
                 fontsize, font_path, all_pages):
    """
    name_pos_pct, aff_pos_pct: (x_percent, y_percent), 0~100
    """
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    pages = range(len(doc)) if all_pages else [0]

    for pno in pages:
        page = doc[pno]
        w, h = page.rect.width, page.rect.height
        nx = w * (name_pos_pct[0] / 100.0)
        ny = h * (name_pos_pct[1] / 100.0)
        ax = w * (aff_pos_pct[0] / 100.0)
        ay = h * (aff_pos_pct[1] / 100.0)

        page.insert_text((nx, ny), name_text,
                         fontname="KRFont",
                         fontfile=font_path,
                         fontsize=fontsize,
                         fill=(0, 0, 0))
        page.insert_text((ax, ay), aff_text,
                         fontname="KRFont",
                         fontfile=font_path,
                         fontsize=fontsize,
                         fill=(0, 0, 0))

    out = BytesIO()
    doc.save(out)
    doc.close()
    out.seek(0)
    return out

# --------- Overlay controls (simple, robust) ---------
if method == "좌표에 텍스트 덧씌우기(폼 없을 때)":
    st.caption("좌상단 기준 퍼센트(%)로 위치를 잡습니다. 폰트 파일을 올리면 한글이 확실히 보입니다.")
    colA, colB = st.columns(2)
    with colA:
        name_x = st.slider("이름 X(%)", 0.0, 100.0, 20.0, 0.1)
        name_y = st.slider("이름 Y(%)", 0.0, 100.0, 35.0, 0.1)
        fontsize = st.slider("폰트 크기", 8, 48, 16)
    with colB:
        aff_x = st.slider("소속 X(%)", 0.0, 100.0, 20.0, 0.1)
        aff_y = st.slider("소속 Y(%)", 0.0, 100.0, 42.0, 0.1)
        all_pages = st.checkbox("모든 페이지에 적용", value=False)

    up_font = st.file_uploader("한글 폰트 업로드 (TTF/OTF 권장: Nanum/Noto)", type=["ttf", "otf"])
    font_path = None
    if up_font is not None:
        fd, path = tempfile.mkstemp(suffix=os.path.splitext(up_font.name)[1])
        with os.fdopen(fd, "wb") as f:
            f.write(up_font.read())
        font_path = path
    else:
        # 번들 혹은 시스템 경로 후보
        for p in [
            "fonts/NanumGothic.ttf",
            "fonts/NotoSansKR-Regular.otf",
            "/usr/share/fonts/truetype/nanum/NanumGothic.ttf",
        ]:
            if os.path.exists(p):
                font_path = p
                break
else:
    st.caption("PDF에 실제 '폼 필드'가 있을 때 사용합니다. 생성 후 감지된 필드명이 표시됩니다.")

go = st.button("3) PDF 생성", type="primary", disabled=(tmpl is None))

if go and tmpl is not None:
    pdf_bytes = tmpl.read()
    if method == "PDF 폼 채우기(권장: 폼 있을 때)":
        # 템플릿의 실제 필드명에 맞춰 아래 키를 수정하세요.
        field_map = {
            "성명": name,
            "이름": name,
            "name": name,
            "Name": name,
            "full_name": name,
            "소속": aff,
            "affiliation": aff,
            "Affiliation": aff,
            "org": aff,
        }
        out = fill_form_fields(pdf_bytes, field_map)
        if out:
            st.success("PDF가 생성되었습니다. (폼 채우기)")
            st.download_button(
                "PDF 다운로드",
                out,
                file_name="filled_%s.pdf" % datetime.now().strftime("%Y%m%d_%H%M%S"),
                mime="application/pdf",
            )
    else:
        out = overlay_text(
            pdf_bytes,
            name, aff,
            (name_x, name_y), (aff_x, aff_y),
            fontsize,
            font_path,
            all_pages,
        )
        st.success("PDF가 생성되었습니다. (좌표 덧씌우기)")
        st.download_button(
            "PDF 다운로드",
            out,
            file_name="personalized_%s.pdf" % datetime.now().strftime("%Y%m%d_%H%M%S"),
            mime="application/pdf",
        )
