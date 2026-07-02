from enum import Enum


class ResumeProcessingStages(str, Enum):
    NONE = "none"
    UPLOADED = "uploaded"
    PARSING = "parsing"
    # Value kept as-is for backward compatibility with already-persisted
    # metadata.json files; only the (previously misspelled) member name changed.
    DOC_TREE_GENERATED = "document tree generated"
    PARSED = "parsed"
    FAILED = "failed"
    ERROR = "error"
