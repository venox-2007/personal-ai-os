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

def get_readonly_fast_path(text: str) -> str | None:
    """
    Identifies unambiguous, read-only requests that can be fulfilled immediately 
    by specific services without full agent routing.
    Never matches mutations (create, update, delete, schedule).
    """
    text_lower = text.strip().lower()
    
    # Must NOT contain mutation keywords
    mutation_keywords = ["create", "add", "make", "schedule", "book", "update", "change", "edit", "move", "delete", "remove", "cancel", "invite"]
    for kw in mutation_keywords:
        if re.search(r'\b' + re.escape(kw) + r'\b', text_lower):
            return None
            
    # Unambiguous read-only calendar phrases
    calendar_read_phrases = [
        "what is in my calendar",
        "whats in my calendar",
        "what's in my calendar",
        "what is on my calendar",
        "whats on my calendar",
        "what's on my calendar",
        "what is on my schedule",
        "whats on my schedule",
        "what's on my schedule",
        "list my upcoming events",
        "show my upcoming events",
        "do i have any meetings today",
        "do i have any events today",
        "show me my calendar",
        "show my schedule",
        "any meetings today",
        "any events today",
        "what is my next event",
        "what's my next event",
        "what is my next meeting",
        "what's my next meeting"
    ]
    
    # Check exact match or very close match (stripping punctuation)
    clean_text = re.sub(r'[^\w\s]', '', text_lower).strip()
    
    for phrase in calendar_read_phrases:
        clean_phrase = re.sub(r'[^\w\s]', '', phrase).strip()
        if clean_text == clean_phrase:
            return "calendar_upcoming"
            
    return None
