import fnmatch
from dataclasses import dataclass
from typing import List

import openai
from github.Commit import Commit
from github.File import File
from github.IssueComment import IssueComment

from github_pr import GithubPR


@dataclass
class LatestFile:
    file: File
    commit: Commit


class ChatGPT:
    COMMENT_HEADER = "### AIxplain Comment"
    _ignore_files_with_content: str
    _ignore_files_in_paths: List[str]
    _github_pr: GithubPR

    def __init__(self, github_pr: GithubPR, openai_token: str, ignore_files_with_content: str,
                 ignore_files_in_paths: List[str]):
        self._ignore_files_with_content = ignore_files_with_content
        self._ignore_files_in_paths = ignore_files_in_paths
        openai.api_key = openai_token
        self._github_pr = github_pr

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
                if file.file.filename == comment_file_name and file.commit.sha != comment_file_sha:
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
            comment = self._generate_comment(file)
            if comment != "":
                comments.append(comment)
        return comments

    def _get_latest_file_version_from_commits(self) -> List[LatestFile]:
        commits = self._github_pr.get_pr_commits()
        files = {}
        for commit in commits:
            for file in commit.files:
                latest_file = LatestFile(file=file, commit=commit)
                files[file.filename] = latest_file

        return list(files.values())

    @staticmethod
    def _get_number_of_tokens_in_content(content: str) -> int:
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
        if any([fnmatch.fnmatch(latest_file.file.filename, path) for path in self._ignore_files_in_paths]):
            print(f'{latest_file.file.filename} is under an ignored path, skipping it.')
            return ""

        header = f"{self.COMMENT_HEADER}\n#### File: _{{file}}_\n#### SHA: _{{sha}}_\n----\n{{response}}"
        file = latest_file.file
        print(f"Generating comment for file: {file.filename}")
        commit = latest_file.commit
        try:
            file_content = self._github_pr.get_content_for_file(file, commit)

            if self._ignore_files_with_content in file_content:
                print(f"File {file.filename} is ignored, skipping it")
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
            content = f"1. Describe what this file does \n2. Check if this file has any problems and if any suggest corrections:"

        content = f'{content} \n If possible put your answer in markdown format.'
        tokens = self._get_number_of_tokens_in_content(file_content)
        if tokens == -1:
            print(f"File is too long to generate a comment: {file.filename}")
            return header.format(file=file.filename, sha=file.sha, response=f"File is too long to generate a comment.")

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
                                     response=f"File is too long to generate a comment.")
            else:
                print(f"Error while generating information: {e}")
                return header.format(file=file.filename, sha=file.sha,
                                     response=f"Error while generating information: {e}")

        comment = response['choices'][0]['message']['content']

        final_comment = header.format(file=file.filename, sha=file.sha, response=comment)
        print(f"Generated comment for file: {file.filename}")
        return final_comment
