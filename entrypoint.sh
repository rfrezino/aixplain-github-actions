#!/bin/sh -l
python /src/main.py --openai_api_key "$1" --github_token "$2" --github_pr_id "$3" --google_gemini_token "$4" --ignore_files_with_content "$5" --ignore_files_in_paths "$6" --instructions "$7"
