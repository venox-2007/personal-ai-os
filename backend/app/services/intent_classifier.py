import re

def is_conversational_request(text: str) -> bool:
    """
    Safely identifies if a request is purely conversational (e.g. general knowledge).
    If there is any ambiguity or any tool keyword is present, returns False.
    """
    text_lower = text.strip().lower()
    
    # 1. Reject if it contains ANY keyword related to our agents/tools
    # Calendar, Files, Coding, Research, Study/RAG, Workflows, Memory
    unsafe_keywords = [
        # Files / Documents
        "file", "document", "folder", "directory", "pdf", "txt", "read", "write", "edit", "delete", "create", "rename", "move", "copy",
        # Calendar
        "calendar", "schedule", "meeting", "event", "appointment", "book", "tomorrow at", "next week",
        # Coding
        "code", "script", "python", "bug", "error", "refactor", "debug", "compile", "run", "git", "repository",
        # Research
        "search", "web", "lookup", "look up", "find", "research", "browser", "url", "link",
        # Study/RAG
        "my notes", "summarize file", "study", "flashcards", "learn",
        # Workflows / Memory
        "workflow", "step", "memory", "remember", "forget", "recall", "automation", "task"
    ]
    
    for kw in unsafe_keywords:
        # Match as whole words/phrases where possible, or just substring for safety
        if re.search(r'\b' + re.escape(kw) + r'\b', text_lower):
            return False
            
    # 2. Accept if it explicitly starts with a conversational general-knowledge prefix
    safe_prefixes = [
        "what is", "who is", "explain", "how does", "tell me about", 
        "why is", "what are", "define", "give me a summary of", "can you explain"
    ]
    
    if any(text_lower.startswith(p) for p in safe_prefixes):
        # Additional safety check: If it's too long, it might be a complex prompt with hidden intents
        if len(text_lower.split()) <= 15:
            return True
            
    return False
