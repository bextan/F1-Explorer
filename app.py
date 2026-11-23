import os

from dash import Dash

from explorer.layout import layout

app = Dash(__name__, title="F1 Explorer", suppress_callback_exceptions=True,
           external_stylesheets=["https://fonts.googleapis.com/css2?family=Titillium+Web:wght@400;700;900&display=swap"])
app.layout = layout
server = app.server

if __name__ == "__main__":
    app.run(debug=False, port=int(os.environ.get("PORT", 8050)))
