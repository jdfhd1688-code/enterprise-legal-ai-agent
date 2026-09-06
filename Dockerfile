FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app
COPY data ./data
COPY scripts ./scripts

EXPOSE 8501

ENV STREAMLIT_SERVER_HEADLESS=true
CMD ["streamlit", "run", "app/frontend.py", "--server.port=8501", "--server.address=0.0.0.0"]
