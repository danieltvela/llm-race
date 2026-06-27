"""Prompt generation utilities for benchmark runs."""

import random
import string


SYSTEM_PROMPT = "You are a helpful assistant. Answer concisely."


def _random_word(length: int = 8) -> str:
    return "".join(random.choices(string.ascii_lowercase, k=length))


def generate_prompt(token_approx: int) -> str:
    word_count = int(token_approx * 1.3)
    words = [_random_word() for _ in range(word_count)]
    sentences: list[str] = []
    i = 0
    while i < len(words):
        sent_len = random.randint(8, 20)
        sentence = " ".join(words[i : i + sent_len])
        sentences.append(sentence.capitalize() + ".")
        i += sent_len
    return " ".join(sentences)
