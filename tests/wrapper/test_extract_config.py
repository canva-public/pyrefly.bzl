from __future__ import annotations

import tomllib
from pathlib import Path

import pytest

from pyrefly.private.wrapper import cli, extract_config


def test_extract_config_writes_only_pyrefly_policy(tmp_path: Path) -> None:
    """Extraction drops unrelated project and tool configuration."""
    source = tmp_path / "pyproject.toml"
    source.write_text(
        '[project]\nname = "consumer"\n'
        "[tool.pyrefly]\nignore-missing-imports = true\n"
        '[tool.pyrefly.errors]\nmissing-import = "warn"\n'
        "[tool.unrelated]\nenabled = true\n"
    )
    output = tmp_path / "effective" / "pyrefly.toml"

    assert (
        extract_config.run(
            cli.ExtractConfigOptions(
                input_config=source,
                output_config=output,
            )
        )
        == 0
    )

    assert tomllib.loads(output.read_text()) == {
        "ignore-missing-imports": True,
        "errors": {"missing-import": "warn"},
    }


@pytest.mark.parametrize(
    ("content", "message"),
    [
        ('[project]\nname = "consumer"\n', "does not contain a [tool.pyrefly] table"),
        ('tool = "not-a-table"\n', "does not contain a [tool.pyrefly] table"),
        ("[tool.pyrefly\nstrict = true\n", "Unable to read"),
    ],
)
def test_extract_config_reports_invalid_pyproject(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    content: str,
    message: str,
) -> None:
    """Malformed or policy-free pyprojects fail with an actionable message."""
    source = tmp_path / "pyproject.toml"
    source.write_text(content)
    output = tmp_path / "pyrefly.toml"

    result = cli.main(
        [
            "extract-config",
            "--input-config",
            str(source),
            "--output-config",
            str(output),
        ]
    )

    assert result == cli.INFRASTRUCTURE_EXIT_CODE
    assert message in capsys.readouterr().err
    assert not output.exists()
