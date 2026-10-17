FROM python:3.11-slim
WORKDIR /srv
ENV PYTHONUNBUFFERED=1 HF_HOME=/hf-cache
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app ./app
COPY experiments ./experiments
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
