from typing import List

from github.File import File
from google import genai
from google.genai import types

from google.genai.types import GenerateContentResponse

from ai_assistent import AiAssistent, LatestFile
from github_pr import GithubPR


class GoogleGemini(AiAssistent):
    MAX_TOKENS = 10000
    _google_gemini_token: str
    _google_project_name: str
    _model_name: str
    _google_project_location: str

    def __init__(
        self,
        github_pr: GithubPR,
        ignore_files_with_content: List[str],
        ignore_files_in_paths: List[str],
        google_gemini_token: str,
        instructions: List[str],
        google_project_name="",
        model_name="gemini-2.0-flash-001",
        google_project_location="us-central1",
    ):
        super().__init__(
            github_pr=github_pr,
            ignore_files_with_content=ignore_files_with_content,
            ignore_files_in_paths=ignore_files_in_paths,
            instructions=instructions,
        )
        self._google_gemini_token = google_gemini_token
        self._google_project_name = google_project_name
        self._model_name = model_name
        self._google_project_location = google_project_location

    def get_client(self) -> genai.Client:
        return genai.Client(
            vertexai=True,
            project=self._google_project_name,
            location=self._google_project_location,
        )

    def _generate_comment(self, latest_file: LatestFile, instructions: str) -> str:
        header = self._get_header()
        file: File = latest_file.file
        print(f"Generating comment for file: {file.filename}")
        ai_input = latest_file.get_file_content(self._github_pr)

        ai_input = f"""
You are a code reviewer, and you are reviewing a PR that was published in GitHub by one of your colleagues. 

This is the modified file that you need to review:
```
{ai_input}
```

This is the patch from what changed from the git file in main:
```
{file.patch}
```

Based on this: 
{instructions}
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
            generate_content_config = types.GenerateContentConfig(
                temperature=1,
                top_p=0.95,
                max_output_tokens=8192,
                response_modalities=["TEXT"],
                safety_settings=[
                    types.SafetySetting(
                        category="HARM_CATEGORY_HATE_SPEECH", threshold="OFF"
                    ),
                    types.SafetySetting(
                        category="HARM_CATEGORY_DANGEROUS_CONTENT", threshold="OFF"
                    ),
                    types.SafetySetting(
                        category="HARM_CATEGORY_SEXUALLY_EXPLICIT", threshold="OFF"
                    ),
                    types.SafetySetting(
                        category="HARM_CATEGORY_HARASSMENT", threshold="OFF"
                    ),
                ],
            )

            response: GenerateContentResponse = (
                self.get_client().models.generate_content(
                    model=self._model_name,
                    contents=ai_input,
                    config=generate_content_config,
                )
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
