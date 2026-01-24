"""
BE-Campaign Integration Module

This module provides reference implementations for integrating ReasonLoop
with the be-campaign backend application.

Components:
- adapters/ai_agent_adapter.py: HTTP client for ReasonLoop API
- services/customer_ai_service.py: Business logic for customer enrichment
- api/routers/customers.py: FastAPI endpoints for triggering enrichment
- models/customer.py: Customer model with AI fields

Usage:
    Copy these files to your be-campaign project and adapt as needed.
"""
