from enum import Enum

class ParserType(Enum):
    RULE_BASED = "rule_based"
    NLP_ML = "nlp_ml"

_selected_parser = ParserType.RULE_BASED


def get_selected_parser():
    return _selected_parser


def set_selected_parser(parser_type: ParserType):
    global _selected_parser
    _selected_parser = parser_type

