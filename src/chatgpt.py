import fnmatch
from typing import List

import openai

from github_pr import GithubPR
from src.ai_assistent import AiAssistent, LatestFile


class ChatGPT(AiAssistent):
    _github_pr: GithubPR
    MAX_TOKENS = 4097

    def __init__(self, github_pr: GithubPR, openai_token: str, ignore_files_with_content: List[str],
                 ignore_files_in_paths: List[str]):
        super().__init__(github_pr=github_pr,
                         ignore_files_with_content=ignore_files_with_content,
                         ignore_files_in_paths=ignore_files_in_paths)
        openai.api_key = openai_token

    def _generate_comment(self, latest_file: LatestFile) -> str:
        if any([fnmatch.fnmatch(latest_file.file.filename, path) for path in self._ignore_files_in_paths]):
            print(f'{latest_file.file.filename} is under an ignored path, skipping it.')
            return ""

        header = f"{self.COMMENT_HEADER}\n#### File: _{{file}}_\n#### SHA: _{{sha}}_\n----\n{{response}}"
        file = latest_file.file
        print(f"Generating comment for file: {file.filename}")
        commit = latest_file.commit
        try:
            file_content = self._github_pr.get_content_for_file(file, commit)

            if self._ignore_files_with_content is not None and self._ignore_files_with_content != "" and self._ignore_files_with_content in file_content:
                print(f"{file.filename}: File content contains {self._ignore_files_with_content}, skipping it")
                return ""
        except Exception as e:
            print(f"Error while getting content for file: {e}")
            return header.format(file=file.filename, sha=file.sha,
                                 response=f"Error while getting content for file: {e}")

        if file.filename.endswith(".py"):
            content = 'You are a Python Enginner and you are reviewing a pull request. You reviews needs to: 1. Describe what this file does; 2. Check if the code has any problem or points for improvement, and if any, demonstrate how to improve or fix it;'
        elif file.filename.endswith(".md"):
            content = 'You are a Technical Writer and you are reviewing documentation. You reviews needs to: Check if the text is clear, check for typos and other problems and if you find anything give suggestions to improve it If possible add examples based on the code.'
        elif '.' in file.filename:
            file_suffix = file.filename.split(".")[-1]
            content = f'You are checking a file with the type {file_suffix}, based in the recommendations for this file type you need to: 1. Describe what this file does; 2. Check if there is any problems in the code and if any suggest corrections If possible add examples based on its content.'
        else:
            content = "1. Describe what this file does \n2. Check if this file has any problems and if any suggest corrections:"

        content = f'{content} \n If possible put your answer in markdown format.'
        tokens = self._get_number_of_tokens_in_content(file_content)
        if tokens == -1:
            print(f"File is too long to generate a comment: {file.filename}")
            return header.format(file=file.filename, sha=file.sha, response="File is too long to generate a comment.")

        try:
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",

                messages=[
                    {"role": "system",
                     "content": content},
                    {"role": "user", "content": file_content},
                ]

            )

        except Exception as e:
            if 'maximum context length' in str(e):
                print(f"File is too long to generate a comment: {file.filename}")
                return header.format(file=file.filename, sha=file.sha,
                                     response="File is too long to generate a comment.")
            else:
                print(f"Error while generating information: {e}")
                return header.format(file=file.filename, sha=file.sha,
                                     response=f"Error while generating information: {e}")

        comment = response['choices'][0]['message']['content']

        final_comment = header.format(file=file.filename, sha=file.sha, response=comment)
        print(f"Generated comment for file: {file.filename}")
        return final_comment
