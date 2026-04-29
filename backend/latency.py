import logging

logger = logging.getLogger("chatapp.performance")

def log_message_latency(client_id: str, scope: str, receive_at: float, db_save_at: float, broadcast_at: float) -> None:
    db_latency = (db_save_at - receive_at) * 1000
    broadcast_latency = (broadcast_at - db_save_at) * 1000
    total_latency = (broadcast_at - receive_at) * 1000
    logger.info(
        "message_pipeline client=%s room=%s \n db_ms=%.2f \n broadcast_ms=%.2f \n total_ms=%.2f",
        client_id,
        scope,
        db_latency,
        broadcast_latency,
        total_latency,
    )