import random
import socketio
from fastapi import FastAPI
from fastapi.templating import Jinja2Templates
from starlette.requests import Request

sio = socketio.AsyncServer(async_mode="asgi", cors_allowed_origins="*")
app = FastAPI()
templates = Jinja2Templates(directory="templates")
socket_app = socketio.ASGIApp(sio, app)

rooms = {}

def crear_mazo():
    palos = ["oros", "copas", "espadas", "bastos"]
    numeros = [1, 2, 3, 4, 5, 6, 7, 10, 11, 12]
    mazo = [{"palo": p, "numero": n} for p in palos for n in numeros]
    random.shuffle(mazo)
    return mazo

@app.get("/")
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@sio.event
async def join_room(sid, data):
    room = data.get("room")
    name = data.get("name", "Jugador")
    sio.enter_room(sid, room)
    if room not in rooms:
        rooms[room] = {"players": [], "deck": [], "hands": {}}
    rooms[room]["players"].append({"sid": sid, "name": name})
    await sio.emit("update_lobby", {"players": [p["name"] for p in rooms[room]["players"]]}, room=room)

@sio.event
async def start_game(sid, data):
    room = data.get("room")
    game_data = rooms.get(room)
    if not game_data:
        return
    num_players = len(game_data["players"])
    
    cartas_por_jugador = 13 if num_players == 3 else (10 if num_players == 4 else 8)
    deck = crear_mazo()
    game_data["hands"] = {}

    for player in game_data["players"]:
        mano = [deck.pop() for _ in range(cartas_por_jugador)]
        game_data["hands"][player["sid"]] = mano
        await sio.emit("game_started", {"hand": mano}, room=player["sid"])

    triunfo = deck.pop()
    await sio.emit("info_partida", {"triunfo": triunfo}, room=room)

@sio.event
async def disconnect(sid):
    for room, data in rooms.items():
        data["players"] = [p for p in data["players"] if p["sid"] != sid]
        await sio.emit("update_lobby", {"players": [p["name"] for p in data["players"]]}, room=room)

app = socket_app
