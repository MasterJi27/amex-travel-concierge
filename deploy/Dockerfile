FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY agent /app/agent
ENV PYTHONPATH=/app
EXPOSE 8002
CMD ["python", "-m", "agent"]
