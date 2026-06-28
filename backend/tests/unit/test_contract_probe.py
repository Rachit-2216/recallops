from scripts.cognee_contract_probe import main


def test_probe_is_hard_gated_by_environment(
    monkeypatch,
    capsys,
) -> None:
    monkeypatch.delenv("RUN_COGNEE_INTEGRATION", raising=False)

    exit_code = main(["--read-only"])

    assert exit_code == 0
    assert capsys.readouterr().out.strip() == (
        "Live Cognee probe skipped: set RUN_COGNEE_INTEGRATION=1"
    )
