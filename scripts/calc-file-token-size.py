#!/usr/bin/env python3
import argparse
import sys
import os

try:
    import tiktoken
except ImportError:
    print("Error: The 'tiktoken' library is required.")
    print("Please install it using: pip install tiktoken")
    sys.exit(1)


def count_tokens_in_file(file_path: str, encoding_name: str = "cl100k_base") -> int:
    """
    Reads a file and returns the token count based on the specified encoding.
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")

    # Initialize the tokenizer
    try:
        tokenizer = tiktoken.get_encoding(encoding_name)
    except ValueError:
        print(
            f"Warning: Encoding '{encoding_name}' not found. Falling back to 'cl100k_base'."
        )
        tokenizer = tiktoken.get_encoding("cl100k_base")

    # Read the file contents securely
    try:
        # Standard UTF-8 reading
        with open(file_path, "r", encoding="utf-8") as file:
            text = file.read()
    except UnicodeDecodeError:
        # Fallback for files that might have mixed encodings (e.g., legacy code files)
        print(
            "Warning: Non-UTF-8 characters detected. Reading with error replacement..."
        )
        with open(file_path, "r", encoding="utf-8", errors="replace") as file:
            text = file.read()

    # Encode the text into tokens
    # disallowed_special=() allows it to parse special tokens without throwing errors
    tokens = tokenizer.encode(text, disallowed_special=())

    return len(tokens)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Calculate the token count of a text file.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    parser.add_argument(
        "file_path", type=str, help="Path to the file you want to analyze."
    )

    parser.add_argument(
        "--encoding",
        type=str,
        default="cl100k_base",
        help="The tokenizer encoding to use (e.g., cl100k_base, o200k_base, p50k_base).",
    )

    args = parser.parse_args()

    try:
        token_count = count_tokens_in_file(args.file_path, args.encoding)
        file_size_kb = os.path.getsize(args.file_path) / 1024

        print("\n--- Token Count Results ---")
        print(f"File:      {os.path.basename(args.file_path)}")
        print(f"Size:      {file_size_kb:.2f} KB")
        print(f"Encoding:  {args.encoding}")
        print("-" * 27)
        print(f"TOKENS:    {token_count:,}\n")

    except Exception as e:
        print(f"\nError processing file: {e}")
        sys.exit(1)
