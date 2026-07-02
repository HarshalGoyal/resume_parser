from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from enum import Enum
from typing import Optional

from app.config.parser_config import get_selected_parser, set_selected_parser, ParserType as ConfigParserType

router = APIRouter(prefix="/parser-config", tags=["Parser Configuration"])

class ParserType(str, Enum):
    rule_based = "rule_based"
    nlp_ml = "nlp_ml"

class ParserConfigRequest(BaseModel):
    parser_type: ParserType

@router.get("/current")
async def get_current_parser():
    current = get_selected_parser()
    return {"current_parser": current.value}

@router.get("/available")
async def get_available_parsers():
    return {"available_parsers": [p.value for p in ParserType]}

@router.post("/set")
async def set_parser(config: ParserConfigRequest):
    if config.parser_type not in ParserType:
        raise HTTPException(status_code=400, detail="Invalid parser type")

    if config.parser_type == ParserType.rule_based:
        set_selected_parser(ConfigParserType.RULE_BASED)
    elif config.parser_type == ParserType.nlp_ml:
        set_selected_parser(ConfigParserType.NLP_ML)

    current = get_selected_parser()
    return {"message": f"Parser switched to {current.value}"}

