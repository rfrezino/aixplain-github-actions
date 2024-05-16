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

            if self._ignore_files_with_content:
                for ignore_content in self._ignore_files_with_content:
                    if ignore_content in file_content:
                        print(f"{file.filename}: File content contains {ignore_content}, skipping it")
                        return ""
        except Exception as e:
            print(f"Error while getting content for file: {e}")
            return header.format(file=file.filename, sha=file.sha,
                                 response=f"Error while getting content for file: {e}")

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
                system_instruction=[instructions]
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

        comment = response.text.strip()

        final_comment = header.format(file=file.filename, sha=file.sha, response=comment)
        print(f"Generated comment for file: {file.filename}")
        return final_comment
