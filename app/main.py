from datetime import datetime, timezone

from fastapi import FastAPI

app = FastAPI(title="Cslip", version="0.1.0")


@app.get("/health")
async def health():
    return {"status": "ok", "timestamp": datetime.now(timezone.utc).isoformat()}


# LINE webhook endpoint added in Task 2
