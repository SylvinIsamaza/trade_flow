"""
Custom ID Generator Utilities
Generates unique IDs in various formats
"""
import uuid
from datetime import datetime
from typing import Optional


def generate_uuid() -> str:
    """Generate a simple UUID."""
    return str(uuid.uuid4())


def generate_user_id() -> str:
    """Generate user ID: usr_<uuid8>"""
    return f"usr_{uuid.uuid4().hex[:12]}"


def generate_account_id(timeframe: str = "live") -> str:
    """Generate account ID: acc_<timeframe>_<uuid8>"""
    return f"acc_{timeframe}_{uuid.uuid4().hex[:8]}"


def generate_trade_id(account_id: str, date: Optional[datetime] = None) -> str:
    """Generate trade ID: trd_<account_short>_<timestamp>_<random>"""
    if date is None:
        date = datetime.utcnow()
    account_short = account_id.split("_")[1] if "_" in account_id else account_id[:4]
    timestamp = date.strftime("%Y%m%d%H%M%S")
    return f"trd_{account_short}_{timestamp}_{uuid.uuid4().hex[:6]}"


def generate_session_id(account_id: str) -> str:
    """Generate session ID: ses_<account_short>_<uuid6>"""
    account_short = account_id.split("_")[1] if "_" in account_id else account_id[:4]
    return f"ses_{account_short}_{uuid.uuid4().hex[:6]}"


def generate_strategy_id(account_id: str) -> str:
    """Generate strategy ID: stg_<account_short>_<uuid6>"""
    account_short = account_id.split("_")[1] if "_" in account_id else account_id[:4]
    return f"stg_{account_short}_{uuid.uuid4().hex[:6]}"


def generate_note_id(account_id: str) -> str:
    """Generate note ID: nte_<account_short>_<uuid6>"""
    account_short = account_id.split("_")[1] if "_" in account_id else account_id[:4]
    return f"nte_{account_short}_{uuid.uuid4().hex[:6]}"


def generate_tag_id(account_id: str) -> str:
    """Generate tag ID: tag_<account_short>_<uuid6>"""
    account_short = account_id.split("_")[1] if "_" in account_id else account_id[:4]
    return f"tag_{account_short}_{uuid.uuid4().hex[:6]}"


def generate_comment_id(account_id: str) -> str:
    """Generate comment ID: cmt_<account_short>_<uuid6>"""
    account_short = account_id.split("_")[1] if "_" in account_id else account_id[:4]
    return f"cmt_{account_short}_{uuid.uuid4().hex[:6]}"


def generate_file_id(account_id: str) -> str:
    """Generate file ID: fil_<account_short>_<uuid6>"""
    account_short = account_id.split("_")[1] if "_" in account_id else account_id[:4]
    return f"fil_{account_short}_{uuid.uuid4().hex[:6]}"


def generate_notification_id(account_id: str) -> str:
    """Generate notification ID: ntf_<account_short>_<uuid6>"""
    account_short = account_id.split("_")[1] if "_" in account_id else account_id[:4]
    return f"ntf_{account_short}_{uuid.uuid4().hex[:6]}"


def generate_insight_id(account_id: str) -> str:
    """Generate AI insight ID: ins_<account_short>_<uuid6>"""
    account_short = account_id.split("_")[1] if "_" in account_id else account_id[:4]
    return f"ins_{account_short}_{uuid.uuid4().hex[:6]}"


def generate_folder_id(account_id: str) -> str:
    """Generate folder ID: fld_<account_short>_<uuid6>"""
    account_short = account_id.split("_")[1] if "_" in account_id else account_id[:4]
    return f"fld_{account_short}_{uuid.uuid4().hex[:6]}"


def generate_job_id() -> str:
    """Generate background job ID: job_<uuid8>"""
    return f"job_{uuid.uuid4().hex[:8]}"


def generate_user_notification_id() -> str:
    """Generate user notification ID: usr_ntf_<uuid8>"""
    return f"usr_ntf_{uuid.uuid4().hex[:8]}"