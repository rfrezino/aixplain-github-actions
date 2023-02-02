from dataclasses import dataclass
from typing import List

import openai
from github.Commit import Commit
from github.File import File

from github_pr import GithubPR


@dataclass
class LatestFile:
    file: File
    commit: Commit


class ChatGPT:
    _github_pr: GithubPR

    def __init__(self, github_pr: GithubPR, openai_token: str):
        openai.api_key = openai_token
        self._github_pr = github_pr

    def execute(self):
        files = self._get_latest_file_version_from_commits()
        self._github_pr.remove_old_comments()
        comments = self._generate_comments(files)
        self._github_pr.add_comments(comments)

    def _generate_comments(self, files: List[LatestFile]) -> List[str]:
        comments = []
        for file in files:
            comments.append(self._generate_comment(file))
        return comments

    def _get_latest_file_version_from_commits(self) -> List[LatestFile]:
        commits = self._github_pr.get_pr_commits()
        files = {}
        for commit in commits:
            for file in commit.files:
                latest_file = LatestFile(file=file, commit=commit)
                files[file.filename] = latest_file

        return list(files.values())

    def _get_number_of_tokens_in_content(self, content: str) -> int:
        MAX_TOKENS = 4097

        # 1500 words in content = 2048 tokens
        # where maximum is 4000 tokens, if content is longer than 4000 tokens, it will return -1
        number_of_tokens = int(len(content.split(" ")) / 1500 * 2048)
        if number_of_tokens > MAX_TOKENS:
            return -1

        # increase 10%
        number_of_tokens = int(number_of_tokens * 1.40)
        if number_of_tokens > MAX_TOKENS:
            return MAX_TOKENS
        return number_of_tokens

    def _generate_comment(self, latest_file: LatestFile) -> str:
        header = "### AIxplain Comment\n#### File: _{file}_\n----\n{response}"
        file = latest_file.file
        print(f"Generating comment for file: {file.filename}")
        commit = latest_file.commit
        file_content = self._github_pr.get_content_for_file(file, commit)

        if file.filename.endswith(".py"):
            request = f"1. Describe what this file does \n2. Considering it's Python code, check if this file has any problems and if any suggest corrections:\n```{file_content}```"
        elif file.filename.endswith(".md"):
            request = f"Check if the text is clear, check for typos and other problems and if you find anything give suggestions to improve it:\n```{file_content}```"
        elif '.' in file.filename:
            file_suffix = file.filename.split(".")[-1]
            request = f"1. Describe what this file does \n2. Considering it's an {file_suffix} file, check if this file has any problems and if any suggest corrections:\n```{file_content}```"
        else:
            request = f"1. Describe what this file does \n2. Check if this file has any problems and if any suggest corrections:\n```{file_content}```"

        request = f'{request} \n If possible put your answer in markdown format.'
        tokens = self._get_number_of_tokens_in_content(request)
        if tokens == -1:
            print(f"File is too long to generate a comment: {file.filename}")
            return header.format(file=file.filename, response=f"File is too long to generate a comment.")

        try:
            response = openai.Completion.create(
                engine="text-davinci-003",
                prompt=request,
                temperature=0.6,
                max_tokens=tokens,
            )
        except Exception as e:
            if 'maximum context length' in str(e):
                print(f"File is too long to generate a comment: {file.filename}")
                return header.format(file=file.filename, response=f"File is too long to generate a comment.")
            else:
                print(f"Error while generating information: {e}")
                return header.format(file=file.filename, response=f"Error while generating information: {e}")

        final_comment = header.format(file=file.filename, response=response['choices'][0]['text'])
        print(f"Generated comment for file: {file.filename}")
        return final_comment
