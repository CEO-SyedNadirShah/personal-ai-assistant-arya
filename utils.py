# ============================================
# arya/utils.py
# Shared LLM instances + safe retry wrapper
# ============================================

import time, os, warnings
warnings.filterwarnings("ignore")

from langchain_groq import ChatGroq
from config import LLM_MODEL_FAST, LLM_MODEL_STRONG, GROQ_API_KEY

# Ensures ChatGroq() can find the key whether it came from .env locally
# or from st.secrets on Streamlit Cloud
os.environ["GROQ_API_KEY"] = GROQ_API_KEY

llm_fast   = ChatGroq(model=LLM_MODEL_FAST, temperature=0.3)
llm_strong = ChatGroq(model=LLM_MODEL_STRONG, temperature=0.5)


def safe_invoke(llm, messages, max_retries: int = 3, wait_seconds: int = 60) -> str:
    """
    Calls llm.invoke(messages) with automatic retry on rate limits.
    Accepts either a plain string prompt or a list of message dicts.
    """
    last_error = None
    for attempt in range(1, max_retries + 1):
        try:
            return llm.invoke(messages).content
        except Exception as e:
            last_error = e
            msg = str(e).lower()
            is_rate_limit = any(kw in msg for kw in
                                 ["rate limit", "429", "quota", "too many requests"])
            wait = wait_seconds if is_rate_limit else 5
            if attempt < max_retries:
                time.sleep(wait)
                continue
            else:
                raise last_error
    raise last_error