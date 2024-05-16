from unittest.mock import Mock

import pytest

from ai_assistent import AiAssistent, LatestFile


class _StubAiAssistent(AiAssistent):
    def _generate_comment(self, latest_file: LatestFile) -> str:
        pass


class TestAiAssistent:
    @pytest.mark.parametrize(
        "file, result",
        (
            ("something/pyproject.toml", True),
            ("something/requirements.txt", True),
            ("something/Pipfile", True),
            ("something/Pipfile.lock", True),
            ("something/setup.py", False),
            ("something/src/main.py", False),
            ("something/src/tests/test_main.py", False),
        ),
    )
    def test_should_file_be_ignored(self, file: str, result: bool) -> None:
        client = _StubAiAssistent(
            github_pr=Mock(),
            ignore_files_with_content=[],
            ignore_files_in_paths=[
                "*pyproject.toml",
                "*requirements.txt",
                "*Pipfile",
                "*Pipfile.lock",
            ],
        )

        assert client._should_file_be_ignored(file) == result
