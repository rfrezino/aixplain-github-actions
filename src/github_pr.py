from github import Github
from github.Commit import Commit
from github.IssueComment import IssueComment
from github.PaginatedList import PaginatedList


class GithubPR:
    _repository_name: str
    _pr_number: int
    _github_token: str

    def __init__(self, repository_name: str, pr_number: int, github_token: str):
        self._repository_name = repository_name
        self._pr_number = pr_number
        self._github_token = github_token
        self._repository = Github(github_token).get_repo(repository_name)

    def get_comments(self) -> PaginatedList[IssueComment]:
        return self._repository.get_pull(self._pr_number).get_issue_comments()

    def remove_old_comments(self):
        for comment in self.get_comments():
            if "[AIxplain Comment]" in comment.body:
                comment.delete()

    def get_pr_commits(self) -> PaginatedList[Commit]:
        return self._repository.get_pull(self._pr_number).get_commits()

    def add_comments(self, comments: list):
        for comment in comments:
            self._repository.get_pull(self._pr_number).create_issue_comment(comment)
