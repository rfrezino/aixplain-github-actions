import fnmatch
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Tuple

from github.IssueComment import IssueComment

from github_pr import GithubPR
from github.Commit import Commit
from github.File import File


@dataclass
class LatestFile:
    file: File
    commit: Commit
    _content: Optional[str] = None

    def get_file_content(self, gr_pr: GithubPR) -> str:
        if self._content is None:
            self._content = gr_pr.get_content_for_file(self.file, self.commit)
        return self._content


@dataclass
class FileInstructions:
    file_match: str
    instructions: str


class AiAssistent(ABC):
    SUMMARY_COMMENT_HEADER = "### AIxplain Summary"
    COMMENT_HEADER = "### AIxplain Comment"
    HIDE_FILE_LINE_START = "<!--FILE:"
    HIDE_FILE_LINE_END = "-->"
    SHA_HEADER = "<!--#### SHA:"
    SHA_HEADER_ENDING = "-->"
    SKIP_COMMENT_TOKEN = "All Good Here!"
    _github_pr: GithubPR
    _ignore_files_with_content: List[str]
    _ignore_files_in_paths: List[str]
    _file_instructions: List[FileInstructions]
    _instructions: List[str]
    _deprecated_comments: List[IssueComment]
    MAX_TOKENS = 0

    def __init__(
        self,
        github_pr: GithubPR,
        ignore_files_with_content: List[str],
        ignore_files_in_paths: List[str],
        instructions: List[str],
    ) -> None:
        self._github_pr = github_pr
        self._ignore_files_with_content = ignore_files_with_content
        self._ignore_files_in_paths = ignore_files_in_paths
        self._instructions = instructions
        self._file_instructions = self._generate_file_instructions()

    def _get_header(self) -> str:
        return f"{self.COMMENT_HEADER}\n#### File: _{{file}}_\n{self.SHA_HEADER} {{sha}} {self.SHA_HEADER_ENDING}\n----\n{{response}}"

    def _generate_file_instructions(self) -> List[FileInstructions]:
        header = f"""You are a senior Python developer reviewing a pull request. Follow these guidelines:

1. Add comments for content that is unclear or problematic.
2. Be succinct and clear in your comments.
3. If you find any problem, provide a solution or suggestion.
4. When possible, add examples based on the code.
5. If you find no problems, reply with "{self.SKIP_COMMENT_TOKEN}".
6. Avoid verbosity; write only what is necessary.
7. Do not include the whole code; only the relevant parts in your comments.
8. Respond constructively.

{{specific_instructions}}

### Example of a Good Comment:

1. List the comments.
2. Explain what can be improved.
3. Show the specific part of the code that needs improvement.
4. Provide a suggestion to fix it, including an example.

### Specific Guidelines for this File Type: 
{{specifics}}

### Input Example:

```yaml
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
```

### Result Example:

1. **YAML Indentation Consistency**
   ```yaml
   - name: dev_image_tag
     type: string
   ```
   - The indentation of elements under `parameters` is inconsistent. YAML files are sensitive to indentation as it determines the structure of the data.
   - **Suggestion:** Ensure consistent indentation across all elements for clarity and to avoid parsing errors.

2. **Variable Name Readability**
   ```yaml
- name: ci_docker_compose_coverage_targ
  type: string
  default: 'coverage'
   ```
   - The variable `ci_docker_compose_coverage_targ` could be more explicit to avoid confusion.
   - **Suggestion:** Change the variable name to `ci_docker_compose_coverage_target` for better readability.

"""
        specific_instruction = ""
        if self._instructions:
            specific_instruction = "Specifics instructions for this file:\n"
            for number, instruction in enumerate(self._instructions):
                specific_instruction += f"{number + 1}. {instruction}\n"

        py_instructions = FileInstructions(
            file_match="*.py",
            instructions=header.format(
                specifics="You are reviewing a Python file.",
                specific_instructions=specific_instruction,
            ),
        )
        md_instructions = FileInstructions(
            file_match="*.md",
            instructions=header.format(
                specifics="Check if the text is clear, check for typos and other problems and if you find anything give suggestions to improve",
                specific_instructions=specific_instruction,
            ),
        )
        file_with_extension_instructions = FileInstructions(
            file_match="*.*",
            instructions=header.format(
                specifics="You are checking a file with the type {file_suffix}, you know the recommendations for this file.",
                specific_instructions=specific_instruction,
            ),
        )
        default_instructions = FileInstructions(
            file_match="*",
            instructions=header.format(
                specifics="Based on the type of this file, check it based on the best practices.",
                specific_instructions=specific_instruction,
            ),
        )

        result = [
            py_instructions,
            md_instructions,
            file_with_extension_instructions,
            default_instructions,
        ]

        appended_instructions = "\n This is the file name {file_name}. Put the response in a single file in plain Markdown Github format."
        for instruction in result:
            instruction.instructions = (
                f"{instruction.instructions} {appended_instructions}"
            )

        return result

    @abstractmethod
    def _generate_comment(self, latest_file: LatestFile, instructions: str) -> str:
        pass

    def _should_file_be_ignored_due_to_content(self, file: LatestFile) -> bool:
        if self._ignore_files_with_content:
            try:
                for ignore_content in self._ignore_files_with_content:
                    if ignore_content in file.get_file_content(self._github_pr):
                        print(
                            f"{file.file.filename}: File content contains {ignore_content}, skipping it. Filter: {self._ignore_files_with_content}"
                        )
                        return True
            except Exception as e:
                print(f"Error while getting content for file: {e}")
                return True
        return False

    def execute(self):
        print("Getting PR information")
        pr_author = self._github_pr.get_pr_author_login()
        if "dependabot" in pr_author:
            print("Dependabot PR, skipping")
            exit(0)

        print("Getting all files from PR")
        all_files = self._get_latest_file_version_from_commits()
        print("Filter files by their content")
        all_files = [
            file
            for file in all_files
            if not self._should_file_be_ignored_due_to_content(file)
        ]
        print("Filter files by their path")
        all_files = [
            file
            for file in all_files
            if not self._should_file_be_ignored_due_to_path(file.file.filename)
        ]
        print("Getting all bot comments")
        all_bot_comments = self.get_all_bot_comments()
        print("Removing deprecated comments")
        remaining_comments = self._remove_deprecated_comments(
            all_files, all_bot_comments
        )
        print("Generating new comments")
        files_to_comment = self._get_files_to_comment(all_files, remaining_comments)
        files_to_comment = self._filter_files_to_comment(
            files_to_comment, all_bot_comments
        )

        if not files_to_comment:
            print("No files to comment, exiting")
            exit(0)

        comments = self._generate_comments(files_to_comment)
        comments = self._filter_comments(comments)

        summary_comment = self._generate_summary_comment(
            all_files, comments, remaining_comments
        )
        comments.append(summary_comment)

        print("Deleting deprecated comments")
        self._delete_deprecated_comments()

        print("Adding new comments")
        self._github_pr.add_comments(comments)

    def _filter_comments(self, comments: List[str]) -> List[str]:
        # if SKIP_COMMENT_TOKEN is in the comment, remove it
        return [
            comment
            for comment in comments
            if self.SKIP_COMMENT_TOKEN.upper() not in comment.upper()
        ]

    def _generate_summary_comment(
        self,
        files_to_comment: List[LatestFile],
        comments: List[str],
        remaining_comments: List[IssueComment],
    ) -> str:
        hidden_files_section = [
            f"{self.HIDE_FILE_LINE_START}{file.file.filename}|{file.file.sha}{self.HIDE_FILE_LINE_END}\n"
            for file in files_to_comment
        ]
        summary = f"""{self.SUMMARY_COMMENT_HEADER}
  
  - {len(files_to_comment)} files were reviewed.
  - {len(comments) + len(remaining_comments)} comments were added.
  
    {"".join(hidden_files_section)}
"""
        return summary

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
            if self.COMMENT_HEADER or self.SUMMARY_COMMENT_HEADER in comment.body:
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

    def _filter_files_to_comment(
        self, files: List[LatestFile], all_bot_comments: List[IssueComment]
    ) -> List[LatestFile]:
        all_files_in_previous_run: List[Tuple[str, str]] = []
        for comment in all_bot_comments:
            if self.SUMMARY_COMMENT_HEADER not in comment.body:
                continue

            lines = comment.body.splitlines()
            for line in lines:
                if self.HIDE_FILE_LINE_START in line:
                    line = line.replace(self.HIDE_FILE_LINE_START, "").replace(
                        self.HIDE_FILE_LINE_END, ""
                    )
                    file_name, file_sha = line.split("|")
                    all_files_in_previous_run.append((file_name.strip(), file_sha))

        for file in files:
            if (file.file.filename, file.file.sha) in all_files_in_previous_run:
                print(f"File {file.file.filename} is already commented, ignoring it")
                files.remove(file)
            else:
                print(
                    f"File {file.file.filename} is not commented, adding it to the list"
                )

        return files

    def _remove_deprecated_comments(
        self, files: List[LatestFile], all_bot_comments: List[IssueComment]
    ) -> List[IssueComment]:
        deprecated_comments = []
        remaining_comments = []

        for comment in all_bot_comments:
            if self.SUMMARY_COMMENT_HEADER in comment.body:
                print("Summary comment found, ignoring it")
                deprecated_comments.append(comment)
                continue

            if self.SKIP_COMMENT_TOKEN.upper() in comment.body.upper():
                print("Comment contains SKIP_COMMENT_TOKEN, ignoring it")
                deprecated_comments.append(comment)
                continue

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
            deleted = False
            for file in files:
                if (
                    file.file.filename == comment_file_name
                    and file.file.sha != comment_file_sha
                ):
                    print(
                        f"{comment_file_name}: File content changed, deleting comment"
                    )
                    deprecated_comments.append(comment)
                    deleted = True
                    break

            if not deleted:
                remaining_comments.append(comment)

        self._deprecated_comments = deprecated_comments

        return remaining_comments

    def _delete_deprecated_comments(self):
        for comment in self._deprecated_comments:
            comment.delete()

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

    def _should_file_be_ignored_due_to_path(self, file_name: str) -> bool:
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
