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
