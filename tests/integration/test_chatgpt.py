import os

from dotenv import load_dotenv

from main import execute


class TestMain:
    def test_execute_local_dev_test(self):
        load_dotenv()
        github_token = os.getenv("GITHUB_TOKEN")
        openai_token = os.getenv("OPENAI_TOKEN")
        freshbooks_repository = os.getenv("GITHUB_REPOSITORY")
        pr_number = int(os.getenv("PR_NUMBER"))

        execute(github_repository=freshbooks_repository,
                github_token=github_token,
                pr_number=pr_number,
                openai_token=openai_token)