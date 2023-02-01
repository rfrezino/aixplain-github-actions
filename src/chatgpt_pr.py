from typing import List

import openai
from github.File import File

from src.github_pr import GithubPR


class ChatGPTPr:
    _github_pr: GithubPR

    def __init__(self, github_pr: GithubPR, openai_token: str):
        openai.api_key = openai_token
        self._github_pr = github_pr

    def execute(self):
        files = self._get_latest_file_version_from_commits()
        self._github_pr.remove_old_comments()
        comments = self._generate_comments(files)
        self._github_pr.add_comments(comments)

    def _generate_comments(self, files: List[File]) -> List[str]:
        comments = []
        for file in files:
            comments.append(self._generate_comment(file))
        return comments

    def _get_latest_file_version_from_commits(self) -> List[File]:
        commits = self._github_pr.get_pr_commits()
        files = {}
        for commit in commits:
            for file in commit.files:
                files[file.filename] = file

        return list(files.values())

    def _generate_comment(self, file: File) -> str:
        file_content = file.decoded_content
        if file.filename.endswith(".py"):
            request = f"Explain this Code and give suggestions to improve it if any:\n```{file_content}```"
        elif file.filename.endswith(".md"):
            request = f"Check for spelling and text comprehension and give suggestions if any:\n```{file_content}```"
        elif '.' in file.filename:
            file_suffix = file.filename.split(".")[-1]
            request = f"Considering it's an {file_suffix} check it considering the good practices for this type of content:\n```{file_content}```"
        else:
            request = f"Check this file and give suggestions if any:\n```{file_content}```"

        response = openai.Completion.create(
            engine="text-davinci-003",
            prompt=request,
            temperature=0.6,
            max_tokens=2048
        )

        final_comment = f"[AIxplain Comment]\n{response['choices'][0]['text']}"
        return final_comment
