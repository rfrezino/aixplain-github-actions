import argparse
import os

from chatgpt import ChatGPT
from github_pr import GithubPR

parser = argparse.ArgumentParser()
parser.add_argument('--openai_api_key', help='Your OpenAI API Key')
parser.add_argument('--github_token', help='Your Github Token')
parser.add_argument('--github_pr_id', help='Your Github PR ID')
args = parser.parse_args()

github_pr = GithubPR(
    repository_name=os.getenv('GITHUB_REPOSITORY'),
    github_token=args.github_token,
    pr_number=int(args.github_pr_id))

chatgpt = ChatGPT(
    github_pr=github_pr,
    openai_token=args.openai_api_key)

chatgpt.execute()
