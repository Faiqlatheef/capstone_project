# AI Research By Faiq — Capstone
**Use case:** Multi-agent research pipeline combining search, summarization, critique, drafting, memory, observability, and deployment guidance.

## How to run
1. Open `notebooks/03_Final_Project.ipynb` in Kaggle or locally.
2. By default the notebook runs in mock/dry-run mode (`USE_MOCK=True`). This does not require API keys.
3. To enable real APIs, set `USE_MOCK=False` and configure your secrets per instructions in this repo.
4. If You need to run fully UI site use this steps
   1. python -m venv .venv
   2. .venv\Scripts\activate.bat
   3. pip install -r requirements.txt
   4. streamlit run ui/app.py

## Deliverables
- `notebooks/03_Final_Project.ipynb` — final polished notebook
- `src/` — modules used by the notebook (agents, orchestrator, tools, memory, observability, etc.)
- `reports/evaluation_report.md` — evaluation and scoring
- `slides/presentation.md` — slide deck outline

## Why this project is judge-friendly
- Demonstrates all major topics from the 5-day course.
- Includes observability & evaluation pipeline (mock LLM-as-a-Judge included).
- Productionization notes and Vertex deployment instructions included.

## Notes
- This capstone is auto-generated from your course notebooks. Review and expand sections with real APIs and richer prompts for a competitive submission.
