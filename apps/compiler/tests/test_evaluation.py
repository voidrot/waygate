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
    assert all(result.passed for result in summary.results)


def test_evaluate_candidate_detects_regression() -> None:
    dataset = evaluation.load_golden_dataset()

    summary = evaluation.evaluate_candidate(
        dataset,
        lambda _case: "Certainly! Here is the summary.\nNo relevant markdown sections.",
    )

    assert summary.passed is False
    assert summary.failed_cases == len(summary.results)
    assert any("missing required grounded facts" in result.failures for result in summary.results)


def test_build_draft_node_candidate_runs_through_draft_node() -> None:
    dataset = evaluation.load_golden_dataset()
    case = dataset.cases[0]
    fake_llm = _StaticLLM(case.expected_output)

    candidate = evaluation.build_draft_node_candidate(lambda _case: fake_llm)
    output = candidate(case)

    assert output == case.expected_output
    assert fake_llm.messages is not None
    assert case.target_topic in fake_llm.messages[0].content