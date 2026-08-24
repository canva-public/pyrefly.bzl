from pathlib import Path

import pytest

from pyrefly.private.wrapper import cli, display_warnings


def test_warning_report_is_printed_and_marked(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """The display action prints its report and creates its requested output."""
    warning_file = tmp_path / "warning.txt"
    warning_file.write_text("[PYREFLY] [WARNING] expected failure\n")
    output_marker = tmp_path / "outputs" / "display.marker"

    assert (
        display_warnings.run(
            cli.DisplayWarningsOptions(
                output_marker=output_marker,
                warning_file=warning_file,
            )
        )
        == 0
    )

    captured = capsys.readouterr()
    assert captured.err == "[PYREFLY] [WARNING] expected failure\n"
    assert output_marker.is_file()
