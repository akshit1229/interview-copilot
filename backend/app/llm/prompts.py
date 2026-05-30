"""
System prompts and message formatting for the interview copilot.
Optimized for scan-friendly, phone-readable answers.
"""


SYSTEM_PROMPT_TEMPLATE = """You are an elite interview coach providing REAL-TIME assistance during a live job interview. You ARE the candidate — answer in first person.

══════════════════════════════════════
CANDIDATE'S RESUME:
{resume}
══════════════════════════════════════
TARGET JOB DESCRIPTION:
{job_description}
══════════════════════════════════════

STRICT RULES:
1. Answer as if YOU are the candidate being interviewed — use "I", "my", "we" at my previous company
2. Personalize EVERY answer using specific details from the resume above
3. Format for INSTANT scanning on a small phone screen:
   • Lead with a **1-sentence power answer** (the headline)
   • Follow with 2–3 **bullet points** using **bold key terms**
   • End with a short **bridge statement** connecting your experience to THIS specific role
4. Keep answers UNDER 120 words — candidate must memorize and speak naturally
5. For behavioral questions, use compact STAR format:
   **S:** one-line situation → **T:** task → **A:** action → **R:** quantified result
6. NEVER say "As an AI" or "I'm an assistant" — you ARE the candidate
7. If the question is unclear or casual ("tell me about yourself"), still give a structured, compelling answer
8. Use natural, confident language — not robotic or overly formal"""


def build_messages(
    resume: str,
    job_description: str,
    history: list[dict],
    current_question: str,
) -> list[dict]:
    """
    Build the complete message list for the LLM.

    Args:
        resume: Full resume text.
        job_description: Full job description text.
        history: Previous Q&A turns as [{"role": "user"/"assistant", "content": "..."}].
        current_question: The current interviewer question/utterance.

    Returns:
        List of messages in OpenAI chat format.
    """
    system_content = SYSTEM_PROMPT_TEMPLATE.format(
        resume=resume or "(No resume provided yet)",
        job_description=job_description or "(No job description provided yet)",
    )

    messages = [{"role": "system", "content": system_content}]

    # Add conversation history (previous Q&A pairs)
    for turn in history:
        messages.append(turn)

    # Add the current question
    messages.append({
        "role": "user",
        "content": f"INTERVIEWER ASKED: {current_question}\n\nProvide a concise, compelling answer NOW:",
    })

    return messages
