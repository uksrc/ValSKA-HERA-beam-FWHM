"""Tests for valska-bayeseor-help command index CLI."""

from __future__ import annotations

import json

from valska.external_tools.bayeseor import cli_help


def test_cli_help_json_contains_catalog_and_workflows(capsys) -> None:
    code = cli_help.main(["--json"])
    assert code == 0

    payload = json.loads(capsys.readouterr().out)
    commands = payload["commands"]
    names = {row["command"] for row in commands}

    assert payload["topic_filter"] is None
    assert "setup" in payload["available_topics"]
    assert "operations" in payload["available_topics"]
    assert "valska-bayeseor-prepare" in names
    assert "valska-bayeseor-cleanup" in names
    assert len(payload["workflows"]) >= 4


def test_cli_help_topic_filter_json(capsys) -> None:
    code = cli_help.main(["--topic", "reporting", "--json"])
    assert code == 0

    payload = json.loads(capsys.readouterr().out)
    commands = payload["commands"]

    assert payload["topic_filter"] == "reporting"
    assert len(commands) == 1
    assert commands[0]["command"] == "valska-bayeseor-report"
    assert commands[0]["topic"] == "reporting"


def test_cli_help_text_output_mentions_roadmap(capsys) -> None:
    code = cli_help.main([])
    assert code == 0

    out = capsys.readouterr().out
    assert "BayesEoR command index:" in out
    assert "valska-bayeseor-help" not in out
    assert "single root 'valska-bayeseor' command with subcommands" in out
