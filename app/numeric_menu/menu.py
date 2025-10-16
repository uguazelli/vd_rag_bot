from pathlib import Path
from typing import Dict, Any, Tuple
import json

# Load menus.json (must be in the same folder as menu.py)
MENU_TREE: Dict[str, Any] = json.loads(
    Path(__file__).with_name("menus.json").read_text(encoding="utf-8")
)

# -------------------------------
# Mini engine
# -------------------------------
def initial_state() -> Dict[str, Any]:
    return {"current": "root"}

def _render(node_id: str) -> str:
    return MENU_TREE["nodes"][node_id].get("text", "")

def _is_handoff(text: str) -> bool:
    t = (text or "").strip().lower()
    return any(k in t for k in MENU_TREE["meta"]["handoff_keywords"])

def _is_menu_alias(text: str) -> bool:
    t = (text or "").strip().lower()
    return t in MENU_TREE["meta"]["aliases_menu"]

def _is_back_alias(text: str) -> bool:
    t = (text or "").strip().lower()
    return t in MENU_TREE["meta"]["aliases_back"]

def _options_for(node_id: str) -> Dict[str, str]:
    node = MENU_TREE["nodes"][node_id]
    if node.get("type") != "menu":
        return {}
    return {opt["key"]: opt["goto"] for opt in node.get("options", [])}

def handle_input(state: Dict[str, Any], text: str) -> Tuple[Dict[str, Any], str, str]:
    # Global shortcuts
    if _is_handoff(text):
        state["current"] = "handoff"
        return state, _render("handoff"), "handoff"
    if _is_menu_alias(text) or _is_back_alias(text):
        state["current"] = "root"
        return state, _render("root"), "ok"

    current = state.get("current", "root")
    node = MENU_TREE["nodes"].get(current, MENU_TREE["nodes"]["root"])

    if node.get("type") == "menu":
        key = (text or "").strip()
        goto = _options_for(current).get(key)
        if goto and goto in MENU_TREE["nodes"]:
            state["current"] = goto
            tgt = MENU_TREE["nodes"][goto]
            if tgt.get("type") == "handoff":
                return state, tgt.get("text", ""), "handoff"
            return state, tgt.get("text", ""), "ok"
        return state, node.get("text", ""), "ok"  # Invalid option: repeat menu

    if node.get("type") == "message":
        if (text or "").strip() == "0" or _is_handoff(text):
            state["current"] = "handoff"
            return state, _render("handoff"), "handoff"
        if _is_menu_alias(text) or _is_back_alias(text):
            state["current"] = "root"
            return state, _render("root"), "ok"
        return state, node.get("text", ""), "ok"  # Invalid input: repeat message

    # Already in handoff
    return state, node.get("text", ""), "handoff"
