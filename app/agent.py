
import os
from typing import Literal

from pydantic import BaseModel, Field
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.tools import tool
from langchain_ollama import ChatOllama
from langchain.agents import AgentExecutor, create_tool_calling_agent

from app import analytics


class MonthComparison(BaseModel):
    month_a: str = Field(
        description="First month in YYYY-MM format, for example 2026-01"
    )
    month_b: str = Field(
        description="Second month in YYYY-MM format, for example 2026-02"
    )


@tool
def get_total_revenue() -> dict:
    """Calculate total net revenue across valid completed sales."""
    return analytics.total_revenue()


@tool
def get_top_product() -> dict:
    """Find the product generating the highest net revenue."""
    return analytics.top_product()


@tool
def get_monthly_revenue_trend() -> dict:
    """Return net revenue grouped by month, in chronological order."""
    return analytics.monthly_trend()


@tool
def get_top_region() -> dict:
    """Find the region generating the highest net revenue."""
    return analytics.top_region()


@tool(args_schema=MonthComparison)
def compare_monthly_revenue(month_a: str, month_b: str) -> dict:
    """Compare net revenue between two months formatted as YYYY-MM."""
    import re

    pattern = r"^20\d{2}-(0[1-9]|1[0-2])$"

    if not re.fullmatch(pattern, month_a):
        return {"error": "month_a must use YYYY-MM format."}

    if not re.fullmatch(pattern, month_b):
        return {"error": "month_b must use YYYY-MM format."}

    return analytics.compare_months(month_a, month_b)


@tool
def get_data_quality_report() -> dict:
    """Report included and excluded records and their exclusion reasons."""
    return analytics.data_quality()

@tool
def get_top_channel() -> dict:
    """Find the sales channel used for the greatest number of included transactions."""
    return analytics.top_sales_channel()


TOOLS = [
    get_total_revenue,
    get_top_product,
    get_monthly_revenue_trend,
    get_top_region,
    compare_monthly_revenue,
    get_data_quality_report,
    get_top_channel,
]

llm = ChatOllama(
    model=os.getenv("OLLAMA_MODEL", "llama3.2"),
    base_url=os.getenv(
        "OLLAMA_BASE_URL",
        "http://host.docker.internal:11434",
    ),
    temperature=0,
    client_kwargs={"timeout": 180.0},
)

prompt = ChatPromptTemplate.from_messages([
    (
        "system",
        
"""
You are a sales business intelligence agent.

You MUST call at least one analytics tool for every question
that asks about actual sales figures, revenue, products, regions,
monthly trends, or comparisons.

Never answer numerical questions from memory or guesswork.

For every question about sales data, you must call the relevant
analytics tool before answering. Never describe a tool call as text.
Only report results returned by the tool.

For questions mentioning "last month", "previous month",
"month-over-month", or "percentage increase from last month's sales":
1. Call get_monthly_revenue_trend.
2. Identify the latest two months returned by the tool.
3. Compare the latest month against the immediately preceding month.
4. Report both revenue values, the absolute change, and percentage change.
5. If fewer than two months are available, explain that more data is needed.

Use only analytics tool results.
Do not invent causes for revenue changes.
Never execute or generate SQL.
"""


    ),
    MessagesPlaceholder(variable_name="chat_history", optional=True),
    ("human", "{input}"),
    MessagesPlaceholder(variable_name="agent_scratchpad"),
])

agent = create_tool_calling_agent(llm, TOOLS, prompt)

agent_executor = AgentExecutor(
    agent=agent,
    tools=TOOLS,
    verbose=True,
    max_iterations=5,
    handle_parsing_errors=True,
)


def answer_question(question, db_path=None):
    result = agent_executor.invoke({"input": question})

    return {
        "intent": "agent_response",
        "answer": result["output"],
        "agent": "langchain-tool-calling",
        "model": os.getenv("OLLAMA_MODEL", "llama3.2"),
        "intermediate_steps": [
            {
                "tool": action.tool,
                "input": action.tool_input,
                "output": str(observation),
            }
            for action, observation in result.get("intermediate_steps", [])
        ],
    }
