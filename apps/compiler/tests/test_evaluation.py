from compiler import evaluation


class _StaticLLM:
    def __init__(self, content: str) -> None:
        self.content = content
        self.messages = None

    def invoke(self, messages):
        self.messages = messages

        class _Response:
            def __init__(self, content: str) -> None:
                self.content = content

        return _Response(self.content)


def test_load_default_golden_dataset() -> None:
    dataset = evaluation.load_golden_dataset()

    assert dataset.version == "1"
    assert len(dataset.cases) >= 2
    assert dataset.cases[0].required_snippets


def test_evaluate_candidate_passes_reference_outputs() -> None:
    dataset = evaluation.load_golden_dataset()

    summary = evaluation.evaluate_candidate(
        dataset,
        lambda case: case.expected_output,
    )

    assert summary.passed is True
    assert summary.failed_cases == 0
    assert summary.average_metrics.grounding == 1.0
    assert all(result.passed for result in summary.results)


def test_evaluate_candidate_detects_regression() -> None:
    dataset = evaluation.load_golden_dataset()

    summary = evaluation.evaluate_candidate(
        dataset,
        lambda _case: "Certainly! Here is the summary.\nNo relevant markdown sections.",
    )

    assert summary.passed is False
    assert summary.failed_cases == len(summary.results)
    assert any(
        "missing required grounded facts" in result.failures
        for result in summary.results
    )


def test_build_draft_node_candidate_runs_through_draft_node() -> None:
    dataset = evaluation.load_golden_dataset()
    case = dataset.cases[0]
    fake_llm = _StaticLLM(case.expected_output)

    candidate = evaluation.build_draft_node_candidate(lambda _case: fake_llm)
    output = candidate(case)

    assert output == case.expected_output
    assert fake_llm.messages is not None
    assert case.target_topic in fake_llm.messages[0].content


def test_write_evaluation_report_and_candidate_outputs(tmp_path) -> None:
    dataset = evaluation.load_golden_dataset()
    summary = evaluation.evaluate_candidate(
        dataset,
        lambda case: case.expected_output,
    )

    report_path = evaluation.write_evaluation_report(
        summary,
        tmp_path / "reports" / "eval.json",
    )
    output_paths = evaluation.write_candidate_outputs(
        summary,
        tmp_path / "candidates",
    )

    assert report_path.exists()
    assert '"passed": true' in report_path.read_text(encoding="utf-8")
    assert len(output_paths) == len(summary.results)
    assert all(path.exists() for path in output_paths)
    assert output_paths[0].read_text(encoding="utf-8").startswith("# ")


def test_main_writes_report_and_candidates(monkeypatch, tmp_path, capsys) -> None:
    dataset = evaluation.load_golden_dataset()

    monkeypatch.setattr(
        evaluation,
        "_build_live_candidate_runner",
        lambda _provider, _model: lambda case: case.expected_output,
    )

    report_path = tmp_path / "artifacts" / "eval.json"
    candidates_dir = tmp_path / "artifacts" / "candidates"

    exit_code = evaluation.main(
        [
            "--dataset",
            str(evaluation.DEFAULT_GOLDEN_DATASET_PATH),
            "--report-path",
            str(report_path),
            "--write-candidates-dir",
            str(candidates_dir),
        ]
    )

    captured = capsys.readouterr()
    assert exit_code == 0
    assert '"passed": true' in captured.out
    assert report_path.exists()
    assert len(list(candidates_dir.glob("*.md"))) == len(dataset.cases)


def test_main_returns_nonzero_for_regression(monkeypatch, capsys) -> None:
    monkeypatch.setattr(
        evaluation,
        "_build_live_candidate_runner",
        lambda _provider, _model: (
            lambda _case: (
                "Certainly! Here is the summary.\nNo relevant markdown sections."
            )
        ),
    )

    exit_code = evaluation.main(
        [
            "--dataset",
            str(evaluation.DEFAULT_GOLDEN_DATASET_PATH),
        ]
    )

    captured = capsys.readouterr()
    assert exit_code == 1
    assert '"passed": false' in captured.out
