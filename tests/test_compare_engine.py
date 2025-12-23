"""Tests for DNS comparison engine."""

import pytest
from unittest.mock import AsyncMock, MagicMock

from dnsscience.core.compare.engine import CompareEngine
from dnsscience.core.compare.differ import ResponseDiffer
from dnsscience.core.models import (
    BulkCompareResult,
    CompareResult,
    DNSQuery,
    DNSRecord,
    DNSResponse,
    RecordType,
)


class TestResponseDiffer:
    """Tests for ResponseDiffer."""

    def test_identical_responses(self, sample_dns_query, sample_dns_response):
        differ = ResponseDiffer()
        result = differ.diff(sample_dns_response, sample_dns_response)

        assert result.match is True
        assert len(result.differences) == 0

    def test_different_rcode(self, sample_dns_query):
        response1 = DNSResponse(
            query=sample_dns_query,
            records=[],
            rcode="NOERROR",
            query_time_ms=10.0,
            server="8.8.8.8",
        )
        response2 = DNSResponse(
            query=sample_dns_query,
            records=[],
            rcode="NXDOMAIN",
            query_time_ms=10.0,
            server="1.1.1.1",
        )

        differ = ResponseDiffer()
        result = differ.diff(response1, response2)

        assert result.match is False
        assert any("rcode" in d.lower() for d in result.differences)

    def test_different_record_count(self, sample_dns_query):
        response1 = DNSResponse(
            query=sample_dns_query,
            records=[
                DNSRecord(
                    name="example.com",
                    record_type=RecordType.A,
                    ttl=300,
                    data="1.2.3.4",
                ),
            ],
            rcode="NOERROR",
            query_time_ms=10.0,
            server="8.8.8.8",
        )
        response2 = DNSResponse(
            query=sample_dns_query,
            records=[
                DNSRecord(
                    name="example.com",
                    record_type=RecordType.A,
                    ttl=300,
                    data="1.2.3.4",
                ),
                DNSRecord(
                    name="example.com",
                    record_type=RecordType.A,
                    ttl=300,
                    data="5.6.7.8",
                ),
            ],
            rcode="NOERROR",
            query_time_ms=10.0,
            server="1.1.1.1",
        )

        differ = ResponseDiffer()
        result = differ.diff(response1, response2)

        assert result.match is False
        assert any("record" in d.lower() for d in result.differences)

    def test_different_record_data(self, sample_dns_query):
        response1 = DNSResponse(
            query=sample_dns_query,
            records=[
                DNSRecord(
                    name="example.com",
                    record_type=RecordType.A,
                    ttl=300,
                    data="1.2.3.4",
                ),
            ],
            rcode="NOERROR",
            query_time_ms=10.0,
            server="8.8.8.8",
        )
        response2 = DNSResponse(
            query=sample_dns_query,
            records=[
                DNSRecord(
                    name="example.com",
                    record_type=RecordType.A,
                    ttl=300,
                    data="5.6.7.8",
                ),
            ],
            rcode="NOERROR",
            query_time_ms=10.0,
            server="1.1.1.1",
        )

        differ = ResponseDiffer()
        result = differ.diff(response1, response2)

        assert result.match is False

    def test_ttl_differences_ignored_by_default(self, sample_dns_query):
        response1 = DNSResponse(
            query=sample_dns_query,
            records=[
                DNSRecord(
                    name="example.com",
                    record_type=RecordType.A,
                    ttl=300,
                    data="1.2.3.4",
                ),
            ],
            rcode="NOERROR",
            query_time_ms=10.0,
            server="8.8.8.8",
        )
        response2 = DNSResponse(
            query=sample_dns_query,
            records=[
                DNSRecord(
                    name="example.com",
                    record_type=RecordType.A,
                    ttl=600,  # Different TTL
                    data="1.2.3.4",
                ),
            ],
            rcode="NOERROR",
            query_time_ms=10.0,
            server="1.1.1.1",
        )

        differ = ResponseDiffer(ignore_ttl=True)
        result = differ.diff(response1, response2)

        assert result.match is True


