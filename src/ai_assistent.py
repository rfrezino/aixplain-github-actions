import fnmatch
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import List

from github.IssueComment import IssueComment

from github_pr import GithubPR
from github.Commit import Commit
from github.File import File


@dataclass
class LatestFile:
    file: File
    commit: Commit


@dataclass
class FileInstructions:
    file_match: str
    instructions: str


class AiAssistent(ABC):
    COMMENT_HEADER = "### AIxplain Comment"
    SHA_HEADER = "<!--#### SHA:"
    SHA_HEADER_ENDING = "-->"
    _github_pr: GithubPR
    _ignore_files_with_content: List[str]
    _ignore_files_in_paths: List[str]
    _file_instructions: List[FileInstructions]
    MAX_TOKENS = 0

    def __init__(
        self,
        github_pr: GithubPR,
        ignore_files_with_content: List[str],
        ignore_files_in_paths: List[str],
    ) -> None:
        self._github_pr = github_pr
        self._ignore_files_with_content = ignore_files_with_content
        self._ignore_files_in_paths = ignore_files_in_paths
        self._file_instructions = self._generate_file_instructions()

    @staticmethod
    def _generate_file_instructions() -> List[FileInstructions]:
        header = """You are a senior python developer and you are reviewing a pull request.
These are the guidelines:
1. You need to add comments for content that is not clear or has problems.
2. You need to be succinct and clear in your comments.
3. If you find any problem, you must provide a solution or suggestion.
4. If possible, add examples based on the code.
5. If you found no problems, reply with "All Good Here!".
6. Don't be verbose, write what is necessary.
7. Don't print the whole code again, just the parts specified in the comments.
8. Just comment about the code in Git Diff, and not about the whole file.
9. Respond in a constructive way.

Example for a good comment:
1. Put the comments in a list
2. Explain what can be improved.
3. Show just the part of the code that needs to be improved.
4. Provide a suggestion to fix it with an example.

This is an input example:

```code
This is the whole code: 

parameters:
 - name: dev_image_tag
  type: string
 - name: image
  type: string
 - name: coverage_target
  type: string
 - name: ci_docker_compose_file
  type: string
- name: ci_docker_compose_coverage_targ
  type: string
  default: 'coverage'
  
This is what you need to improve:

--- a/file.yaml
+++ b/file.yaml
@@ -6,4 +6,8 @@ parameters:
  - name: coverage_target
   type: string
  - name: ci_docker_compose_file
-  type: string
+  type: string
+- name: ci_docker_compose_coverage_targ
+  type: string
+  default: 'coverage'

```

This is a result example:
``` 
1. **YAML indentation consistency**
   ```yaml
   - name: dev_image_tag
     type: string
   ```
   - The indentation of elements under `parameters` is inconsistent. YAML files are sensitive to indentation as it determines the structure of the data.
   - **Suggestion:** Ensure consistent indentation across all elements for clarity and to avoid parsing errors.

2. **The variable name can be explicit for redability**
   ```yaml
- name: ci_docker_compose_coverage_targ
  type: string
  default: 'coverage'
   ```
   - Tha variable `ci_docker_compose_coverage_targ` can be more explicit to do not cause confusion.
   - **Suggestion:** Change the variable name to `ci_docker_compose_coverage_target` for better readability.
```

Some specifics for this file type: {specifics} 
"""

        py_instructions = FileInstructions(
            file_match="*.py",
            instructions=header.format(specifics="You are reviewing a Python file."),
        )
        md_instructions = FileInstructions(
            file_match="*.md",
            instructions=header.format(
                specifics="heck if the text is clear, check for typos and other problems and if you find anything give suggestions to improve"
            ),
        )
        file_with_extension_instructions = FileInstructions(
            file_match="*.*",
            instructions=header.format(
                specifics="You are checking a file with the type {file_suffix}, you know the recommendations for this file."
            ),
        )
        default_instructions = FileInstructions(
            file_match="*",
            instructions=header.format(
                specifics="Based on the type of this file, check it based on the best practices."
            ),
        )

        result = [
            py_instructions,
            md_instructions,
            file_with_extension_instructions,
            default_instructions,
        ]

        appended_instructions = "\n This is the file name {file_name}. Put the response in plain markdown format."
        for instruction in result:
            instruction.instructions = (
                f"{instruction.instructions} {appended_instructions}"
            )

        return result

    @abstractmethod
    def _generate_comment(self, latest_file: LatestFile, instructions: str) -> str:
        pass

    def execute(self):
        print("Getting PR information")
        pr_author = self._github_pr.get_pr_author_login()
        if "dependabot" in pr_author:
            print("Dependabot PR, skipping")
            exit(0)

        print("Getting all files from PR")
        all_files = self._get_latest_file_version_from_commits()
        print("Getting all bot comments")
        all_bot_comments = self.get_all_bot_comments()
        print("Removing deprecated comments")
        remaining_comments = self._remove_deprecated_comments(
            all_files, all_bot_comments
        )
        print("Generating new comments")
        files_to_comment = self._get_files_to_comment(all_files, remaining_comments)
        comments = self._generate_comments(files_to_comment)
        print("Adding new comments")
        self._github_pr.add_comments(comments)

    def _get_latest_file_version_from_commits(self) -> List[LatestFile]:
        files_in_pr = [f.filename for f in self._github_pr.get_files()]
        commits = self._github_pr.get_pr_commits()
        files = {}
        for commit in commits:
            for file in commit.files:
                if file.filename not in files_in_pr:
                    continue

                latest_file = LatestFile(file=file, commit=commit)
                files[file.filename] = latest_file

        return list(files.values())

    def get_all_bot_comments(self) -> List[IssueComment]:
        comments = self._github_pr.get_comments()
        result = []
        for comment in comments:
            if self.COMMENT_HEADER in comment.body:
                result.append(comment)
        return result

    def _get_files_to_comment(
        self, files: List[LatestFile], all_bot_comments: List[IssueComment]
    ) -> List[LatestFile]:
        result = []
        for file in files:
            if file.file.filename not in [
                self._get_file_name_from_comment(comment.body)
                for comment in all_bot_comments
            ]:
                result.append(file)
                print(
                    f"File {file.file.filename} is not commented, adding it to the list"
                )
            else:
                print(f"File {file.file.filename} is already commented, ignoring it")

        return result

    def _remove_deprecated_comments(
        self, files: List[LatestFile], all_bot_comments: List[IssueComment]
    ) -> List[IssueComment]:
        deprecated_comments = []
        remaining_comments = []

        for comment in all_bot_comments:
            comment_file_name = self._get_file_name_from_comment(comment.body)
            comment_file_sha = self._get_file_sha_from_comment(comment.body)

            # If it's not a comment created by the bot (doesn't contain self.COMMENT_HEADER in body), ignore it
            if self.COMMENT_HEADER not in comment.body:
                print("Comment is not created by the bot, ignoring it")
                continue

            if comment_file_name == "" or comment_file_sha == "":
                print("Could not parse comment, deleting it")
                deprecated_comments.append(comment)
                continue

            # if file is no longer in the PR, delete the comment
            if comment_file_name not in [file.file.filename for file in files]:
                print(
                    f"{comment_file_name}: File is no longer in the PR, deleting comment"
                )
                deprecated_comments.append(comment)
                continue

            # if file changed sha, delete the comment
            for file in files:
                if (
                    file.file.filename == comment_file_name
                    and file.file.sha != comment_file_sha
                ):
                    print(
                        f"{comment_file_name}: File content changed, deleting comment"
                    )
                    deprecated_comments.append(comment)
                    break

                remaining_comments.append(comment)

        for comment in deprecated_comments:
            comment.delete()

        return remaining_comments

    def _get_file_sha_from_comment(self, comment: str) -> str:
        lines = comment.splitlines()
        for line in lines:
            if self.SHA_HEADER in line:
                # Remove first and last char from sha as the format is _{sha}_
                sha = line.split(self.SHA_HEADER)[1].strip()
                sha = sha.replace(self.SHA_HEADER_ENDING, "").strip()
                return sha
            elif line.startswith("---"):
                break
        return ""

    @staticmethod
    def _get_file_name_from_comment(comment: str) -> str:
        lines = comment.splitlines()
        for line in lines:
            if line.startswith("#### File:"):
                # Remove first and last char from file name as the format is _{file_name}_
                return line.split("#### File:")[1].strip()[1:-1]
            elif line.startswith("---"):
                break
        return ""

    def _generate_comments(self, files: List[LatestFile]) -> List[str]:
        comments = []
        for file in files:
            if file.file.status == "removed":
                continue

            if self._should_file_be_ignored(file.file.filename):
                continue

            instructions_text: str = next(
                (
                    instruction.instructions
                    for instruction in self._file_instructions
                    if fnmatch.fnmatch(file.file.filename, instruction.file_match)
                ),
                "",
            )
            if instructions_text == "":
                print(f"No instructions found for file {file.file.filename}")
                continue

            instructions_text = instructions_text.replace(
                "{file_suffix}", Path(file.file.filename).suffix
            )
            instructions_text = instructions_text.replace(
                "{file_name}", file.file.filename
            )

            comment = self._generate_comment(file, instructions_text)
            if comment != "":
                comment = self._sanitize_comment(comment)
                comments.append(comment)
        return comments

    def _should_file_be_ignored(self, file_name: str) -> bool:
        if any(
            [fnmatch.fnmatch(file_name, path) for path in self._ignore_files_in_paths]
        ):
            print(f"{file_name} is under an ignored path, skipping it.")
            return True
        return False

    def _get_number_of_tokens_in_content(self, content: str) -> int:
        # 1500 words in content = 2048 tokens
        # where maximum is 4000 tokens, if content is longer than 4000 tokens, it will return -1
        number_of_tokens = int(len(content.split(" ")) / 1500 * 2048)
        if number_of_tokens > self.MAX_TOKENS:
            return -1

        # increase 10%
        number_of_tokens = int(number_of_tokens * 1.40)
        if number_of_tokens > self.MAX_TOKENS:
            return self.MAX_TOKENS
        return number_of_tokens

    @staticmethod
    def _sanitize_comment(comment: str) -> str:
        CODE_BLOCK_START = "```"
        # There is some common errors AI can make in the response, so we need to sanitize it
        comment_lines = comment.splitlines()

        # 1) In markdown, sometimes a code block section is not starting in the position 0, so we need to fix it
        for i, line in enumerate(comment_lines):
            if not line.startswith(CODE_BLOCK_START) and line.strip().startswith(
                CODE_BLOCK_START
            ):
                comment_lines[i] = line.strip()

        return "\n".join(comment_lines)
