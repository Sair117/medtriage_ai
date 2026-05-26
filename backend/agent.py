"""LangGraph-based triage agent with dual-model strategy and RAG."""

import json
import os
from typing import TypedDict, Literal

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langgraph.graph import StateGraph, END

from config import (
    GOOGLE_API_KEY, CHAT_MODEL, REASONING_MODEL,
    TEMPERATURE_CHAT, TEMPERATURE_REASONING,
)
from models import Urgency, ConversationPhase
from prompts import SYSTEM_PROMPT, URGENCY_ASSESSMENT_PROMPT, ROUTING_PROMPT, SUMMARY_PROMPT
from rag import retrieve_context

os.environ["GOOGLE_API_KEY"] = GOOGLE_API_KEY


class GraphState(TypedDict):
    messages: list
    phase: str
    patient: dict
    triage: dict
    turn_count: int
    needs_escalation: bool
    rag_context: str
    latest_response: str


def get_chat_llm():
    return ChatGoogleGenerativeAI(model=CHAT_MODEL, temperature=TEMPERATURE_CHAT)


def get_reasoning_llm():
    return ChatGoogleGenerativeAI(model=REASONING_MODEL, temperature=TEMPERATURE_REASONING)


def _get_conversation_text(state: GraphState) -> str:
    parts = []
    for msg in state["messages"]:
        if isinstance(msg, HumanMessage):
            parts.append(f"Patient: {msg.content}")
        elif isinstance(msg, AIMessage):
            parts.append(f"Bot: {msg.content}")
    return "\n".join(parts[-10:])


def _get_patient_symptoms_text(state: GraphState) -> str:
    parts = []
    for msg in state["messages"]:
        if isinstance(msg, HumanMessage):
            parts.append(msg.content)
    return " | ".join(parts[-6:])


def _parse_json(text: str) -> dict:
    text = text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[-1].rsplit("```", 1)[0]
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}") + 1
        if start != -1 and end > start:
            try:
                return json.loads(text[start:end])
            except json.JSONDecodeError:
                pass
    return {}


# --- Graph nodes ---

def greeting_node(state: GraphState) -> GraphState:
    llm = get_chat_llm()
    msgs = [
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content="A new patient has connected. Greet them warmly and ask what brings them in today. Keep it to 2 sentences."),
    ]
    response = llm.invoke(msgs)
    state["messages"].append(AIMessage(content=response.content))
    state["phase"] = ConversationPhase.SYMPTOM_COLLECTION.value
    state["latest_response"] = response.content
    return state


def symptom_collection_node(state: GraphState) -> GraphState:
    symptoms_text = _get_patient_symptoms_text(state)
    rag_ctx = retrieve_context(symptoms_text)
    state["rag_context"] = rag_ctx

    llm = get_chat_llm()
    msgs = [SystemMessage(content=SYSTEM_PROMPT)]
    if rag_ctx:
        msgs.append(SystemMessage(content=f"Relevant medical knowledge for reference:\n{rag_ctx}"))
    msgs.extend(state["messages"])

    if state["turn_count"] >= 2:
        msgs.append(SystemMessage(content="You should have a reasonable picture of symptoms by now. Ask 1-2 final clarifying questions about severity or duration if needed, then transition to collecting personal details."))
    else:
        msgs.append(SystemMessage(content="Ask focused follow-up questions about the symptoms: location, severity (1-10), duration, what makes it better/worse. Ask 1-2 questions at a time."))

    response = llm.invoke(msgs)
    state["messages"].append(AIMessage(content=response.content))
    state["turn_count"] += 1
    state["latest_response"] = response.content
    return state


