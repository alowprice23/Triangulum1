import re

def compress(text, max_length=200):
    """
    Compress text to a maximum length while preserving key information.
    
    This implements a hierarchical compression algorithm:
    1. First removes code comments
    2. Then removes unnecessary whitespace
    3. Then shortens code examples to just function signatures
    4. Finally truncates if still too long
    
    Args:
        text: String to compress
        max_length: Target maximum length in tokens (approximately chars)
        
    Returns:
        Compressed string
    """
    # If already under length, return as-is
    if len(text) <= max_length:
        return text
    
    # Remove code blocks but keep their signatures
    def replace_code_block(match):
        code = match.group(2)
        first_line = code.strip().split("\n")[0]
        return f"```\n{first_line}\n...```"
    
    text = re.sub(r'```(?:\w+)?\n(.*?)```', replace_code_block, text, flags=re.DOTALL)
    
    if len(text) <= max_length:
        return text
    
    # Remove excessive whitespace
    text = re.sub(r'\n\s*\n', '\n', text)
    text = re.sub(r' {2,}', ' ', text)
    
    if len(text) <= max_length:
        return text
    
    # Extract key sentences: first sentence and sentences with key terms
    sentences = re.split(r'(?<=[.!?])\s+', text)
    
    key_terms = ['error', 'fail', 'exception', 'bug', 'fix', 'issue',
                'undefined', 'null', 'reference', 'type']
    
    important_sentences = [sentences[0]]  # Always keep first sentence
    
    for sentence in sentences[1:]:
        if any(term in sentence.lower() for term in key_terms):
            important_sentences.append(sentence)
    
    compressed = ' '.join(important_sentences)
    
    # Final truncation if still too long
    if len(compressed) > max_length:
        compressed = compressed[:max_length-3] + '...'
        
    return compressed
