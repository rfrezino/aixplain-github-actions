from typing import List

from github import Github
from github.Commit import Commit
from github.File import File
from github.IssueComment import IssueComment


class GithubPR:
    _repository_name: str
    _pr_number: int
    _github_token: str
    _github: Github

    def __init__(self, repository_name: str, pr_number: int, github_token: str):
        self._repository_name = repository_name
        self._pr_number = pr_number
        self._github_token = github_token
        self._github = Github(github_token)
        self._repository = self._github.get_repo(full_name_or_id=repository_name)

    def get_comments(self) -> List[IssueComment]:
        result = []
        comments = self._repository.get_pull(self._pr_number).get_issue_comments()
        for comment in comments:
            result.append(comment)
        return result

    def remove_old_comments(self, identifier: str) -> None:
        for comment in self.get_comments():
            if identifier in comment.body:
                comment.delete()

    def get_pr_commits(self) -> List[Commit]:
        commits = self._repository.get_pull(self._pr_number).get_commits()
        result = []
        for commit in commits:
            result.append(commit)
        return result

    def get_files(self) -> List[File]:
        files = self._repository.get_pull(self._pr_number).get_files()
        result = []
        for file in files:
            result.append(file)
        return result

    def add_comments(self, comments: list):
        for comment in comments:
            self._repository.get_pull(self._pr_number).create_issue_comment(comment)

    def get_content_for_file(self, file: File, commit: Commit) -> str:
        return self._repository.get_contents(file.filename, ref=commit.sha).decoded_content.decode("utf-8")
