import argparse
import os

from src.chatgpt import ChatGPT
from src.github import Github

parser = argparse.ArgumentParser()
parser.add_argument('--openai_api_key', help='Your OpenAI API Key')
parser.add_argument('--github_token', help='Your Github Token')
parser.add_argument('--github_pr_id', help='Your Github PR ID')
args = parser.parse_args()

github_pr = Github(
    repository_name=os.getenv('GITHUB_REPOSITORY'),
    github_token=args.github_token,
    pr_number=args.github_pr_id)

chatgpt = ChatGPT(
    github_pr=github_pr,
    openai_token=args.openai_api_key)

chatgpt.execute()
