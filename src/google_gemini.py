import fnmatch
from typing import List

import vertexai
from vertexai.generative_models import GenerativeModel, GenerationResponse
import vertexai.preview.generative_models as generative_models

from src.ai_assistent import AiAssistent, LatestFile
from src.github_pr import GithubPR


class GoogleGemini(AiAssistent):
    MAX_TOKENS = 10000

    def __init__(self, github_pr: GithubPR, ignore_files_with_content: List[str],
                    ignore_files_in_paths: List[str], google_gemini_token: str):
            super().__init__(
                github_pr=github_pr,
                ignore_files_with_content=ignore_files_with_content,
                ignore_files_in_paths=ignore_files_in_paths)
            self._google_gemini_token = google_gemini_token

    def _generate_comment(self, latest_file: LatestFile, instructions: str) -> str:
        header = f"{self.COMMENT_HEADER}\n#### File: _{{file}}_\n#### SHA: _{{sha}}_\n----\n{{response}}"
        file = latest_file.file
        print(f"Generating comment for file: {file.filename}")
        commit = latest_file.commit
        try:
            file_content = self._github_pr.get_content_for_file(file, commit)

            if self._ignore_files_with_content is not None and self._ignore_files_with_content != "" and self._ignore_files_with_content in file_content:
                print(f"{file.filename}: File content contains {self._ignore_files_with_content}, skipping it")
                return ""
        except Exception as e:
            print(f"Error while getting content for file: {e}")
            return header.format(file=file.filename, sha=file.sha,
                                 response=f"Error while getting content for file: {e}")

        if file.filename.endswith(".py"):
            system_content = 'You are a Python Enginner and you are reviewing a pull request. You reviews needs to: 1. Describe what this file does; 2. Check if the code has any problem or points for improvement, and if any, demonstrate how to improve or fix it;'
        elif file.filename.endswith(".md"):
            system_content = 'You are a Technical Writer and you are reviewing documentation. You reviews needs to: Check if the text is clear, check for typos and other problems and if you find anything give suggestions to improve it If possible add examples based on the code.'
        elif '.' in file.filename:
            file_suffix = file.filename.split(".")[-1]
            system_content = f'You are checking a file with the type {file_suffix}, based in the recommendations for this file type you need to: 1. Describe what this file does; 2. Check if there is any problems in the code and if any suggest corrections If possible add examples based on its content.'
        else:
            system_content = "1. Describe what this file does \n2. Check if this file has any problems and if any suggest corrections:"

        system_content = f'{system_content} \n If possible put your answer in markdown format.'
        tokens = self._get_number_of_tokens_in_content(file_content)
        if tokens == -1:
            print(f"File is too long to generate a comment: {file.filename}")
            return header.format(file=file.filename, sha=file.sha, response="File is too long to generate a comment.")

        try:
            generation_config = {
                "max_output_tokens": 8192,
                "temperature": 1,
                "top_p": 0.95,
            }

            safety_settings = {
                generative_models.HarmCategory.HARM_CATEGORY_HATE_SPEECH: generative_models.HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
                generative_models.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: generative_models.HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
                generative_models.HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: generative_models.HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
                generative_models.HarmCategory.HARM_CATEGORY_HARASSMENT: generative_models.HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
            }
            vertexai.init(project="freshbooks-builds", location="us-central1")
            model = GenerativeModel(
                "gemini-1.5-flash-preview-0514",
                system_instruction=[system_content]
            )
            response: GenerationResponse = model.generate_content(
                [file_content],
                generation_config=generation_config,
                safety_settings=safety_settings,
                stream=False,
            )

        except Exception as e:
            if 'maximum context length' in str(e):
                print(f"File is too long to generate a comment: {file.filename}")
                return header.format(file=file.filename, sha=file.sha,
                                     response="File is too long to generate a comment.")
            else:
                print(f"Error while generating information: {e}")
                return header.format(file=file.filename, sha=file.sha,
                                     response=f"Error while generating information: {e}")

        comment = response.text

        final_comment = header.format(file=file.filename, sha=file.sha, response=comment)
        print(f"Generated comment for file: {file.filename}")
        return final_comment
