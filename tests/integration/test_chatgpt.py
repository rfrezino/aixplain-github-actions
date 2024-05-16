import os

from dotenv import load_dotenv

from src.execute import execute


class TestMain:
    def test_execute_local_dev_test(self):
        load_dotenv()
        github_token = os.getenv("GITHUB_TOKEN")
        openai_token = os.getenv("OPENAI_TOKEN")
        freshbooks_repository = os.getenv("GITHUB_REPOSITORY")
        pr_number = int(os.getenv("PR_NUMBER"))
        openai_token = None
        google_token = "any"

        ignore_files_with_content = "# Generated by FreshCLI."
        ignore_files_in_path = (
            "*pyproject.toml;*requirements.txt;*Pipfile;*Pipfile.lock"
        )

        execute(
            github_repository=freshbooks_repository,
            github_token=github_token,
            pr_number=pr_number,
            openai_token=openai_token,
            google_gemini_token=google_token,
            ignore_files_with_content=ignore_files_with_content,
            ignore_files_in_path=ignore_files_in_path,
        )
