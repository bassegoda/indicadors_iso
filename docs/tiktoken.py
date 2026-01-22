import tiktoken

enc = tiktoken.encoding_for_model("gpt-4")
with open("llm_context.md", "r", encoding="utf-8") as f:
    text = f.read()
tokens = enc.encode(text)
print(f"Tokens: {len(tokens)}")