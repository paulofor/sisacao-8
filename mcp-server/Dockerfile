FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY mcp-server/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY mcp-server/src /app/mcp-server/src

HEALTHCHECK --interval=30s --timeout=10s --start-period=20s --retries=5 \
  CMD python -c "import json,sys,urllib.request; \
req=urllib.request.Request('http://127.0.0.1:80/mcp', \
data=json.dumps({'jsonrpc':'2.0','id':'healthcheck','method':'tools/call','params':{'name':'ping','arguments':{}}}).encode(), \
headers={'Content-Type':'application/json','Accept':'application/json, text/event-stream'}); \
resp=urllib.request.urlopen(req, timeout=8); \
sys.exit(0 if 200 <= resp.status < 300 else 1)"

CMD ["python", "/app/mcp-server/src/server.py"]
