from chatgpt import ChatGPT


class TestChatGPT:
    def test_get_file_sha_from_comment_when_sha_is_valid_return_sha(self):
        comment_format = f"{ChatGPT.COMMENT_HEADER}\n#### File: _{{file}}_\n#### SHA: _{{sha}}_\n----\n{{response}}"
        comment = comment_format.format(file="test.py", sha="1234567890", response="test")
        result = ChatGPT._get_file_sha_from_comment(comment)
        assert result == "1234567890"

    def test_get_file_sha_from_comment_when_no_sha_set_return_empty_string(self):
        comment_format = f"{ChatGPT.COMMENT_HEADER}\n#### File: _{{file}}_\n----\n{{response}}"
        comment = comment_format.format(file="test.py", response="test")
        result = ChatGPT._get_file_sha_from_comment(comment)
        assert result == ""

    def test_get_file_name_from_comment_when_name_is_valid_return_name(self):
        comment_format = f"{ChatGPT.COMMENT_HEADER}\n#### File: _{{file}}_\n----\n{{response}}"
        comment = comment_format.format(file="test.py", response="test")
        result = ChatGPT._get_file_name_from_comment(comment)
        assert result == "test.py"

    def test_get_file_name_from_comment_when_no_name_set_return_empty_string(self):
        comment_format = f"{ChatGPT.COMMENT_HEADER}\n#### SHA: _{{sha}}_\n----\n{{response}}"
        comment = comment_format.format(sha="1234567890", response="test")
        result = ChatGPT._get_file_name_from_comment(comment)
        assert result == ""
