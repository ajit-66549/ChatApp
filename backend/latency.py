import logging

logger = logging.getLogger("chatapp.performance")

def log_message_latency(client_id: str, scope: str, receive_at: float, db_save_at: float, broadcast_at: float, db_stage_timings: dict = None) -> None:
    db_latency = (db_save_at - receive_at) * 1000
    broadcast_latency = (broadcast_at - db_save_at) * 1000
    total_latency = (broadcast_at - receive_at) * 1000
    db_stage_timings = db_stage_timings or {}
    logger.info(
        "message_pipeline client=%s room=%s \n db_ms=%.2f \n broadcast_ms=%.2f \n total_ms=%.2f \n model_init_ms=%.2f \n commit_ms=%.2f \n refresh_ms=%.2f \n repo_total_ms=%.2f",
        client_id,
        scope,
        db_latency,
        broadcast_latency,
        total_latency,
        db_stage_timings.get("model_init_ms", 0.0),
        db_stage_timings.get("commit_ms", 0.0),
        db_stage_timings.get("refresh_ms", 0.0),
        db_stage_timings.get("repo_total_ms", 0.0),
    )