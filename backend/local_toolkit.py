from langchain.tools import BaseTool
from typing import List
from search import create_index, search_documents
from ocr import run_ocr

def fetch_newspaper_text(agent_query):
    documents = create_index('tests/data')
    results = search_documents(agent_query, documents, top_k=1)
    total_str = ""
    for result in results:
        result_str = run_ocr(result.path)
        total_str = total_str + " " + result_str
    return total_str

# Proper subclass with type annotations
class LocalProcessorTool(BaseTool):
    name: str = "LocalProcessor"
    description: str = (
        "Use this tool to search a local collection of documents. "
        "Input a prompt/request in sentence form, and it returns relevant information in text form."
    )

    def _run(self, agent_query: str) -> str:
        return fetch_newspaper_text(agent_query)

    async def _arun(self, agent_query: str) -> str:
        raise NotImplementedError("Async version not implemented")

class LocalToolkit:
    def __init__(self):
        self.tools: List[BaseTool] = [LocalProcessorTool()]

    def get_tools(self) -> List[BaseTool]:
        return self.tools
