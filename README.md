# **ai-inference-service**

## **Purpose**

The AI Inference Service is an internal microservice responsible for processing structured input and generating AI-driven insights.

It is responsible for:

* accepting structured inference requests from the API service
* processing spoken or written input
* executing inference logic (stubbed or model-backed)
* returning structured AI output
* exposing health endpoints for runtime checks

It is not responsible for:

* serving as a public-facing client gateway
* handling authentication or request orchestration
* formatting client-facing responses
* managing deployment state or infrastructure

---

## **API Contract**

### **Endpoints**

#### **GET /health**

Returns service health status.

Example response:

```json
{
  "status": "ok",
  "service": "ai-inference-service"
}
```

---

#### **POST /v1/infer**

Accepts structured inference input and returns AI-generated insights.

Example request:

```json
{
  "request_id": "abc-123",
  "input_type": "text",
  "content": "I have been feeling overwhelmed this week."
}
```

Example response:

```json
{
  "summary": "User reports stress and overwhelm.",
  "signals": ["stress", "fatigue"],
  "recommendation": "Suggest a short grounding exercise."
}
```

---

## **Service Structure**

* `src/app.py` — application entrypoint
* `src/routes/health.py` — health endpoint
* `src/routes/infer.py` — inference endpoint
* `src/services/inference_engine.py` — inference logic layer
* `src/models/schemas.py` — request/response schemas
* `src/config/settings.py` — runtime configuration
* `tests/` — test suite

---

## **CI/CD Pipeline (Phase 5 Complete)**

This service uses GitHub Actions with environment-aware behavior:

### **PR Behavior**

* Runs lint + tests (`validate`)
* Does NOT build images
* Does NOT update deployment state

### **Push to `main`**

* Runs validation
* Builds Docker image
* Tags image with full Git SHA
* Pushes image to shared ECR repository
* Automatically updates **dev** environment in GitOps repo

### **Promotion Model**

* **Staging / Prod are NOT rebuilt**
* Manual promotion workflow updates GitOps state
* Same immutable image is reused across environments

**Principle:**

```
build once → promote the same artifact across environments
```

---

## **Containerization**

* Dockerized FastAPI service
* Lightweight Python 3.12 slim base image
* Image built from repository root using `Dockerfile`
* Image pushed to shared ECR repository:

```
<account>.dkr.ecr.<region>.amazonaws.com/ai-inference-service
```

---

## **Deployment Model**

This service does NOT deploy itself.

Instead:

* CI updates deployment state in `gitops-infra`
* Git becomes the source of truth for environment state
* Argo CD (future phase) will reconcile state into Kubernetes

---

## **Contains**

* AI inference service code
* Dockerfile
* Helm chart
* GitHub Actions CI pipeline
* Tests

---

## **Does Not Contain**

* Terraform infrastructure
* GitOps deployment state
* API orchestration logic
* Environment-specific configuration
* Direct deployment logic

---

## **Key Architectural Decisions**

* Separation of concerns between API (orchestration) and AI (processing)
* Immutable image tagging using full Git commit SHA
* Shared ECR repository across environments
* GitOps-driven deployment model
* Promotion across environments without rebuilding artifacts
* Internal-only service design (not publicly exposed)

---

## **Future Phases**

* Integration with real AI/ML models
* Compute-aware workloads (CPU/GPU optimization)
* Async processing for long-running inference tasks
* Model versioning and routing strategies
* Observability (logging, metrics, tracing)
* Autoscaling and performance tuning

---

## **Architecture Context**

This service is part of a hybrid platform:

* **API Service** → client-facing gateway and orchestration layer
* **AI Inference Service (this service)** → internal processing and insight generation
* **CMS Monolith** → internal content management system
