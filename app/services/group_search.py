class GroupSearch:
    @staticmethod
    def find_by_group(records: list[dict], group_name: str) -> list[dict]:
        group_name = group_name.strip().upper()
        result: list[dict] = []

        for record in records:
            groups_list = record.get("groups_list", [])
            groups_raw = str(record.get("groups", "")).upper()

            if group_name in groups_list or group_name in groups_raw:
                result.append(record)

        return result