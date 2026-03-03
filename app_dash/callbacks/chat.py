"""Chat callbacks — 发送消息、流式更新、药丸点击"""

import threading
import uuid
from typing import Any, Callable, Dict, List

import dash
from dash import Input, Output, State, ctx, no_update
from dash.exceptions import PreventUpdate

from pfa.ai_chat import (
    build_system_prompt,
    build_welcome_message,
    call_ai_stream,
    execute_trade_payload,
    parse_trade_command,
)
from pfa.data.store import load_chat_history, save_chat_history
from app_dash.components.chat import CHIPS, render_message

# Thread-safe buffer for streaming: {request_id: {"text": str, "done": bool}}
_stream_buffer: Dict[str, Dict[str, Any]] = {}
_stream_lock = threading.Lock()


def _run_stream(request_id: str, messages: List[Dict], user_id: str) -> None:
    """Background thread: run AI stream and write to buffer."""
    try:
        full = ""
        for chunk in call_ai_stream(messages):
            full += chunk
            with _stream_lock:
                if request_id in _stream_buffer:
                    _stream_buffer[request_id]["text"] = full
        with _stream_lock:
            if request_id in _stream_buffer:
                _stream_buffer[request_id]["done"] = True
    except Exception:
        with _stream_lock:
            if request_id in _stream_buffer:
                _stream_buffer[request_id]["text"] = "AI 服务暂不可用"
                _stream_buffer[request_id]["done"] = True


def register_chat_callbacks(app: dash.Dash, get_holdings_val_fn: Callable[[], dict]):
    """Register chat-related callbacks. get_holdings_val_fn returns valuation dict."""

    @app.callback(
        Output("chat-messages", "children"),
        Input("chat-messages-store", "data"),
    )
    def _render_messages(messages_data):
        """Render message list from store."""
        if not messages_data:
            return []
        return [render_message(m.get("role", "assistant"), m.get("content", "")) for m in messages_data]

    @app.callback(
        Output("chat-messages-store", "data"),
        Output("chat-stream-store", "data"),
        Output("chat-current-stream", "style"),
        Output("chat-stream-bubble", "children"),
        Output("chat-input", "value"),
        Input("chat-send", "n_clicks"),
        Input("chat-input", "n_submit"),
        Input({"type": "chat-chip", "index": dash.ALL}, "n_clicks"),
        Input("chat-stream-interval", "n_intervals"),
        State("chat-input", "value"),
        State("chat-messages-store", "data"),
        State("chat-user-id-store", "data"),
        State("chat-stream-store", "data"),
        prevent_initial_call=True,
    )
    def _chat_callback(
        send_clicks,
        n_submit,
        chip_clicks,
        n_interval,
        input_value,
        messages_data,
        user_id,
        stream_request_id,
    ):
        user_id = user_id or "admin"
        messages: List[Dict] = list(messages_data) if messages_data else []

        # Interval: poll stream buffer
        if ctx.triggered_id == "chat-stream-interval":
            if stream_request_id:
                with _stream_lock:
                    buf = _stream_buffer.get(stream_request_id)
                if buf:
                    text = buf.get("text", "")
                    done = buf.get("done", False)
                    if done:
                        messages.append({"role": "assistant", "content": text})
                        save_chat_history(messages, user_id)
                        with _stream_lock:
                            _stream_buffer.pop(stream_request_id, None)
                        return messages, "", {"display": "none"}, "", no_update
                    return no_update, stream_request_id, {"display": "flex"}, text, no_update
            raise PreventUpdate

        # Chip click: use chip prompt as input
        triggered = ctx.triggered_id
        if isinstance(triggered, dict) and triggered.get("type") == "chat-chip":
            idx = triggered.get("index", 0)
            if idx < len(CHIPS):
                input_value = CHIPS[idx][1]

        # Send or submit: need user input
        if not input_value or not (send_clicks or n_submit):
            chip_clicked = isinstance(triggered, dict) and triggered.get("type") == "chat-chip"
            if chip_clicked and chip_clicks:
                input_value = CHIPS[triggered.get("index", 0)][1]
            else:
                raise PreventUpdate

        user_input = (input_value or "").strip()
        if not user_input:
            raise PreventUpdate

        messages.append({"role": "user", "content": user_input})

        # Initialize with welcome if empty (first message)
        if len(messages) == 1 and get_holdings_val_fn:
            val = get_holdings_val_fn()
            if val:
                welcome = build_welcome_message(val)
                messages = [{"role": "assistant", "content": welcome}, {"role": "user", "content": user_input}]
                save_chat_history(messages, user_id)

        # Trade command?
        parsed = parse_trade_command(user_input)
        if parsed and parsed.get("action") in ("add", "update", "remove", "memo") and parsed.get("symbol"):
            reply = execute_trade_payload(parsed, user_input)
            messages.append({"role": "assistant", "content": reply})
            save_chat_history(messages, user_id)
            return messages, "", {"display": "none"}, "", ""

        # AI stream
        holdings, val = [], {}
        try:
            from agents.secretary_agent import load_portfolio
            from pfa.portfolio_valuation import calculate_portfolio_value
            p = load_portfolio()
            holdings = p.get("holdings", [])
            val = calculate_portfolio_value(holdings) if holdings else get_holdings_val_fn() or {}
        except Exception:
            val = get_holdings_val_fn() or {}

        system_prompt = build_system_prompt(holdings, val)
        api_messages = [{"role": "system", "content": system_prompt}]
        for m in messages[-8:]:
            api_messages.append({"role": m["role"], "content": m.get("content", "")})

        request_id = str(uuid.uuid4())
        with _stream_lock:
            _stream_buffer[request_id] = {"text": "", "done": False}

        t = threading.Thread(target=_run_stream, args=(request_id, api_messages, user_id))
        t.daemon = True
        t.start()

        return messages, request_id, {"display": "flex"}, "", ""
