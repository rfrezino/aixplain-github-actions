import argparse
import os

from chatgpt import ChatGPT
from github_pr import GithubPR

def execute(github_repository: str, github_token: str, pr_number: int, openai_token: str):
    github_pr = GithubPR(
        repository_name=github_repository,
        github_token=github_token,
        pr_number=pr_number)

    chatgpt = ChatGPT(
        github_pr=github_pr,
        openai_token=openai_token)

    chatgpt.execute()


parser = argparse.ArgumentParser()
parser.add_argument('--openai_api_key', help='Your OpenAI API Key', default='')
parser.add_argument('--github_token', help='Your Github Token', default='')
parser.add_argument('--github_pr_id', help='Your Github PR ID', default=1)
args = parser.parse_args()

execute(github_repository=os.getenv('GITHUB_REPOSITORY'),
        github_token=args.github_token,
        pr_number=int(args.github_pr_id),
        openai_token=args.openai_api_key)
