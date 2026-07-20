def enqueue_enrichment_job(lead_id: str, job_type: str) -> dict:
    """Synchronous MVP contract; replace with Celery/RQ/Temporal adapter in production."""
    return {"lead_id": lead_id, "job_type": job_type, "status": "QUEUED_MVP"}
