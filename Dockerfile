FROM python:3.12-slim
WORKDIR /app
RUN pip install uv
COPY requirements.txt .
RUN uv pip install --system -r requirements.txt
COPY harmoniq_app/ ./agents/harmoniq_app/
COPY proxy_server.py .
COPY ui/ ./ui/
EXPOSE 8080
ENV PYTHONPATH=/app/agents
ENV PORT=8080
CMD ["python3", "proxy_server.py"]