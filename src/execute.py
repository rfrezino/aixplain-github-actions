from typing import Optional, List

from chatgpt import ChatGPT
from github_pr import GithubPR
from google_gemini import GoogleGemini


def _generate_list_from_string(string: str) -> List[str]:
    return [x.strip() for x in string.split(";") if x.strip()]


def execute(
    github_repository: str,
    github_token: str,
    pr_number: int,
    openai_token: Optional[str],
    google_gemini_token: Optional[str],
    ignore_files_with_content: str,
    ignore_files_in_path: str,
    instructions: str,
    google_project_name: str = "",
    google_model_name: str = "",
):
    if openai_token is None and google_gemini_token is None:
        raise ValueError("You need to provide at least one AI Token")

    print(f"Github Repository: {github_repository}")
    github_pr = GithubPR(
        repository_name=github_repository,
        github_token=github_token,
        pr_number=pr_number,
    )

    ignore_files_with_content_list = _generate_list_from_string(
        ignore_files_with_content
    )
    ignore_files_in_path_list = _generate_list_from_string(ignore_files_in_path)
    instructions_list = _generate_list_from_string(instructions)

    if openai_token is not None and openai_token != "":
        print("Using ChatGPT")
        chatgpt = ChatGPT(
            github_pr=github_pr,
            openai_token=openai_token,
            ignore_files_with_content=ignore_files_with_content_list,
            ignore_files_in_paths=ignore_files_in_path_list,
            instructions=instructions_list,
        )
        chatgpt.execute()
    else:
        print("Using Google Gemini")
        google_gemini = GoogleGemini(
            github_pr=github_pr,
            google_gemini_token=google_gemini_token,
            ignore_files_with_content=ignore_files_with_content_list,
            ignore_files_in_paths=ignore_files_in_path_list,
            instructions=instructions_list,
            google_project_name=google_project_name,
            model_name=google_model_name,
        )

        google_gemini.execute()
