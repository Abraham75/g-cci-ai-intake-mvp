import time, uuid
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from schemas import IntakeRequest, LeadResponse
from store import STORE
from engine import route_submodel, score_truck, score_non_truck
from explain import build_explain

app = FastAPI(title="G-CCI AI Intake MVP")

app.mount("/static", StaticFiles(directory="static"), name="static")

clients = set()

@app.get("/")
def index():
    return FileResponse("static/GCCI v5.index.htm")

@app.websocket("/ws")
async def ws(ws: WebSocket):
    await ws.accept()
    clients.add(ws)
    try:
        while True:
            await ws.receive_text()
    except WebSocketDisconnect:
        clients.remove(ws)

async def broadcast(msg):
    for c in list(clients):
        try:
            await c.send_json(msg)
        except:
            clients.remove(c)

@app.post("/api/intake", response_model=LeadResponse)
async def intake(data: IntakeRequest):
    model_path = route_submodel(data.incident_type)

    if model_path == "TRUCK_SUBMODEL":
        score, conf, value = score_truck(data)
    else:
        score, conf, value = score_non_truck(data)

    explain = build_explain(data, model_path, score)

    lead_id = str(uuid.uuid4())
    lead = LeadResponse(
        lead_id=lead_id,
        created_ts=int(time.time() * 1000),
        model_path=model_path,
        lead_score=score,
        confidence=conf,
        expected_value_range=value,
        mycase_file=f"#CASE-{lead_id[:6]}",
        intake=data.model_dump(),
        explain=explain
    ).model_dump()

    STORE.add_lead(lead_id, lead)
    await broadcast({"type": "LEAD", "payload": lead})

    if model_path == "TRUCK_SUBMODEL" and score >= 85:
        alert = {"level": "CRITICAL", "message": "Elite Truck Case Detected"}
        STORE.add_alert(alert)
        await broadcast({"type": "ALERT", "payload": alert})

    return lead
