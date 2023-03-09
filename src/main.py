import argparse
import os

from chatgpt import ChatGPT
from github_pr import GithubPR


def execute(github_repository: str, github_token: str, pr_number: int, openai_token: str,
            ignore_files_with_content: str, ignore_files_in_path: str):
    print(f"Github Repository: {github_repository}")
    github_pr = GithubPR(
        repository_name=github_repository,
        github_token=github_token,
        pr_number=pr_number)

    chatgpt = ChatGPT(
        github_pr=github_pr,
        openai_token=openai_token,
        ignore_files_with_content=ignore_files_with_content,
        ignore_files_in_path=ignore_files_in_path.split(';')
    )

    chatgpt.execute()


parser = argparse.ArgumentParser()
parser.add_argument('--openai_api_key', help='Your OpenAI API Key', default='')
parser.add_argument('--github_token', help='Your Github Token', default='')
parser.add_argument('--github_pr_id', help='Your Github PR ID', default=1)
parser.add_argument('--ignore_files_with_content', help='If file has this content on its body, ignore it.', default='')
parser.add_argument('--ignore_files_in_path', help='List of relative paths, split by ";" Example "*/test/;*/docs/"', default='')
args = parser.parse_args()
#
execute(github_repository=os.getenv('GITHUB_REPOSITORY'),
        github_token=args.github_token,
        pr_number=int(args.github_pr_id),
        openai_token=args.openai_api_key,
        ignore_files_with_content=args.ignore_files_with_content,
        ignore_files_in_path=args.ignore_files_in_path)
