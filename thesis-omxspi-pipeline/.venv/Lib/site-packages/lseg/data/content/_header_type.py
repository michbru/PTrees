from enum import Enum, unique, auto


@unique
class HeaderType(Enum):
    NAME = auto()
    TITLE = auto()
    NAME_AND_TITLE = auto()


def get_header_type_by_use_field_names_in_headers(
    use_field_names_in_headers: bool, default_header_type: HeaderType = HeaderType.TITLE
) -> HeaderType:
    header_type = default_header_type
    if use_field_names_in_headers is not None:
        if use_field_names_in_headers:
            header_type = HeaderType.NAME
        else:
            header_type = HeaderType.TITLE
    return header_type
