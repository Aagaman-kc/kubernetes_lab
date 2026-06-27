# Base image
FROM python:3.11-alpine
# woeking directory  inside container
WORKDIR /app
# COPY application
COPY requirements.txt .
COPY app.py .
RUN pip install -r requirements.txt

EXPOSE 80
# start fast api
CMD ["uvicorn","app:app","--host","0.0.0.0","--port","80"]