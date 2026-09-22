import json
from pathlib import Path

import pytest

from pyrefly.private.wrapper import cli, display_warnings


@pytest.mark.parametrize(
    ("expected_failure", "exit_code", "has_warnings", "expected_output"),
    [
        (True, 1, False, "Pyrefly findings\n"),
        (False, 0, True, "Pyrefly findings\n"),
        (False, 1, False, ""),
        (True, 0, False, ""),
    ],
)
def test_relevant_fulltext_output_is_printed_and_marked(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    expected_failure: bool,
    exit_code: int,
    has_warnings: bool,
    expected_output: str,
) -> None:
    """Only expected failures and warning findings are printed to stdout."""
    check_marker = tmp_path / "check.marker"
    check_marker.write_text(
        json.dumps(
            {
                "expected_failure": expected_failure,
                "exit_code": exit_code,
                "has_warnings": has_warnings,
            }
        )
    )
    fulltext_output = tmp_path / "fulltext.txt"
    fulltext_output.write_text("Pyrefly findings\n")
    output_marker = tmp_path / "outputs" / "display.marker"

    assert (
        display_warnings.run(
            cli.DisplayWarningsOptions(
                output_marker=output_marker,
                check_marker=check_marker,
                fulltext_output=fulltext_output,
            )
        )
        == 0
    )

    captured = capsys.readouterr()
    assert captured.out == expected_output
    assert captured.err == ""
    assert output_marker.is_file()