def urgency_assessment_node(state: GraphState) -> GraphState:
    symptoms_text = _get_patient_symptoms_text(state)
    rag_ctx = retrieve_context(symptoms_text)
    state["rag_context"] = rag_ctx

    llm = get_reasoning_llm()
    prompt = URGENCY_ASSESSMENT_PROMPT.format(
        symptoms_summary=symptoms_text,
        rag_context=rag_ctx or "No specific guidelines retrieved.",
    )
    response = llm.invoke([HumanMessage(content=prompt)])
    result = _parse_json(response.content)

    triage = state["triage"]
    urgency_str = result.get("urgency", "routine").lower()
    if urgency_str in ("emergency", "urgent", "routine"):
        triage["urgency"] = urgency_str
    else:
        triage["urgency"] = "routine"

    triage["red_flags"] = result.get("red_flags", [])
    state["triage"] = triage
    state["needs_escalation"] = result.get("needs_escalation", False)

    if urgency_str == "emergency" and result.get("needs_escalation", False):
        state["phase"] = ConversationPhase.ESCALATION.value
        state["needs_escalation"] = True
    else:
        state["phase"] = ConversationPhase.INFO_GATHERING.value

    return state


def info_gathering_node(state: GraphState) -> GraphState:
    patient = state["patient"]
    missing = []
    if not patient.get("name"):
        missing.append("name")
    if not patient.get("age"):
        missing.append("age")
    if not patient.get("allergies"):
        missing.append("any allergies")
    if not patient.get("current_medications"):
        missing.append("current medications")

    llm = get_chat_llm()
    msgs = [SystemMessage(content=SYSTEM_PROMPT)]
    msgs.extend(state["messages"])

    if missing:
        fields = ", ".join(missing)
        msgs.append(SystemMessage(content=f"Now collect the patient's personal details. Still needed: {fields}. Ask naturally, 1-2 items at a time. Be brief."))
    else:
        msgs.append(SystemMessage(content="You have all needed info. Let the patient know you're preparing their triage summary and routing them. Keep it to 1-2 sentences."))
        state["phase"] = ConversationPhase.CLASSIFICATION.value

    response = llm.invoke(msgs)
    state["messages"].append(AIMessage(content=response.content))
    state["turn_count"] += 1
    state["latest_response"] = response.content
    return state


def classification_node(state: GraphState) -> GraphState:
    symptoms_text = _get_patient_symptoms_text(state)
    rag_ctx = retrieve_context(symptoms_text + " department")

    patient = state["patient"]
    llm = get_reasoning_llm()
    prompt = ROUTING_PROMPT.format(
        symptoms=symptoms_text,
        duration=patient.get("symptom_duration", "not specified"),
        urgency=state["triage"].get("urgency", "routine"),
        rag_context=rag_ctx or "No specific protocols retrieved.",
    )
    response = llm.invoke([HumanMessage(content=prompt)])
    result = _parse_json(response.content)

    triage = state["triage"]
    triage["department"] = result.get("department", "General Practice")
    triage["chief_complaint"] = result.get("chief_complaint", "See conversation notes")
    state["triage"] = triage
    state["phase"] = ConversationPhase.ROUTING.value
    return state


def routing_node(state: GraphState) -> GraphState:
    patient = state["patient"]
    triage = state["triage"]
    conversation_text = _get_conversation_text(state)
    rag_ctx = state.get("rag_context", "")

    llm = get_reasoning_llm()
    prompt = SUMMARY_PROMPT.format(
        name=patient.get("name", "Not provided"),
        age=patient.get("age", "Not provided"),
        gender=patient.get("gender", "Not provided"),
        symptoms=_get_patient_symptoms_text(state),
        duration=patient.get("symptom_duration", "Not specified"),
        allergies=patient.get("allergies", "None reported"),
        medications=patient.get("current_medications", "None reported"),
        medical_history=patient.get("medical_history", "None reported"),
        urgency=triage.get("urgency", "routine"),
        department=triage.get("department", "General Practice"),
        conversation_summary=conversation_text,
        rag_context=rag_ctx or "None.",
    )
    response = llm.invoke([HumanMessage(content=prompt)])
    result = _parse_json(response.content)

    triage["summary"] = result.get("summary", "Patient triaged based on reported symptoms.")
    triage["recommendations"] = result.get("recommendations", "Standard intake protocol.")
    state["triage"] = triage

    dept = triage.get("department", "General Practice")
    urgency = triage.get("urgency", "routine")

    llm_chat = get_chat_llm()
    msgs = [SystemMessage(content=SYSTEM_PROMPT)]
    msgs.extend(state["messages"])
    msgs.append(SystemMessage(content=f"The patient has been triaged as '{urgency}' priority and will be routed to the {dept} department. Inform them briefly and reassuringly. Keep it to 2 sentences."))
    final = llm_chat.invoke(msgs)

    state["messages"].append(AIMessage(content=final.content))
    state["latest_response"] = final.content
    state["phase"] = ConversationPhase.COMPLETE.value
    return state


