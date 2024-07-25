"""Provide a substitute for DeepL so that we can stub DeepL out in testing
and therefore not require an API key"""



class ReverseTextTranslator:
    """A trivial 'translator' for use in testing, that just reverses the text in each string"""

    def translate_text(self, text, target_lang):
        """Match the interface of the DeepL translator, 
            which can handle individual strings or lists of strings
            and takes a target language, which we ignore here"""
        if isinstance(text, str):
            return text[::-1]  # just reverse the text, easy to verify in tests
        else:  # it's a list of strings
            return [s[::-1] for s in text]