class TestCompareEngine:
    """Tests for CompareEngine."""

    @pytest.fixture
    def mock_source_client(self):
        client = AsyncMock()
        return client

    @pytest.fixture
    def mock_target_client(self):
        client = AsyncMock()
        return client

    @pytest.fixture
    def compare_engine(self, mock_source_client, mock_target_client):
        return CompareEngine(
            source_client=mock_source_client,
            target_client=mock_target_client,
        )

    @pytest.mark.asyncio
    async def test_compare_single(
        self,
        compare_engine,
        mock_source_client,
        mock_target_client,
        sample_dns_query,
        sample_dns_response,
    ):
        mock_source_client.query.return_value = sample_dns_response
        mock_target_client.query.return_value = sample_dns_response

        result = await compare_engine.compare(sample_dns_query)

        assert isinstance(result, CompareResult)
        assert result.match is True
        mock_source_client.query.assert_called_once()
        mock_target_client.query.assert_called_once()

    @pytest.mark.asyncio
    async def test_compare_bulk(
        self,
        compare_engine,
        mock_source_client,
        mock_target_client,
        sample_dns_response,
    ):
        mock_source_client.query.return_value = sample_dns_response
        mock_target_client.query.return_value = sample_dns_response

        queries = [
            DNSQuery(name="example.com", record_type=RecordType.A),
            DNSQuery(name="google.com", record_type=RecordType.A),
            DNSQuery(name="cloudflare.com", record_type=RecordType.A),
        ]

        result = await compare_engine.compare_bulk(queries)

        assert isinstance(result, BulkCompareResult)
        assert result.queries_tested == 3
        assert result.matches == 3
        assert result.mismatches == 0
        assert result.confidence_score == 1.0

    @pytest.mark.asyncio
    async def test_compare_bulk_with_mismatches(
        self,
        compare_engine,
        mock_source_client,
        mock_target_client,
        sample_dns_query,
    ):
        source_response = DNSResponse(
            query=sample_dns_query,
            records=[
                DNSRecord(
                    name="example.com",
                    record_type=RecordType.A,
                    ttl=300,
                    data="1.2.3.4",
                )
            ],
            rcode="NOERROR",
            query_time_ms=10.0,
            server="source",
        )
        target_response = DNSResponse(
            query=sample_dns_query,
            records=[],
            rcode="NXDOMAIN",
            query_time_ms=10.0,
            server="target",
        )

        # First query matches, second doesn't
        mock_source_client.query.side_effect = [source_response, source_response]
        mock_target_client.query.side_effect = [source_response, target_response]

        queries = [
            DNSQuery(name="example.com", record_type=RecordType.A),
            DNSQuery(name="missing.com", record_type=RecordType.A),
        ]

        result = await compare_engine.compare_bulk(queries)

        assert result.queries_tested == 2
        assert result.matches == 1
        assert result.mismatches == 1
        assert result.confidence_score == 0.5

    @pytest.mark.asyncio
    async def test_compare_handles_source_error(
        self,
        compare_engine,
        mock_source_client,
        mock_target_client,
        sample_dns_query,
        sample_dns_response,
    ):
        mock_source_client.query.side_effect = Exception("Connection failed")
        mock_target_client.query.return_value = sample_dns_response

        result = await compare_engine.compare(sample_dns_query)

        assert result.match is False
        assert result.source_response is None
        assert "error" in str(result.differences).lower()

    @pytest.mark.asyncio
    async def test_compare_handles_target_error(
        self,
        compare_engine,
        mock_source_client,
        mock_target_client,
        sample_dns_query,
        sample_dns_response,
    ):
        mock_source_client.query.return_value = sample_dns_response
        mock_target_client.query.side_effect = Exception("Connection failed")

        result = await compare_engine.compare(sample_dns_query)

        assert result.match is False
        assert result.target_response is None
