from mcp.server.mcpserver import MCPServer
import json
import httpx as httpx

from pathlib import Path

NOTES_PATH = Path(__file__).parent / "notes.json"

with open(NOTES_PATH, "r") as f:
    notes = json.load(f)


def save_notes() -> None:
    with open(NOTES_PATH, "w") as f:
        json.dump(notes, f, indent=4)


mcp = MCPServer(name="notes-server", version="1.0.0", description="Notes MCP Server")


@mcp.tool()
def search_notes(query: str) -> dict:
    return {title: note for title, note in notes.items() if query in title}


@mcp.tool()
def add_note(title: str, note: str) -> str:
    notes[title] = note
    save_notes()
    return "Note added successfully"


@mcp.tool()
def update_note(note: str, new_note: str) -> str:
    notes[note] = new_note
    save_notes()
    return "Note updated successfully"

@mcp.tool()
def delete_note(note: str) -> str:
    notes.pop(note)
    save_notes()
    return "Note deleted successfully"

@mcp.tool()
def get_all_notes() -> dict:
    return notes


@mcp.tool()
def get_weather(location: str) -> dict:
    url = f"https://geocoding-api.open-meteo.com/v1/search?name={location}"
    (longitude, latitude) = get_coordinates(url)
    url = f"https://api.open-meteo.com/v1/forecast?latitude={latitude}&longitude={longitude}&current_weather=true"
    response = httpx.get(url)
    data = response.json()
    return data


def get_coordinates(url: str) -> tuple[float, float]:
    response = httpx.get(url)
    data = response.json()
    return data["results"][0]["longitude"], data["results"][0]["latitude"]


# Resource returns all notes as string
@mcp.resource("notes://all")
def notes_resource() -> str:
    return "\n".join([f"{title}: {note}" for title, note in notes.items()])

# Prompt template: plan a productive day.
@mcp.prompt()
def plan_my_day(city: str) -> str:
    return f"Plan my day in {city}. Use get_weather + notes://all..."


if __name__ == "__main__":
    mcp.run(
        transport="streamable-http",
        host="0.0.0.0",
        port=8000,
    )