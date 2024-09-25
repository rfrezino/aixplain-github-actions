from typing import List

import vertexai
from vertexai.generative_models import GenerativeModel, GenerationResponse
import vertexai.preview.generative_models as generative_models

from ai_assistent import AiAssistent, LatestFile
from github_pr import GithubPR


class GoogleGemini(AiAssistent):
    MAX_TOKENS = 10000

    def __init__(
        self,
        github_pr: GithubPR,
        ignore_files_with_content: List[str],
        ignore_files_in_paths: List[str],
        google_gemini_token: str,
        instructions: List[str],
    ):
        super().__init__(
            github_pr=github_pr,
            ignore_files_with_content=ignore_files_with_content,
            ignore_files_in_paths=ignore_files_in_paths,
            instructions=instructions,
        )
        self._google_gemini_token = google_gemini_token

    def _generate_comment(self, latest_file: LatestFile, instructions: str) -> str:
        header = self._get_header()
        file = latest_file.file
        print(f"Generating comment for file: {file.filename}")
        ai_input = latest_file.get_file_content(self._github_pr)

        changes = file.patch
        ai_input = f"""This is the whole file:
```
{ai_input}
```

These are the changes, based on unified diff:
```
{changes}
```
"""

        tokens = self._get_number_of_tokens_in_content(ai_input)
        if tokens == -1:
            print(f"File is too long to generate a comment: {file.filename}")
            return header.format(
                file=file.filename,
                sha=file.sha,
                response="File is too long to generate a comment.",
            )

        try:
            generation_config = {
                "max_output_tokens": 8192,
                "temperature": 1,
                "top_p": 0.95,
            }

            safety_settings = {
                generative_models.HarmCategory.HARM_CATEGORY_HATE_SPEECH: generative_models.HarmBlockThreshold.BLOCK_ONLY_HIGH,
                generative_models.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: generative_models.HarmBlockThreshold.BLOCK_ONLY_HIGH,
                generative_models.HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: generative_models.HarmBlockThreshold.BLOCK_ONLY_HIGH,
                generative_models.HarmCategory.HARM_CATEGORY_HARASSMENT: generative_models.HarmBlockThreshold.BLOCK_ONLY_HIGH,
            }
            vertexai.init(project="freshbooks-builds", location="us-central1")
            model = GenerativeModel(
                "gemini-1.5-pro-002", system_instruction=instructions
            )
            response: GenerationResponse = model.generate_content(
                contents=ai_input,
                generation_config=generation_config,
                safety_settings=safety_settings,
                stream=False,
            )

        except Exception as e:
            if "maximum context length" in str(e):
                print(f"File is too long to generate a comment: {file.filename}")
                return header.format(
                    file=file.filename,
                    sha=file.sha,
                    response="File is too long to generate a comment.",
                )
            else:
                print(f"Error while generating information: {e}")
                return header.format(
                    file=file.filename,
                    sha=file.sha,
                    response=f"Error while generating information: {e}",
                )

        comment = response.text.strip()

        final_comment = header.format(
            file=file.filename, sha=file.sha, response=comment
        )
        print(f"Generated comment for file: {file.filename}")
        return final_comment
