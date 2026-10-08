from __future__ import annotations

import pytest

from gridshare import cli

pytestmark = pytest.mark.chain


def test_demo_runs_end_to_end(capsys):
    cli.demo()
    out = capsys.readouterr().out
    assert "Deploying GridLedger" in out
    assert "peer-to-peer energy traded" in out
    assert "settled on-chain" in out
    assert "total trades on-chain" in out


def test_main_dispatches_demo(monkeypatch):
    called = {"demo": False}
    monkeypatch.setattr(cli, "demo", lambda: called.__setitem__("demo", True))
    monkeypatch.setattr("sys.argv", ["gridshare", "demo"])
    cli.main()
    assert called["demo"] is True
