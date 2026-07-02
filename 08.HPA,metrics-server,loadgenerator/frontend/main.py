from fastapi import FastAPI
from fastapi.responses import HTMLResponse
import requests

app = FastAPI()

@app.get('/',response_class=HTMLResponse)
def home():
    response = requests.get("http://backend")
    data = response.json
    return f"""
    <html>
    <head>
        <title>Kubernetes Demo</title>
    </head>

    <body style="font-family:Arial">

        <h1>Frontend Pod</h1>
        <h2>Response from Backend</h2>
        <pre>{data}</pre>

    </body>
    </html>
"""