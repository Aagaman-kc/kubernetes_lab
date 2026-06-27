from fastapi import FastAPI

app = FastAPI()

@app.get('/')
def home():
    return {
        'message':'Hello from 06.phase',
        'note':'i will learn everything about networking, cloud, devops, mlops and architecture'
    }