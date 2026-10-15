from datetime import date

from estado import health as H

TODAY = date(2026, 10, 15)


def _wf(path=".github/workflows/diario.yml", state="active", conclusion="success"):
    return {"path": path, "state": state,
            "last": conclusion and {"conclusion": conclusion, "date": "2026-10-15", "url": "https://run"}}


def test_scheduled_ignores_commented_cron():
    assert H.scheduled("on:\n  schedule:\n    - cron: \"0 5 * * *\"\n")
    assert not H.scheduled("on:\n  # schedule:\n  #   - cron: \"0 5 15 9 *\"\n  workflow_dispatch:\n")


def test_workflow_findings():
    found = H.workflow_findings("r", TODAY, [_wf(), _wf("a/b/fallo.yml", conclusion="failure"),
                                             _wf("a/b/apagado.yml", state="disabled_inactivity"),
                                             _wf("a/b/mano.yml", state="disabled_manually"),
                                             _wf("a/b/nuevo.yml", conclusion=None)], TODAY)
    by = {f.key: f for f in found}
    assert set(by) == {"r:fallo.yml:fallo", "r:apagado.yml:inactivo", "r:mano.yml:disabled_manually"}
    assert by["r:mano.yml:disabled_manually"].level == "info"
    assert "gh workflow enable apagado.yml" in by["r:apagado.yml:inactivo"].text


def test_inactivity_warns_before_github_turns_the_cron_off():
    assert not H.workflow_findings("r", date(2026, 9, 1), [_wf()], TODAY)
    found = H.workflow_findings("r", date(2026, 8, 20), [_wf()], TODAY)
    assert [f.key for f in found] == ["r:inactividad"] and found[0].level == "aviso"
    assert not H.workflow_findings("r", date(2026, 1, 1), [_wf(state="disabled_manually")], TODAY)[1:]


def _doc(generated="2026-10-15T07:00Z", kind="fire"):
    return {"source": "r", "version": 1, "generated": generated, "coverage": {"label": "x", "sites": None},
            "signals": [{"id": "1", "kind": kind, "date": "2026-10-01", "title": "t", "url": "https://x",
                         "precision": "municipio", "municipalities": ["01001"]}]}


def test_signals_findings():
    assert not H.signals_findings("r", _doc(), TODAY, 3, True)
    assert [f.level for f in H.signals_findings("r", None, TODAY, 3, True)] == ["info"]
    assert not H.signals_findings("r", None, TODAY, 3, False)
    assert [f.key for f in H.signals_findings("r", _doc("2026-10-01T07:00Z"), TODAY, 3, True)] == ["r:viejo"]
    assert not H.signals_findings("r", _doc("2026-10-01T07:00Z"), TODAY, None, True)
    assert [f.key for f in H.signals_findings("r", _doc(kind="water_status"), TODAY, 3, True)] == ["r:tipo:water_status"]


def test_issue_plan():
    assert H.issue_plan(None, []) == "nothing"
    assert H.issue_plan(None, ["a"]) == "create"
    assert H.issue_plan(["a"], ["a"]) == "refresh"
    assert H.issue_plan(["a"], ["a", "b"]) == "comment"
    assert H.issue_plan(["a"], []) == "close"


def test_report_lists_the_quiet_ones():
    text = H.report([H.Finding("a", "error", "a:x", "roto"), H.Finding("b", "info", "b:y", "nota")], ["a", "b"], TODAY)
    assert "**a**: roto" in text and "## Sin novedad\n\nb" in text and "<details>" in text
