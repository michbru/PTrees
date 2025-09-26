import dataclasses
import re
from typing import Union

from lseg.data._types import Strings

# regular expression pattern for intra-field position sequence
_partial_update_intra_field_positioning_sequence_regular_expression_pattern = re.compile(
    r"[\x1b\x5b|\x9b]([0-9]+)\x60([^\x1b^\x5b|\x9b]+)"
)


def _decode_intra_field_position_sequence(cached_value: str, new_value: str):
    # find all partial update in the value
    tokens = _partial_update_intra_field_positioning_sequence_regular_expression_pattern.findall(new_value)

    # check this value contains a partial update or not?
    if len(tokens) == 0:
        # no partial update required, so done
        return new_value

    # do a partial update
    updated_value = cached_value
    for offset, replace in tokens:
        # convert offset from str to int
        offset = int(offset)
        assert offset < len(updated_value)

        # replace the value in the string
        updated_value = updated_value[:offset] + replace + updated_value[offset + len(replace) :]

    # done, return
    return updated_value


@dataclasses.dataclass
class UniverseRecord:
    user_fields: Union[Strings, None]
    refresh_msg: dict = dataclasses.field(default_factory=dict)

    def get_field_value(self, field) -> Union[str, int, None]:
        try:
            return self.__getitem__(field)
        except KeyError:
            return None

    def get_fields(self, fields: Strings = None) -> dict:
        """
        Get fields from stream cache
        """
        if not self.refresh_msg:
            return {}

        record_fields = self.refresh_msg.get("Fields", {})

        if not fields:
            return record_fields

        return {field: record_fields[field] for field in fields if field in record_fields}

    def get_fields_values(self) -> list:
        return list(self.get_fields().values())

    def get_fields_keys(self) -> list:
        return list(self.get_fields().keys())

    def get_fields_items(self) -> list:
        return list(self.get_fields().items())

    def filter_fields(self, message_fields: dict) -> dict:
        if self.user_fields:
            return {k: v for k, v in message_fields.items() if k in self.user_fields}
        return message_fields

    def write_refresh_msg(self, refresh_msg: dict) -> None:
        if self.user_fields:
            refresh_msg["Fields"] = self.filter_fields(refresh_msg.get("Fields"))

        self.refresh_msg = refresh_msg

    def write_update_msg(self, update_msg: dict) -> None:
        for message_key, message_value in update_msg.items():
            if message_key == "Fields":
                message_fields = message_value
                message_fields = self.filter_fields(message_fields)

                # fields data
                # loop over all update items
                for key, value in message_fields.items():
                    # only string value need to check for a partial update
                    if isinstance(value, str):
                        # value is a string, so check for partial update string
                        # process partial update and update the callback
                        # with processed partial update
                        message_fields[key] = self._decode_partial_update_field(key, value)

                # update the field data
                self.refresh_msg.setdefault(message_key, {})
                self.refresh_msg[message_key].update(message_fields)
            else:
                # not a "Fields" data
                self.refresh_msg[message_key] = message_value

    def remove_fields(self, fields: Strings):
        for field in fields:
            self.get_fields().pop(field, None)

    def _decode_partial_update_field(self, key, value):
        """
        This legacy is used to process the partial update
        RETURNS the processed partial update data
        """

        fields = self.get_fields()
        if key not in fields:
            fields[key] = value
            return value

        # process infra-field positioning sequence
        cached_value = fields[key]

        # done
        return _decode_intra_field_position_sequence(cached_value, value)

    def __getitem__(self, field):
        if field in self.get_fields_keys():
            return self.get_fields()[field]

        raise KeyError(f"Field '{field}' not in Record")

    def __iter__(self):
        return iter(self.get_fields().items())


class CustomInstsUniverseRecord(UniverseRecord):
    def filter_fields(self, message_fields: dict) -> dict:
        if self.user_fields:
            return {k: v for k, v in message_fields.items() if k in self.user_fields}
        return message_fields
