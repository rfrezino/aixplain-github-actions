#!/bin/sh -l
python /src/main.py --openai_api_key "$1" --github_token "$2" --github_pr_id "$3" --ignore_files_with_content "$4" --ignore_files_in_paths "$5"