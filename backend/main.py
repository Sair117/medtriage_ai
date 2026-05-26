"""FastAPI server with WebSocket chat endpoint."""

import json
import os
import sys
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from langchain_core.messages import HumanMessage, AIMessage

sys.path.insert(0, os.path.dirname(__file__))

from agent import build_graph, create_initial_state, GraphState
from models import ConversationPhase


sessions: dict[str, GraphState] = {}
graph = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global graph
    graph = build_graph()
    yield
    sessions.clear()


app = FastAPI(title="MedTriage AI", lifespan=lifespan)

FRONTEND_DIR = os.path.join(os.path.dirname(__file__), "..", "frontend")


@app.get("/health")
async def health():
    return {"status": "ok", "service": "MedTriage AI"}


def _extract_patient_info(message: str, state: GraphState) -> None:
    """Try to extract structured patient info from messages."""
    patient = state["patient"]
    msg_lower = message.lower()

    if not patient.get("name"):
        for prefix in ["my name is ", "i'm ", "i am ", "name: ", "name is "]:
            if prefix in msg_lower:
                idx = msg_lower.index(prefix) + len(prefix)
                name_part = message[idx:].split(",")[0].split(".")[0].split("\n")[0].strip()
                if 1 < len(name_part) < 50:
                    patient["name"] = name_part.title()
                    break

    if not patient.get("age"):
        import re
        age_match = re.search(r"\b(\d{1,3})\s*(?:years?\s*old|yrs?\s*old|yo|y/o|y\.o\.)\b", msg_lower)
        if age_match:
            age = int(age_match.group(1))
            if 0 < age < 150:
                patient["age"] = age
        else:
            age_match = re.search(r"\bage\s*(?:is\s*)?(\d{1,3})\b", msg_lower)
            if age_match:
                age = int(age_match.group(1))
                if 0 < age < 150:
                    patient["age"] = age

    for keyword in ["no allergies", "none", "no known allergies", "nka", "nkda"]:
        if keyword in msg_lower and not patient.get("allergies"):
            patient["allergies"] = "No known allergies"
            break
    if not patient.get("allergies"):
        for prefix in ["allergic to ", "allergy to ", "allergies: "]:
            if prefix in msg_lower:
                idx = msg_lower.index(prefix) + len(prefix)
                allergy_part = message[idx:].split(".")[0].split("\n")[0].strip()
                if allergy_part:
                    patient["allergies"] = allergy_part
                break

    for keyword in ["no medications", "no meds", "not taking any", "none"]:
        if keyword in msg_lower and not patient.get("current_medications"):
            patient["current_medications"] = "None"
            break
    for prefix in ["taking ", "medications: ", "meds: ", "i take "]:
        if prefix in msg_lower and not patient.get("current_medications"):
            idx = msg_lower.index(prefix) + len(prefix)
            med_part = message[idx:].split(".")[0].split("\n")[0].strip()
            if med_part and len(med_part) > 2:
                patient["current_medications"] = med_part
            break

    state["patient"] = patient


async def _run_agent_step(state: GraphState, user_message: str | None = None) -> tuple[str, GraphState]:
    """Run one step of the agent graph."""
    if user_message:
        state["messages"].append(HumanMessage(content=user_message))
        _extract_patient_info(user_message, state)

    phase = state["phase"]

    if phase == ConversationPhase.GREETING.value:
        from agent import greeting_node
        state = greeting_node(state)
    elif phase == ConversationPhase.SYMPTOM_COLLECTION.value:
        from agent import symptom_collection_node, should_assess_urgency
        state = symptom_collection_node(state)
        next_step = should_assess_urgency(state)
        if next_step == "urgency_assessment":
            from agent import urgency_assessment_node, after_urgency
            state = urgency_assessment_node(state)
            next_step2 = after_urgency(state)
            if next_step2 == "escalation":
                from agent import escalation_node
                state = escalation_node(state)
            else:
                state["phase"] = ConversationPhase.INFO_GATHERING.value
    elif phase == ConversationPhase.INFO_GATHERING.value:
        from agent import info_gathering_node, should_classify
        state = info_gathering_node(state)
        next_step = should_classify(state)
        if next_step == "classification":
            from agent import classification_node, routing_node
            state = classification_node(state)
            state = routing_node(state)
    elif phase == ConversationPhase.ESCALATION.value:
        from agent import escalation_node
        state = escalation_node(state)
    elif phase == ConversationPhase.COMPLETE.value:
        state["latest_response"] = "Your triage is complete. A staff member will assist you shortly. If your condition changes, please let us know."

    return state["latest_response"], state


@app.websocket("/ws/chat")
async def chat_ws(websocket: WebSocket):
    await websocket.accept()
    session_id = str(uuid.uuid4())
    state = create_initial_state()
    sessions[session_id] = state

    try:
        greeting, state = await _run_agent_step(state)
        sessions[session_id] = state
        await websocket.send_json({
            "type": "message",
            "content": greeting,
            "phase": state["phase"],
        })

        while True:
            data = await websocket.receive_json()
            user_msg = data.get("message", "").strip()
            if not user_msg:
                continue

            response, state = await _run_agent_step(state, user_msg)
            sessions[session_id] = state

            payload = {
                "type": "message",
                "content": response,
                "phase": state["phase"],
            }

            if state["phase"] == ConversationPhase.COMPLETE.value:
                payload["type"] = "triage_complete"
                payload["triage"] = state["triage"]
                payload["patient"] = state["patient"]

            await websocket.send_json(payload)

    except WebSocketDisconnect:
        sessions.pop(session_id, None)
    except Exception as e:
        try:
            await websocket.send_json({"type": "error", "content": f"Something went wrong: {str(e)}"})
        except:
            pass
        sessions.pop(session_id, None)


app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")
