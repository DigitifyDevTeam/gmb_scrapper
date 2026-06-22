import enum


class SearchStatus(str, enum.Enum):
    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"
    STOPPED = "stopped"
    COMPLETED = "completed"
    FAILED = "failed"


class WebsiteReason(str, enum.Enum):
    NO_URL = "no_url"
    DNS_FAILURE = "dns_failure"
    HTTP_FAILURE = "http_failure"
    SOCIAL_ONLY = "social_only"
    UNDER_CONSTRUCTION = "under_construction"
    VALID = "valid"
