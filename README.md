# Platforming

### Install Required Tools

```
brew install kind kubectl
brew install python3 pipx
pipx install fastapi uvicorn
brew install --cask lens
```

### Phase 1 : Go from zero to a Local Observable Service

#### Part 1 – Build a Microservice for the Demo

Goal: Build a simple FastAPI microservice to serve as the demo app.

Endpoints:
	•	/checkout → simulates real business logic
	•	/healthz → readiness / liveness probe

#### Part 2 – Add Built-In Observability

Goal: We don’t just want an app that runs — we want one that explains itself when it runs.
	1.	Integrate OpenTelemetry to export traces of each request.
	•	Requests show up in Jaeger (span name, duration, trace ID).
	2.	Integrate Prometheus (using prometheus-fastapi-instrumentator) to export metrics at /metrics.
	•	Real-time counts, latencies, and error rates ready for Prometheus scraping.

#### Part 3 – Test Locally Before Automation

1. Run the app locally

```
# from fastapi-demo/
python3 -m venv .venv
source ./.venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8080
```

2. Test endpoints
   
`curl -s http://localhost:8080/healthz`
`curl -s http://localhost:8080/checkout`

You should see JSON responses.

3. Run Jaeger to see Traces

Spin up a quick Jaeger all-in-one with an OTLP HTTP receiver (to see the traces)

```
docker run -p 16686:16686 -p 4318:4318 --name jaeger \
  jaegertracing/all-in-one:1.57
```

Keep your app running with defaults (it exports to http://localhost:4318/v1/traces).

Send a few requests: `for i in {1..5}; do curl -s http://localhost:8080/checkout > /dev/null; done`

Open the Jaeger UI: http://localhost:16686
→ find service fastapi-demo → see spans.


#### Adding Prometheus Metrics

1. Install the library `pip install prometheus-fastapi-instrumentator`

Add to your requirements.txt:

```
fastapi
uvicorn
opentelemetry-api
opentelemetry-sdk
opentelemetry-exporter-otlp
prometheus-fastapi-instrumentator
```

Run the app
`uvicorn app.main:app --reload --port 8080`

Verify endpoints:
`curl -s http://localhost:8080/healthz`

`curl -s http://localhost:8080/checkout`

Open http://localhost:8080/metrics

Example output:

```
# HELP http_request_duration_seconds Request duration
# TYPE http_request_duration_seconds histogram
http_request_duration_seconds_count{handler="/checkout",method="GET",status="200"} 5.0
http_request_duration_seconds_sum{handler="/checkout",method="GET",status="200"} 2.61
```

###  Visualize metrics with Prometheus

If you have Prometheus installed via Homebrew:
	1.	Create prometheus.yml
	2.	Start Prometheus: `prometheus --config.file=prometheus.yml`

	3.	Add this scrape job:
```
scrape_configs:
  - job_name: 'fastapi-demo'
    static_configs:
      - targets: ['localhost:8080']
```

	4.	Visit http://localhost:9090
      Query: http_request_duration_seconds_count

      Now you’re seeing live FastAPI request metrics directly from your app!

Metrics show the what — 500 requests/sec, 2% errors.
Traces reveal the why — checkout calls payment 3× because of retries.
Together they form core observability.

“Developers can now see both sides of performance: metrics show the ‘what’ — 500 requests per second, 2% errors — while traces reveal the ‘why’ — checkout calls payment three times because of retries.”


#### Part 4 – Validate Your Dockerfile
Goal : Validate your Dockerfile before CI/CD

```
docker build -t fastapi-demo:local .
docker run -p 8080:8080 --rm fastapi-demo:local
curl -s http://localhost:8080/checkout
```

To export traces from inside the container to local Jaeger:

```
# Ensure Jaeger from step D is running
docker run -e OTEL_EXPORTER_OTLP_ENDPOINT=http://host.docker.internal:4318/v1/traces \
  -e OTEL_SERVICE_NAME=fastapi-demo \
  -p 8080:8080 --rm fastapi-demo:local
```

#### Part 5 – Enable Traces Inside Docker (with Correct Networking)
If you try exporting traces from inside the container to Jaeger using:

```
docker run -e OTEL_EXPORTER_OTLP_ENDPOINT=http://host.docker.internal:4318/v1/traces \
  -e OTEL_SERVICE_NAME=fastapi-demo \
  -p 8080:8080 --rm fastapi-demo:local
```

you might see connection errors if Jaeger isn’t reachable from the container.
To fix that, run both containers on the same Docker network.

1. Create a shared network : `docker network create observability` 
2. Run Jaeger on that network:
   
   ```
   docker run -d --name jaeger \
  --network observability \
  -e COLLECTOR_OTLP_ENABLED=true \
  -p 16686:16686 -p 4318:4318 \
  jaegertracing/all-in-one:1.57
  ```
3. Run the FastAPI app on the same network

```
docker run --rm \
  --network observability \
  -e OTEL_EXPORTER_OTLP_ENDPOINT=http://jaeger:4318/v1/traces \
  -e OTEL_SERVICE_NAME=fastapi-demo \
  -p 8080:8080 fastapi-demo:local
  ```

4. Test it: `for i in {1..5}; do curl -s http://localhost:8080/checkout > /dev/null; done`

Then open Jaeger → http://localhost:16686

✅ You’ll now see traces for fastapi-demo.

#### Optional: Use Docker Compose for One-Command Startup

Create a `docker-compose.yml`:

```
version: "3.8"
services:
  jaeger:
    image: jaegertracing/all-in-one:1.57
    ports:
      - "16686:16686"
      - "4318:4318"
    environment:
      - COLLECTOR_OTLP_ENABLED=true

  fastapi-demo:
    build: .
    ports:
      - "8080:8080"
    environment:
      - OTEL_EXPORTER_OTLP_ENDPOINT=http://jaeger:4318/v1/traces
      - OTEL_SERVICE_NAME=fastapi-demo
    depends_on:
      - jaeger
```

Then run: `docker compose up --build`

Both the app and Jaeger come online automatically and connect correctly.


#### Phase 1 Outcome
	•	FastAPI service runs locally
	•	Exposes /checkout and /healthz
	•	Traces visible in Jaeger
	•	Metrics exposed at /metrics
	•	Docker build works
	•	Foundation ready for automation (Phase 2)



