import os, sys
proj = r'C:\Users\HEALTHY MACHINES\OneDrive\Desktop\capstone_project_package'
if proj not in sys.path:
    sys.path.insert(0, proj)
    sys.path.insert(0, proj + "/src")

from src.tool_adapter import simple_search, Tool
from src.agents import ResearchAgent

# 1) Check environment
print("GOOGLE_API_KEY:", bool(os.environ.get("GOOGLE_API_KEY")))
print("GOOGLE_CX:", bool(os.environ.get("GOOGLE_CX") or os.environ.get("CUSTOM_SEARCH_CX")))

# 2) Test search adapter directly with a query you used
q1 = "Recent breakthroughs in quantum computing and impact on AI (2024–2025)"
res1 = simple_search(q1)
print("simple_search result source:", res1.get("source"))
print("hits count:", len(res1.get("hits", [])))
if res1.get("hits"):
    print("first hit:", res1["hits"][0])

# 3) Test ResearchAgent in real mode (use_mock=False) with the Tool wrapper
tool = Tool("web_search", simple_search)
agent = ResearchAgent("ResearchAgent", tools={"search": tool}, use_mock=False)
out = agent.act(q1)
print("ResearchAgent output (use_mock=False):")
print(out)

# 4) Now test a different query
q2 = "Recent breakthroughs in America"
out2 = agent.act(q2)
print("ResearchAgent output for second query:")
print(out2)
