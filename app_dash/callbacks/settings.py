"""Settings page callbacks"""

import dash
from dash import Input, Output, State


def register_settings_callbacks(app: dash.Dash):
    @app.callback(
        Output("url", "pathname", allow_duplicate=True),
        Input("settings-add-rss", "n_clicks"),
        Input({"type": "settings-del-rss", "index": dash.ALL}, "n_clicks"),
        State("settings-rss-url", "value"),
        State("settings-rss-name", "value"),
        prevent_initial_call=True,
    )
    def _settings_actions(add_clicks, del_clicks, url_val, name_val):
        triggered = dash.ctx.triggered_id
        if triggered == "settings-add-rss" and add_clicks and (url_val or "").strip():
            from agents.secretary_agent import add_rss_source
            add_rss_source((url_val or "").strip(), (name_val or "").strip() or "RSS", "其他")
            return "/settings"
        if isinstance(triggered, dict) and triggered.get("type") == "settings-del-rss" and triggered.get("url"):
            from agents.secretary_agent import remove_rss_source
            remove_rss_source(triggered["url"])
            return "/settings"
        raise dash.exceptions.PreventUpdate