def escalation_node(state: GraphState) -> GraphState:
    triage = state["triage"]
    triage["urgency"] = Urgency.EMERGENCY.value
    triage["department"] = "Emergency Medicine"
    triage["escalation_reason"] = "Red flag symptoms detected — requires immediate human attention"
    state["triage"] = triage

    llm = get_chat_llm()
    msgs = [SystemMessage(content=SYSTEM_PROMPT)]
    msgs.extend(state["messages"])
    msgs.append(SystemMessage(content="EMERGENCY DETECTED. Calmly but clearly tell the patient their symptoms need immediate medical attention. If not at the clinic, advise calling emergency services or going to the nearest ER. Be empathetic but urgent. Keep it to 3 sentences."))
    response = llm.invoke(msgs)

    state["messages"].append(AIMessage(content=response.content))
    state["latest_response"] = response.content
    state["phase"] = ConversationPhase.COMPLETE.value
    return state


# --- Routing logic ---

def should_assess_urgency(state: GraphState) -> Literal["urgency_assessment", "symptom_collection"]:
    if state["turn_count"] >= 4:
        return "urgency_assessment"

    last_ai = None
    for msg in reversed(state["messages"]):
        if isinstance(msg, AIMessage):
            last_ai = msg.content.lower()
            break

    if last_ai and any(phrase in last_ai for phrase in [
        "personal details", "personal information", "let me collect",
        "i'd like to get some details", "could you tell me your name",
        "your name", "how old are you",
    ]):
        return "urgency_assessment"

    return "symptom_collection"


def after_urgency(state: GraphState) -> Literal["escalation", "info_gathering"]:
    if state.get("needs_escalation"):
        return "escalation"
    return "info_gathering"


def should_classify(state: GraphState) -> Literal["classification", "info_gathering"]:
    if state["phase"] == ConversationPhase.CLASSIFICATION.value:
        return "classification"
    return "info_gathering"


# --- Build the graph ---

def build_graph():
    graph = StateGraph(GraphState)

    graph.add_node("greeting", greeting_node)
    graph.add_node("symptom_collection", symptom_collection_node)
    graph.add_node("urgency_assessment", urgency_assessment_node)
    graph.add_node("info_gathering", info_gathering_node)
    graph.add_node("classification", classification_node)
    graph.add_node("routing", routing_node)
    graph.add_node("escalation", escalation_node)

    graph.set_entry_point("greeting")
    graph.add_edge("greeting", "symptom_collection")
    graph.add_conditional_edges("symptom_collection", should_assess_urgency)
    graph.add_conditional_edges("urgency_assessment", after_urgency)
    graph.add_conditional_edges("info_gathering", should_classify)
    graph.add_edge("classification", "routing")
    graph.add_edge("routing", END)
    graph.add_edge("escalation", END)

    return graph.compile()


def create_initial_state() -> GraphState:
    return {
        "messages": [],
        "phase": ConversationPhase.GREETING.value,
        "patient": {},
        "triage": {},
        "turn_count": 0,
        "needs_escalation": False,
        "rag_context": "",
        "latest_response": "",
    }
