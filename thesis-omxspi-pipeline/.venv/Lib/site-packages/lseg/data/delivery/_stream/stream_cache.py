from typing import List


class StreamCache(dict):
    def __init__(self, data: dict):
        super().__init__(data.get("Fields", {}))
        self.status = data.get("State")
        self.service = data.get("Key", {}).get("Service")
        self.name = data.get("Key", {}).get("Name")

    def __bool__(self):
        return bool(dict(self))

    def __iter__(self):
        return iter(self.get_fields().items())

    def __getitem__(self, field):
        if field in self.keys():
            return super().__getitem__(field)
        raise KeyError(f"Field '{field}' not in Stream cache")

    def __len__(self):
        return len(self.keys())

    def __repr__(self):
        return str({"name": self.name, "service": self.service, "fields": dict(list(self.items()))})

    def __str__(self):
        service_name = f"{self.service or 'Unknown service'}|{str(self.name)}"
        field_value = ",".join(f"{f}:{v}" for f, v in self.items())
        return f"{service_name}[{field_value}]"

    @property
    def fields(self) -> List[str]:
        return list(self.keys())

    def get_fields(self, fields: list = None) -> dict:
        """
        Get fields from stream cache
        """
        if not self:
            return {}

        if not fields:
            return self

        return {field: self[field] for field in fields if field in self}
