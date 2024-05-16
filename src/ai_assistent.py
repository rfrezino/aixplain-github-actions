import fnmatch
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import List

from github.IssueComment import IssueComment

from src.github_pr import GithubPR
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
    _github_pr: GithubPR
    _ignore_files_with_content: List[str]
    _ignore_files_in_paths: List[str]
    _file_instructions: List[FileInstructions]
    MAX_TOKENS = 0

    def __init__(self, github_pr: GithubPR, ignore_files_with_content: List[str],
                 ignore_files_in_paths: List[str]) -> None:
        self._github_pr = github_pr
        self._ignore_files_with_content = ignore_files_with_content
        self._ignore_files_in_paths = ignore_files_in_paths
        self._file_instructions = self._generate_file_instructions()

    @staticmethod
    def _generate_file_instructions() -> List[FileInstructions]:
        py_instructions = FileInstructions(file_match="*.py", instructions="You are a Python Enginner and you are reviewing a pull request. You reviews needs to: 1. Describe what this file does; 2. Check if the code has any problem or points for improvement, and if any, demonstrate how to improve or fix it;")
        md_instructions = FileInstructions(file_match="*.md", instructions="You are a Technical Writer and you are reviewing documentation. You reviews needs to: Check if the text is clear, check for typos and other problems and if you find anything give suggestions to improve it If possible add examples based on the code.")
        file_with_extension_instructions = FileInstructions(file_match="*.*", instructions="You are checking a file with the type {file_suffix}, based in the recommendations for this file type you need to: 1. Describe what this file does; 2. Check if there is any problems in the code and if any suggest corrections If possible add examples based on its content.")
        default_instructions = FileInstructions(file_match="*", instructions="1. Describe what this file does \n2. Check if this file has any problems and if any suggest corrections.")

        result = [py_instructions, md_instructions, file_with_extension_instructions, default_instructions]

        appended_instructions = '\n If possible put your answer in markdown format.'
        for instruction in result:
            instruction.instructions = f'{instruction.instructions} {appended_instructions}'

        return result

    @abstractmethod
    def _generate_comment(self, latest_file: LatestFile, instructions: str) -> str:
        pass

    def execute(self):
        print("Getting all files from PR")
        all_files = self._get_latest_file_version_from_commits()
        print("Getting all bot comments")
        all_bot_comments = self.get_all_bot_comments()
        print("Removing deprecated comments")
        remaining_comments = self._remove_deprecated_comments(all_files, all_bot_comments)
        print("Generating new comments")
        files_to_comment = self._get_files_to_comment(all_files, remaining_comments)
        comments = self._generate_comments(files_to_comment)
        print("Adding new comments")
        self._github_pr.add_comments(comments)

    def _get_latest_file_version_from_commits(self) -> List[LatestFile]:
        files_in_pr = self._github_pr.get_files()
        latest_files = {}
        for file in files_in_pr:
            file.sha
            if file.filename not in latest_files:
                latest_files[file.filename] = LatestFile(file=file, commit=file)
            elif file.commit.commit.author.date > latest_files[file.filename].commit.commit.author.date:
                latest_files[file.filename] = LatestFile(file=file, commit=file.commit)



        # commits = self._github_pr.get_pr_commits()
        # files = {}
        # for commit in commits:
        #     for file in commit.files:
        #         latest_file = LatestFile(file=file, commit=commit)
        #         files[file.filename] = latest_file

        return list(files.values())

    def get_all_bot_comments(self) -> List[IssueComment]:
        comments = self._github_pr.get_comments()
        result = []
        for comment in comments:
            if self.COMMENT_HEADER in comment.body:
                result.append(comment)
        return result

    def _get_files_to_comment(self, files: List[LatestFile], all_bot_comments: List[IssueComment]) -> List[LatestFile]:
        result = []
        for file in files:
            if file.file.filename not in [self._get_file_name_from_comment(comment.body) for comment in
                                          all_bot_comments]:
                result.append(file)
                print(f"File {file.file.filename} is not commented, adding it to the list")
            else:
                print(f"File {file.file.filename} is already commented, ignoring it")

        return result

    def _remove_deprecated_comments(self, files: List[LatestFile], all_bot_comments: List[IssueComment]) -> List[
        IssueComment]:
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
                print(f"{comment_file_name}: File is no longer in the PR, deleting comment")
                deprecated_comments.append(comment)
                continue

            # if file changed sha, delete the comment
            for file in files:
                if file.file.filename == comment_file_name and file.file.sha != comment_file_sha:
                    print(f"{comment_file_name}: File content changed, deleting comment")
                    deprecated_comments.append(comment)
                    break

            remaining_comments.append(comment)

        for comment in deprecated_comments:
            comment.delete()

        return remaining_comments

    @staticmethod
    def _get_file_sha_from_comment(comment: str) -> str:
        lines = comment.splitlines()
        for line in lines:
            if line.startswith("#### SHA:"):
                # Remove first and last char from sha as the format is _{sha}_
                return line.split("#### SHA:")[1].strip()[1:-1]
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

            instructions = next((instruction.instructions for instruction in self._file_instructions if
                                 fnmatch.fnmatch(file.file.filename, instruction.file_match)), None)
            if instructions is None:
                print(f"No instructions found for file {file.file.filename}")
                continue

            instructions.replace("{file_suffix}", Path(file.file.filename).suffix)

            comment = self._generate_comment(file, instructions)
            if comment != "":
                comments.append(comment)
        return comments

    def _should_file_be_ignored(self, file_name: str) -> bool:
        if any([fnmatch.fnmatch(file_name, path) for path in self._ignore_files_in_paths]):
            print(f'{file_name} is under an ignored path, skipping it.')
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
