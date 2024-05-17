import fnmatch
from typing import List

import openai

from github_pr import GithubPR
from ai_assistent import AiAssistent, LatestFile


class ChatGPT(AiAssistent):
    _github_pr: GithubPR
    MAX_TOKENS = 4097

    def __init__(
        self,
        github_pr: GithubPR,
        openai_token: str,
        ignore_files_with_content: List[str],
        ignore_files_in_paths: List[str],
        instructions: List[str],
    ):
        super().__init__(
            github_pr=github_pr,
            ignore_files_with_content=ignore_files_with_content,
            ignore_files_in_paths=ignore_files_in_paths,
            instructions=instructions,
        )
        openai.api_key = openai_token

    def _generate_comment(self, latest_file: LatestFile, instructions: str) -> str:
        header = f"{self.COMMENT_HEADER}\n#### File: _{{file}}_\n{self.SHA_HEADER} {{sha}} {self.SHA_HEADER_ENDING}\n----\n{{response}}"
        file = latest_file.file
        print(f"Generating comment for file: {file.filename}")
        commit = latest_file.commit
        try:
            file_content = self._github_pr.get_content_for_file(file, commit)

            if self._ignore_files_with_content:
                for ignore_content in self._ignore_files_with_content:
                    if ignore_content in file_content:
                        print(
                            f"{file.filename}: File content contains {ignore_content}, skipping it"
                        )
                        return ""
        except Exception as e:
            print(f"Error while getting content for file: {e}")
            return header.format(
                file=file.filename,
                sha=file.sha,
                response=f"Error while getting content for file: {e}",
            )

        ai_input = f"""
This is the whole file content:
```
{file_content}
```

And these are the changes you need to review, they are in git diff format:
```
{file.patch}
```
"""

        tokens = self._get_number_of_tokens_in_content(ai_input)
        if tokens == -1:
            print(f"File is too long to generate a comment: {file.filename}")
            return header.format(
                file=file.filename,
                sha=file.sha,
                response="File is too long to generate a comment.",
            )

        try:
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": instructions},
                    {"role": "user", "content": ai_input},
                ],
            )

        except Exception as e:
            if "maximum context length" in str(e):
                print(f"File is too long to generate a comment: {file.filename}")
                return header.format(
                    file=file.filename,
                    sha=file.sha,
                    response="File is too long to generate a comment.",
                )
            else:
                print(f"Error while generating information: {e}")
                return header.format(
                    file=file.filename,
                    sha=file.sha,
                    response=f"Error while generating information: {e}",
                )

        comment = response["choices"][0]["message"]["content"]

        final_comment = header.format(
            file=file.filename, sha=file.sha, response=comment
        )
        print(f"Generated comment for file: {file.filename}")
        return final_comment
