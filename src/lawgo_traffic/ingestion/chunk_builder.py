from lawgo_traffic.ingestion.legal_parser import LegalUnit


def build_parent_chunks(units: list[LegalUnit]) -> list[dict]:
    """Group LegalUnits by Article to create parent chunks."""
    # TODO: implement
    raise NotImplementedError


def build_child_chunks(units: list[LegalUnit]) -> list[dict]:
    """Create child chunks (Clause/Point level) with legal_path and text_for_search."""
    # TODO: implement
    raise NotImplementedError


def build_all_chunks(units: list[LegalUnit]) -> tuple[list[dict], list[dict]]:
    """Return (parents, children) tuple."""
    return build_parent_chunks(units), build_child_chunks(units)
