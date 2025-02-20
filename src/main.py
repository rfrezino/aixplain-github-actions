import argparse
import os

from execute import execute


parser = argparse.ArgumentParser()
parser.add_argument("--openai_api_key", help="Your OpenAI API Key", default="")
parser.add_argument("--github_token", help="Your Github Token", default="")
parser.add_argument("--github_pr_id", help="Your Github PR ID", default=1)
parser.add_argument(
    "--google_gemini_token", help="Your Google Gemini Token", default=""
)
parser.add_argument(
    "--ignore_files_with_content",
    help="If file has this content on its body, ignore it.",
    default="",
)
parser.add_argument(
    "--ignore_files_in_paths",
    help='List of relative paths, split by ";" Example "*/test/;*/docs/"',
    default="",
)
parser.add_argument(
    "--instructions",
    help="Instructions for the model. List of instructions separated by ';'. Example: 'python code;generate comment'",
    default="",
)
parser.add_argument("--google_ai_model", help="AI model to use", default="gemini-2.0-flash-001")
parser.add_argument("--google_project_name", help="Google Project Name", default="")

args = parser.parse_args()

execute(
    github_repository=os.getenv("GITHUB_REPOSITORY"),
    github_token=args.github_token,
    pr_number=int(args.github_pr_id),
    openai_token=args.openai_api_key,
    google_gemini_token=args.google_gemini_token,
    ignore_files_with_content=args.ignore_files_with_content,
    ignore_files_in_path=args.ignore_files_in_paths,
    instructions=args.instructions,
    google_project_name=args.google_project_name,
    google_model_name=args.google_ai_model,
)
