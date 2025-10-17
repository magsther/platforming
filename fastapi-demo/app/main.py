from fastapi import FastAPI
import time, random
from app.otel_config import init_tracer
from opentelemetry import trace
from prometheus_fastapi_instrumentator import Instrumentator

# Initialize tracing
init_tracer()
tracer = trace.get_tracer(__name__)

# Create app
app = FastAPI()

# ✅ Initialize Prometheus metrics BEFORE startup
instrumentator = Instrumentator().instrument(app).expose(app)

@app.get("/checkout")
async def checkout():
    with tracer.start_as_current_span("checkout-operation"):
        time.sleep(random.uniform(0.2, 0.8))
        return {"status": "success"}

@app.get("/healthz")
def health():
    return {"status": "healthy"}
