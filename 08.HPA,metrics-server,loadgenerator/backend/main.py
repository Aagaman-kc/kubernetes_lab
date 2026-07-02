from fastapi import FastAPI

app = FastAPI()

@app.get('/')
def home():
    data = {
        "name":"aagaman.k.c",
        "message":"hello from phase 8"
    }
    return data