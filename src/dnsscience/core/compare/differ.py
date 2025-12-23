"""Response diffing logic for DNS comparison."""

from dnsscience.core.models import (
    DNSRecord,
    DNSResponse,
    RecordDiff,
    ResponseDiff,
)


class ResponseDiffer:
    """
    Compare two DNS responses and identify differences.

    Handles:
    - RCODE comparison
    - Record count comparison
    - Individual record comparison (name, type, TTL, value)
    - Timing differences
    """

    def __init__(
        self,
        ignore_ttl: bool = False,
        ttl_tolerance: int = 0,
        ignore_case: bool = True,
        ignore_record_order: bool = True,
    ):
        self.ignore_ttl = ignore_ttl
        self.ttl_tolerance = ttl_tolerance
        self.ignore_case = ignore_case
        self.ignore_record_order = ignore_record_order

    def diff(self, source: DNSResponse, target: DNSResponse) -> ResponseDiff:
        """Compare two DNS responses and return detailed diff."""
        rcode_match = source.rcode == target.rcode
        record_count_match = len(source.records) == len(target.records)

        # Compare records
        record_diffs, missing_source, missing_target = self._compare_records(
            source.records, target.records
        )

        records_match = len(record_diffs) == 0 and len(missing_source) == 0 and len(missing_target) == 0

        # Overall match
        match = rcode_match and records_match

        # Timing difference
        timing_diff = target.query_time_ms - source.query_time_ms

        return ResponseDiff(
            query=source.query,
            match=match,
            rcode_match=rcode_match,
            record_count_match=record_count_match,
            records_match=records_match,
            timing_diff_ms=timing_diff,
            source_response=source,
            target_response=target,
            record_diffs=record_diffs,
            missing_in_source=missing_source,
            missing_in_target=missing_target,
        )

    def _compare_records(
        self, source_records: list[DNSRecord], target_records: list[DNSRecord]
    ) -> tuple[list[RecordDiff], list[DNSRecord], list[DNSRecord]]:
        """Compare record lists and identify differences."""
        diffs: list[RecordDiff] = []
        missing_in_source: list[DNSRecord] = []
        missing_in_target: list[DNSRecord] = []

        # Normalize records for comparison
        source_normalized = {self._record_key(r): r for r in source_records}
        target_normalized = {self._record_key(r): r for r in target_records}

        source_keys = set(source_normalized.keys())
        target_keys = set(target_normalized.keys())

        # Records only in source
        for key in source_keys - target_keys:
            missing_in_target.append(source_normalized[key])

        # Records only in target
        for key in target_keys - source_keys:
            missing_in_source.append(target_normalized[key])

        # Records in both - check for value differences
        for key in source_keys & target_keys:
            source_rec = source_normalized[key]
            target_rec = target_normalized[key]

            # Compare TTL if not ignored
            if not self.ignore_ttl:
                ttl_diff = abs(source_rec.ttl - target_rec.ttl)
                if ttl_diff > self.ttl_tolerance:
                    diffs.append(
                        RecordDiff(
                            field="ttl",
                            source_value=source_rec.ttl,
                            target_value=target_rec.ttl,
                        )
                    )

            # Compare values (already matched by key, but check for subtle differences)
            source_val = self._normalize_value(source_rec.value)
            target_val = self._normalize_value(target_rec.value)
            if source_val != target_val:
                diffs.append(
                    RecordDiff(
                        field="value",
                        source_value=source_rec.value,
                        target_value=target_rec.value,
                    )
                )

        return diffs, missing_in_source, missing_in_target

    def _record_key(self, record: DNSRecord) -> tuple:
        """Generate a comparison key for a record."""
        name = record.name.lower() if self.ignore_case else record.name
        name = name.rstrip(".")  # Normalize trailing dot
        value = self._normalize_value(record.value)

        return (name, record.record_type, value)

    def _normalize_value(self, value: str) -> str:
        """Normalize a record value for comparison."""
        value = value.strip()
        if self.ignore_case:
            value = value.lower()
        # Normalize trailing dots in domain names
        if value.endswith("."):
            value = value[:-1]
        return value


class RecordSetDiffer:
    """
    Compare entire record sets (useful for zone comparisons).
    """

    def __init__(self, differ: ResponseDiffer | None = None):
        self.differ = differ or ResponseDiffer()

    def diff_zones(
        self,
        source_records: list[DNSRecord],
        target_records: list[DNSRecord],
    ) -> dict:
        """Compare two complete zone record sets."""
        diffs, missing_source, missing_target = self.differ._compare_records(
            source_records, target_records
        )

        return {
            "match": len(diffs) == 0 and len(missing_source) == 0 and len(missing_target) == 0,
            "source_count": len(source_records),
            "target_count": len(target_records),
            "differences": [
                {
                    "field": d.field,
                    "source": d.source_value,
                    "target": d.target_value,
                }
                for d in diffs
            ],
            "missing_in_source": [
                {"name": r.name, "type": r.record_type.value, "value": r.value}
                for r in missing_source
            ],
            "missing_in_target": [
                {"name": r.name, "type": r.record_type.value, "value": r.value}
                for r in missing_target
            ],
        }
