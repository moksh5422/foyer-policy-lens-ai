import os
from pathlib import Path
import streamlit as st
from app.pipeline import PolicyLensPipeline

st.set_page_config(page_title="Policy Lens AI", page_icon="🛡️", layout="wide")
st.title("🛡️ Policy Lens AI")
st.caption("Evidence-first insurance policy assistant. Uses synthetic demo policies; not claims or legal advice.")

with st.sidebar:
    st.header("Policy documents")
    uploaded = st.file_uploader("Upload policy documents", type=["pdf", "docx", "xlsx", "pptx", "txt", "md"], accept_multiple_files=True)
    top_k = st.slider("Evidence chunks", 2, 8, 5)
    use_llm = st.checkbox("Use optional OpenAI reasoning", value=False)
    model = st.text_input("OpenAI model", value=os.getenv("OPENAI_MODEL", "gpt-4o-mini"))
    st.caption("Keep secrets out of uploads and never upload real customer data to this demo.")

if uploaded:
    # UploadedFile objects are handled in memory/temp storage by the ingestion layer.
    from app.ingestion import ingest_file, chunk_document
    docs = []
    for f in uploaded:
        docs.extend(ingest_file(f))
    from app.pipeline import PolicyLensPipeline
    pipeline = PolicyLensPipeline(chunk_document(docs))
else:
    demo_dir = Path("data/policies")
    pipeline = PolicyLensPipeline.from_paths([str(p) for p in sorted(demo_dir.iterdir()) if p.is_file()])

examples = [
    "Is accidental water damage caused by a burst pipe covered?",
    "Is damage caused by gradual seepage covered?",
    "Is a vehicle used in racing covered for collision damage?",
    "Is theft of a permanently installed home appliance covered?",
    "Is minor cosmetic damage automatically covered?",
    "Is damage caused by an earthquake covered?",
]
question = st.text_area("Ask a coverage question", value=examples[0], height=90)
if st.button("Assess coverage", type="primary"):
    result = pipeline.answer(question, top_k=top_k, use_llm=use_llm, model=model)
    left, right = st.columns([1, 3])
    left.metric("Decision", result.decision)
    right.metric("Evidence chunks", len(result.evidence))
    st.subheader("Assessment")
    st.write(result.summary)
    st.write(result.reasoning)
    if result.conditions:
        st.subheader("Conditions to verify")
        for item in result.conditions:
            st.write("• " + item)
    if result.exclusions:
        st.subheader("Relevant exclusions")
        for item in result.exclusions:
            st.write("• " + item)
    st.subheader("Evidence")
    for ev in result.evidence:
        with st.expander(f"{ev.source} · {ev.chunk_id} · score {ev.score:.3f}"):
            st.write(ev.text)
    st.subheader("Recommended next steps")
    for item in result.questions_for_claimant:
        st.write("• " + item)
    st.caption(result.disclaimer)

st.divider()
st.caption("Built as a portfolio demonstration. Outcomes should be reviewed by an appropriately qualified human before any real-world use.")
