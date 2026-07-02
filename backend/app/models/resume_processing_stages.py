from enum import Enum

class ResumeProcessingStages(str, Enum):
    NONE = "none"
    UPLOADED = "uploaded"
    PARSING = "parsing"
    DOC_TREE_GENERATEED = "document tree generated"
    PARSED = "parsed"
    ERROR = "error"
