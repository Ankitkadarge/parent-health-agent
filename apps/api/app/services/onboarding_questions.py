from typing import Any

from pydantic import BaseModel

YES_NO_OPTIONS = ["Yes", "No"]


class OnboardingQuestion(BaseModel):
    key: str
    target: str
    type: str
    prompt: str
    options: list[str] | None = None


# Keep the MVP onboarding deliberately short. The preferred language is already
# collected during family signup, so the WhatsApp flow only asks the parent for
# the minimum diabetes and medication information needed for later check-ins.
ONBOARDING_STEPS: list[OnboardingQuestion] = [
    OnboardingQuestion(
        key="diagnosed_with_diabetes",
        target="parent",
        type="choice",
        prompt="Have you been diagnosed with diabetes by a doctor?",
        options=YES_NO_OPTIONS,
    ),
    OnboardingQuestion(
        key="taking_medication",
        target="parent",
        type="choice",
        prompt="Are you currently taking any medication?",
        options=YES_NO_OPTIONS,
    ),
    OnboardingQuestion(
        key="medicine_time",
        target="parent",
        type="free_text",
        prompt="What time do you usually take your medicine? For example: 7 PM.",
    ),
]

FIRST_STEP = ONBOARDING_STEPS[0]

_STEP_INDEX_BY_KEY = {step.key: index for index, step in enumerate(ONBOARDING_STEPS)}


def get_question(step_key: str) -> OnboardingQuestion | None:
    return next((step for step in ONBOARDING_STEPS if step.key == step_key), None)


def get_next_question(step_key: str, answer_value: Any = None) -> OnboardingQuestion | None:
    """Return the next question, applying the small MVP branch.

    When the parent is not taking medication, asking for a medicine time would
    be confusing, so onboarding completes immediately after that answer.
    """
    if step_key == "taking_medication" and answer_value == "No":
        return None

    index = _STEP_INDEX_BY_KEY[step_key]
    next_index = index + 1
    return ONBOARDING_STEPS[next_index] if next_index < len(ONBOARDING_STEPS) else None
