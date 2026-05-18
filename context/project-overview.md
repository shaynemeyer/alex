# Alex

## Overview

Alex (Agentic Learning Equities eXplainer) is a multi-agent enterprise-grade SaaS financial planning platform. Users connect their equity portfolios and receive AI-generated analysis: written reports, visualizations, and retirement projections. A background research agent continuously gathers market intelligence and stores it in a vector knowledge base that the portfolio agents draw from when generating analysis.

## Goals

1. Let authenticated users manage equity portfolios and preferences.
2. Provide AI-generated portfolio analysis reports, charts, and retirement projections on demand.
3. Continuously gather and index market research to enrich agent analysis.
4. Classify financial instruments automatically so portfolio data is always enriched.
5. Deploy a production-grade multi-agent system on AWS serverless infrastructure.
6. Keep infrastructure costs low through S3 Vectors (90% cheaper than OpenSearch) and Aurora Serverless v2.

## Core User Flow

1. User signs in via Clerk.
2. User views or updates their equity portfolio.
3. User triggers a portfolio analysis.
4. Planner agent orchestrates Tagger, Reporter, Charter, and Retirement agents in parallel.
5. Agents write results (reports, charts, projections) to the database.
6. User reviews the completed analysis on the frontend.

## Features

### Authentication and Portfolio Management

- Clerk-based authentication with route protection.
- Per-user portfolio storage with instrument classifications.
- User preferences (retirement target, risk tolerance).

### Multi-Agent Analysis

- **Financial Planner**: Orchestrates the full analysis workflow; retrieves relevant context from the S3 Vectors knowledge base.
- **InstrumentTagger**: Classifies unknown instruments by asset class, region, and sector using structured outputs.
- **Report Writer**: Generates a comprehensive markdown portfolio narrative with recommendations.
- **Chart Maker**: Produces Recharts-compatible JSON for asset class, regional, and sector allocation charts.
- **Retirement Specialist**: Projects retirement income and runs Monte Carlo simulations.

### Autonomous Research

- **Researcher Agent**: Runs on App Runner on an EventBridge schedule (every 2 hours).
- Browses financial websites via Playwright MCP and stores insights as vectors in S3 Vectors.
- Knowledge is retrieved by the Financial Planner during user-triggered analysis.

### Infrastructure

- Serverless compute: Lambda (agents, ingest, API backend) and App Runner (researcher).
- Vector storage: S3 Vectors with SageMaker Serverless embeddings (all-MiniLM-L6-v2).
- Relational storage: Aurora Serverless v2 PostgreSQL with Data API.
- CDN and API: CloudFront + S3 (frontend), API Gateway + Lambda (backend API).
- Observability: CloudWatch dashboards, alarms, and LangFuse tracing.

## Scope

### In Scope

- Clerk authentication and route protection
- Portfolio creation and management
- Instrument auto-classification
- On-demand multi-agent portfolio analysis (reports, charts, retirement projections)
- Autonomous background research and vector knowledge base
- S3 Vectors similarity search for context retrieval
- Aurora Serverless v2 for relational data
- Full-stack deployment: NextJS frontend, FastAPI backend, Lambda agents
- CloudWatch monitoring and LangFuse observability
- Enterprise hardening: WAF, VPC endpoints, GuardDuty, guardrails

### Out of Scope

- Real-time market data feeds (Polygon API integration is future work)
- Options strategy analysis
- Tax optimization agent
- Portfolio rebalancing agent
- ESG scoring
- Billing and subscription management

## Success Criteria

1. A signed-in user can add a portfolio and trigger an analysis.
2. The Planner correctly orchestrates all sub-agents and returns a complete result.
3. Reports, charts, and retirement projections are persisted and displayed in the frontend.
4. The Researcher agent runs autonomously and populates the S3 Vectors knowledge base.
5. The Planner retrieves relevant research context during analysis.
6. Infrastructure deploys end-to-end via Terraform with no manual steps beyond `terraform apply`.
7. Costs remain under ~$50/month under normal development usage.
