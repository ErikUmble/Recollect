# sql_agent_openrouter_latest.py

import os
from dotenv import load_dotenv

# LangChain imports
from langchain_openai import ChatOpenAI
from langchain.agents import create_agent
from langchain_core.messages import HumanMessage

from local_toolkit import LocalToolkit

# Load environment variables
load_dotenv()
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
if not OPENROUTER_API_KEY:
    raise ValueError("Set OPENROUTER_API_KEY in your environment")

# Build the agent
def build_agent():

    print("STARTED BUILDING AGENT!")
    # LLM using OpenRouter
    llm = ChatOpenAI(
        model="openai/gpt-3.5-turbo",
        temperature=0,
        streaming=False,
        openai_api_key=OPENROUTER_API_KEY,
        base_url="https://openrouter.ai/api/v1"
    )

    # Create Local Toolkit
    toolkit = LocalToolkit()
    tools = toolkit.get_tools()

    tools_str = "\n".join([f"{tool.name}: {tool.description}" for tool in tools])

    system_prompt_str = f"""
        You are a research assistant and summarization agent. Your goal is to provide 
        clear, accurate, and concise summaries of historical newspaper content in 
        response to user queries.

        You have the following tool(s) available to you to achieve your goal:
        {tools_str}
        """

    # Create agent
    agent = create_agent(
        llm,
        tools,
        system_prompt=system_prompt_str
    )

    print("FINISHED BUILDING AGENT!")
    return agent

def main():

    agent = build_agent()

    # User question as HumanMessage
    user_question = HumanMessage(content="What do you know about Dr. Graves?")

    # Invoke the agent
    result = agent.invoke({"messages": [user_question]})
    print("Agent result:", result)

if __name__ == "__main__":
    main()