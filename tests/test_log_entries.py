"""Unit tests for log entries tools."""

import unittest
from datetime import datetime
from unittest.mock import Mock, patch

from pagerduty_mcp.models import (
    IncidentLogEntryQuery,
    ListResponseModel,
    LogEntry,
    LogEntryQuery,
)
from pagerduty_mcp.tools.log_entries import (
    get_log_entry,
    list_incident_log_entries,
    list_log_entries,
)


class TestLogEntriesTools(unittest.TestCase):
    """Test cases for log entries tools."""

    @classmethod
    def setUpClass(cls):
        """Set up test fixtures once for the entire test class."""
        cls.sample_log_entry_data = {
            "id": "LOGENTRY123",
            "type": "resolve_log_entry",
            "summary": "Resolved by User",
            "self": "https://api.pagerduty.com/log_entries/LOGENTRY123",
            "html_url": "https://test.pagerduty.com/log_entries/LOGENTRY123",
            "created_at": "2023-01-01T00:00:00Z",
            "agent": {
                "id": "PUSER123",
                "type": "user_reference",
                "summary": "Test User",
                "self": "https://api.pagerduty.com/users/PUSER123",
            },
            "service": {
                "id": "PSERVICE123",
                "type": "service_reference",
                "summary": "Test Service",
                "self": "https://api.pagerduty.com/services/PSERVICE123",
            },
            "incident": {
                "id": "PINCIDENT123",
                "type": "incident_reference",
                "summary": "Test Incident",
                "self": "https://api.pagerduty.com/incidents/PINCIDENT123",
                "html_url": "https://test.pagerduty.com/incidents/PINCIDENT123",
            },
        }

        cls.sample_trigger_log_entry_data = {
            "id": "LOGENTRY456",
            "type": "trigger_log_entry",
            "summary": "Incident triggered",
            "self": "https://api.pagerduty.com/log_entries/LOGENTRY456",
            "created_at": "2023-01-01T00:00:00Z",
            "agent": {
                "id": "PSERVICE123",
                "type": "service_reference",
                "summary": "Test Service",
                "self": "https://api.pagerduty.com/services/PSERVICE123",
            },
            "incident": {
                "id": "PINCIDENT123",
                "type": "incident_reference",
                "summary": "Test Incident",
                "self": "https://api.pagerduty.com/incidents/PINCIDENT123",
            },
        }

        cls.sample_acknowledge_log_entry_data = {
            "id": "LOGENTRY789",
            "type": "acknowledge_log_entry",
            "summary": "Acknowledged by User",
            "self": "https://api.pagerduty.com/log_entries/LOGENTRY789",
            "created_at": "2023-01-01T00:00:00Z",
            "agent": {
                "id": "PUSER456",
                "type": "user_reference",
                "summary": "Another User",
                "self": "https://api.pagerduty.com/users/PUSER456",
            },
            "incident": {
                "id": "PINCIDENT123",
                "type": "incident_reference",
                "summary": "Test Incident",
            },
        }

    @patch("pagerduty_mcp.tools.log_entries.get_client")
    @patch("pagerduty_mcp.tools.log_entries.paginate")
    def test_list_log_entries_basic(self, mock_paginate, mock_get_client):
        """Test basic log entries listing."""
        # Setup mocks
        mock_paginate.return_value = [self.sample_log_entry_data]

        # Test with basic query
        query = LogEntryQuery()
        result = list_log_entries(query)

        # Assertions
        self.assertIsInstance(result, ListResponseModel)
        self.assertEqual(len(result.response), 1)
        self.assertIsInstance(result.response[0], LogEntry)
        self.assertEqual(result.response[0].id, "LOGENTRY123")
        self.assertEqual(result.response[0].type, "resolve_log_entry")

        # Verify paginate was called with correct parameters
        mock_paginate.assert_called_once()
        call_args = mock_paginate.call_args
        self.assertEqual(call_args[1]["entity"], "log_entries")
        self.assertEqual(call_args[1]["maximum_records"], 100)

    @patch("pagerduty_mcp.tools.log_entries.get_client")
    @patch("pagerduty_mcp.tools.log_entries.paginate")
    def test_list_log_entries_with_filters(self, mock_paginate, mock_get_client):
        """Test listing log entries with various filters."""
        # Setup mocks
        mock_paginate.return_value = [
            self.sample_log_entry_data,
            self.sample_trigger_log_entry_data,
            self.sample_acknowledge_log_entry_data,
        ]

        # Test with filters
        since_date = datetime(2023, 1, 1)
        until_date = datetime(2023, 1, 31)
        query = LogEntryQuery(
            since=since_date,
            until=until_date,
            is_overview=True,
            include=["incidents", "services"],
            limit=50,
        )
        result = list_log_entries(query)

        # Assertions
        self.assertIsInstance(result, ListResponseModel)
        self.assertEqual(len(result.response), 3)

        # Verify parameters were passed correctly
        call_args = mock_paginate.call_args
        params = call_args[1]["params"]
        self.assertEqual(params["since"], since_date.isoformat())
        self.assertEqual(params["until"], until_date.isoformat())
        self.assertEqual(params["is_overview"], "true")
        self.assertEqual(params["include[]"], ["incidents", "services"])
        self.assertEqual(params["time_zone"], "UTC")
        self.assertEqual(call_args[1]["maximum_records"], 50)

    @patch("pagerduty_mcp.tools.log_entries.get_client")
    @patch("pagerduty_mcp.tools.log_entries.paginate")
    def test_list_log_entries_overview_only(self, mock_paginate, mock_get_client):
        """Test listing log entries with overview flag (triggers, acks, resolves only)."""
        # Setup mocks
        mock_paginate.return_value = [
            self.sample_trigger_log_entry_data,
            self.sample_acknowledge_log_entry_data,
            self.sample_log_entry_data,
        ]

        # Test with is_overview=True
        query = LogEntryQuery(is_overview=True)
        result = list_log_entries(query)

        # Assertions
        self.assertEqual(len(result.response), 3)
        entry_types = [entry.type for entry in result.response]
        self.assertIn("trigger_log_entry", entry_types)
        self.assertIn("acknowledge_log_entry", entry_types)
        self.assertIn("resolve_log_entry", entry_types)

        # Verify is_overview parameter was passed
        call_args = mock_paginate.call_args
        params = call_args[1]["params"]
        self.assertEqual(params["is_overview"], "true")

    @patch("pagerduty_mcp.tools.log_entries.get_client")
    @patch("pagerduty_mcp.tools.log_entries.paginate")
    def test_list_log_entries_default_limit(self, mock_paginate, mock_get_client):
        """Test that default limit is properly set."""
        # Setup mocks
        mock_paginate.return_value = [self.sample_log_entry_data]

        # Test without explicit limit
        query = LogEntryQuery()
        result = list_log_entries(query)

        # Verify default limit
        call_args = mock_paginate.call_args
        self.assertEqual(call_args[1]["maximum_records"], 100)

    @patch("pagerduty_mcp.tools.log_entries.get_client")
    @patch("pagerduty_mcp.tools.log_entries.paginate")
    def test_list_incident_log_entries_basic(self, mock_paginate, mock_get_client):
        """Test listing log entries for a specific incident."""
        # Setup mocks
        mock_paginate.return_value = [
            self.sample_trigger_log_entry_data,
            self.sample_acknowledge_log_entry_data,
            self.sample_log_entry_data,
        ]

        # Test
        query = IncidentLogEntryQuery()
        result = list_incident_log_entries("PINCIDENT123", query)

        # Assertions
        self.assertIsInstance(result, ListResponseModel)
        self.assertEqual(len(result.response), 3)
        self.assertIsInstance(result.response[0], LogEntry)

        # Verify correct endpoint was called
        call_args = mock_paginate.call_args
        self.assertEqual(call_args[1]["entity"], "incidents/PINCIDENT123/log_entries")
        self.assertEqual(call_args[1]["maximum_records"], 100)

    @patch("pagerduty_mcp.tools.log_entries.get_client")
    @patch("pagerduty_mcp.tools.log_entries.paginate")
    def test_list_incident_log_entries_with_filters(self, mock_paginate, mock_get_client):
        """Test listing incident log entries with filters."""
        # Setup mocks
        mock_paginate.return_value = [self.sample_log_entry_data]

        # Test with filters
        query = IncidentLogEntryQuery(
            is_overview=True,
            include=["incidents", "services", "channels"],
            limit=25,
        )
        result = list_incident_log_entries("PINCIDENT123", query)

        # Assertions
        self.assertEqual(len(result.response), 1)

        # Verify parameters were passed correctly
        call_args = mock_paginate.call_args
        params = call_args[1]["params"]
        self.assertEqual(params["is_overview"], "true")
        self.assertEqual(params["include[]"], ["incidents", "services", "channels"])
        self.assertEqual(call_args[1]["maximum_records"], 25)

    @patch("pagerduty_mcp.tools.log_entries.get_client")
    @patch("pagerduty_mcp.tools.log_entries.paginate")
    def test_list_incident_log_entries_time_range(self, mock_paginate, mock_get_client):
        """Test listing incident log entries within a time range."""
        # Setup mocks
        mock_paginate.return_value = [self.sample_log_entry_data]

        # Test with time range
        since_date = datetime(2023, 1, 1)
        until_date = datetime(2023, 1, 2)
        query = IncidentLogEntryQuery(since=since_date, until=until_date)
        result = list_incident_log_entries("PINCIDENT123", query)

        # Verify time parameters were passed
        call_args = mock_paginate.call_args
        params = call_args[1]["params"]
        self.assertEqual(params["since"], since_date.isoformat())
        self.assertEqual(params["until"], until_date.isoformat())
        self.assertEqual(params["time_zone"], "UTC")

    @patch("pagerduty_mcp.tools.log_entries.get_client")
    def test_get_log_entry_success(self, mock_get_client):
        """Test getting a specific log entry successfully."""
        # Setup mock
        mock_client = Mock()
        mock_client.rget.return_value = self.sample_log_entry_data
        mock_get_client.return_value = mock_client

        # Test
        result = get_log_entry("LOGENTRY123")

        # Assertions
        self.assertIsInstance(result, LogEntry)
        self.assertEqual(result.id, "LOGENTRY123")
        self.assertEqual(result.type, "resolve_log_entry")
        self.assertEqual(result.agent.id, "PUSER123")
        self.assertEqual(result.incident.id, "PINCIDENT123")
        mock_client.rget.assert_called_once_with("/log_entries/LOGENTRY123")

    @patch("pagerduty_mcp.tools.log_entries.get_client")
    def test_get_log_entry_api_error(self, mock_get_client):
        """Test get_log_entry with API error."""
        # Setup mock to raise exception
        mock_client = Mock()
        mock_client.rget.side_effect = Exception("API Error: Log entry not found")
        mock_get_client.return_value = mock_client

        # Test that exception is raised
        with self.assertRaises(Exception) as context:
            get_log_entry("LOGENTRY999")

        self.assertIn("API Error", str(context.exception))

    @patch("pagerduty_mcp.tools.log_entries.get_client")
    @patch("pagerduty_mcp.tools.log_entries.paginate")
    def test_list_log_entries_empty_result(self, mock_paginate, mock_get_client):
        """Test listing log entries with no results."""
        # Setup mocks
        mock_paginate.return_value = []

        # Test
        query = LogEntryQuery()
        result = list_log_entries(query)

        # Assertions
        self.assertIsInstance(result, ListResponseModel)
        self.assertEqual(len(result.response), 0)

    @patch("pagerduty_mcp.tools.log_entries.get_client")
    @patch("pagerduty_mcp.tools.log_entries.paginate")
    def test_list_incident_log_entries_empty_result(self, mock_paginate, mock_get_client):
        """Test listing incident log entries with no results."""
        # Setup mocks
        mock_paginate.return_value = []

        # Test
        query = IncidentLogEntryQuery()
        result = list_incident_log_entries("PINCIDENT999", query)

        # Assertions
        self.assertIsInstance(result, ListResponseModel)
        self.assertEqual(len(result.response), 0)

    def test_log_entry_query_to_params(self):
        """Test LogEntryQuery.to_params() method."""
        since_date = datetime(2023, 1, 1)
        until_date = datetime(2023, 1, 31)
        query = LogEntryQuery(
            since=since_date,
            until=until_date,
            is_overview=True,
            include=["incidents", "services"],
            limit=50,
        )

        params = query.to_params()

        self.assertEqual(params["since"], since_date.isoformat())
        self.assertEqual(params["until"], until_date.isoformat())
        self.assertEqual(params["is_overview"], "true")
        self.assertEqual(params["include[]"], ["incidents", "services"])
        self.assertEqual(params["limit"], 50)
        self.assertEqual(params["time_zone"], "UTC")

    def test_log_entry_query_to_params_minimal(self):
        """Test LogEntryQuery.to_params() with minimal parameters."""
        query = LogEntryQuery()
        params = query.to_params()

        self.assertEqual(params["time_zone"], "UTC")
        self.assertEqual(params["is_overview"], "false")
        self.assertNotIn("since", params)
        self.assertNotIn("until", params)
        self.assertNotIn("include[]", params)

    def test_incident_log_entry_query_to_params(self):
        """Test IncidentLogEntryQuery.to_params() method."""
        query = IncidentLogEntryQuery(
            is_overview=True,
            include=["channels", "teams"],
            limit=75,
        )

        params = query.to_params()

        self.assertEqual(params["is_overview"], "true")
        self.assertEqual(params["include[]"], ["channels", "teams"])
        self.assertEqual(params["limit"], 75)
        self.assertEqual(params["time_zone"], "UTC")

    @patch("pagerduty_mcp.tools.log_entries.get_client")
    def test_get_log_entry_with_channel(self, mock_get_client):
        """Test getting a log entry with channel information (notify_log_entry)."""
        # Setup mock with channel data
        log_entry_with_channel = {
            "id": "LOGENTRY999",
            "type": "notify_log_entry",
            "summary": "Notification sent",
            "self": "https://api.pagerduty.com/log_entries/LOGENTRY999",
            "created_at": "2023-01-01T00:00:00Z",
            "channel": {
                "type": "email",
                "summary": "user@example.com",
            },
            "incident": {
                "id": "PINCIDENT123",
                "type": "incident_reference",
                "summary": "Test Incident",
            },
        }

        mock_client = Mock()
        mock_client.rget.return_value = log_entry_with_channel
        mock_get_client.return_value = mock_client

        # Test
        result = get_log_entry("LOGENTRY999")

        # Assertions
        self.assertIsInstance(result, LogEntry)
        self.assertEqual(result.type, "notify_log_entry")
        self.assertIsNotNone(result.channel)
        self.assertEqual(result.channel.type, "email")
        self.assertEqual(result.channel.summary, "user@example.com")

    @patch("pagerduty_mcp.tools.log_entries.get_client")
    @patch("pagerduty_mcp.tools.log_entries.paginate")
    def test_list_log_entries_multiple_types(self, mock_paginate, mock_get_client):
        """Test listing log entries returns various log entry types correctly."""
        # Setup mocks with different log entry types
        escalate_log_entry = {
            "id": "LOGENTRY_ESC",
            "type": "escalate_log_entry",
            "summary": "Escalated to next level",
            "self": "https://api.pagerduty.com/log_entries/LOGENTRY_ESC",
            "created_at": "2023-01-01T01:00:00Z",
            "incident": {
                "id": "PINCIDENT123",
                "type": "incident_reference",
            },
        }

        annotate_log_entry = {
            "id": "LOGENTRY_ANN",
            "type": "annotate_log_entry",
            "summary": "Note added to incident",
            "self": "https://api.pagerduty.com/log_entries/LOGENTRY_ANN",
            "created_at": "2023-01-01T02:00:00Z",
            "agent": {
                "id": "PUSER789",
                "type": "user_reference",
                "summary": "Annotator User",
            },
            "incident": {
                "id": "PINCIDENT123",
                "type": "incident_reference",
            },
        }

        mock_paginate.return_value = [escalate_log_entry, annotate_log_entry]

        # Test
        query = LogEntryQuery()
        result = list_log_entries(query)

        # Assertions
        self.assertEqual(len(result.response), 2)
        self.assertEqual(result.response[0].type, "escalate_log_entry")
        self.assertEqual(result.response[1].type, "annotate_log_entry")

    @patch("pagerduty_mcp.tools.log_entries.get_client")
    @patch("pagerduty_mcp.tools.log_entries.paginate")
    def test_list_log_entries_with_teams_and_contexts(self, mock_paginate, mock_get_client):
        """Test log entries with teams and contexts fields."""
        # Setup mock with teams and contexts
        log_entry_with_extras = {
            "id": "LOGENTRY_FULL",
            "type": "trigger_log_entry",
            "summary": "Incident triggered with context",
            "self": "https://api.pagerduty.com/log_entries/LOGENTRY_FULL",
            "created_at": "2023-01-01T00:00:00Z",
            "incident": {
                "id": "PINCIDENT123",
                "type": "incident_reference",
            },
            "teams": [
                {"id": "PTEAM123", "type": "team_reference", "summary": "Team A"},
                {"id": "PTEAM456", "type": "team_reference", "summary": "Team B"},
            ],
            "contexts": [
                {"type": "link", "href": "https://example.com/issue/123"},
            ],
            "event_details": {
                "description": "Server CPU usage critical",
            },
        }

        mock_paginate.return_value = [log_entry_with_extras]

        # Test
        query = LogEntryQuery(include=["teams"])
        result = list_log_entries(query)

        # Assertions
        self.assertEqual(len(result.response), 1)
        entry = result.response[0]
        self.assertIsNotNone(entry.teams)
        self.assertEqual(len(entry.teams), 2)
        self.assertIsNotNone(entry.contexts)
        self.assertIsNotNone(entry.event_details)


if __name__ == "__main__":
    unittest.main()
