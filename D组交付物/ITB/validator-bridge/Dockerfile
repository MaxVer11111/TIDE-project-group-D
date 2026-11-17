FROM python:3.13-slim
RUN pip install --no-cache-dir --index-url https://pypi.org/simple jsonschema==4.26.0
WORKDIR /app
COPY server.py /app/server.py
CMD ["python", "server.py"]
