# ai-inference-service

## Purpose
The AI Inference Service is an internal processing service for AI platform.

It is responsible for:
- accepting structured inference requests from the API service
- processing spoken or written input
- running stubbed or real inference logic
- returning structured AI output
- exposing health endpoints for runtime checks

It is not responsible for:
- serving as the public-facing client gateway
- handling client-facing authentication or orchestration
- owning public API response composition

## API Contract

### Endpoints

#### GET /health
Returns service health status.

Example response:
{
  "status": "ok",
  "service": "ai-inference-service"
}

#### POST /v1/infer
Accepts structured inference input from the API service and returns AI-generated output.

Example request:
{
  "request_id": "abc-123",
  "input_type": "text",
  "content": "I have been feeling overwhelmed this week."
}

Example response:
{
  "summary": "User reports stress and overwhelm.",
  "signals": ["stress", "fatigue"],
  "recommendation": "Suggest a short grounding exercise."
}

## Contains
- AI service code
- Dockerfile
- Helm chart
- GitHub Actions CI workflow
- Tests

## Does Not Contain
- Terraform infrastructure
- GitOps deployment state
- API orchestration logic
- CMS deployment logic

## Future Phases
- Model inference endpoints
- Resource constraints for compute workloads
- CI pipeline and container build process
