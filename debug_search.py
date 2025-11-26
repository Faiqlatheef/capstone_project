from src.tool_adapter import simple_search
import json
print(json.dumps(simple_search("Recent breakthroughs in India"), indent=2, ensure_ascii=False))
print("---")
print(json.dumps(simple_search("Recent breakthroughs in Canada"), indent=2, ensure_ascii=False))
