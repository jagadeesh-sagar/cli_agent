import os
from tavily import TavilyClient

def web_search(query: str) -> str:
    client = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))
    results = client.search(query, max_results=3)
    return "\n\n".join(
        f"**{r['title']}**\n{r['content']}" 
        for r in results["results"]
    )

