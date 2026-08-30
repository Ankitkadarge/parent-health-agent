from pydantic import BaseModel

LANGUAGE_OPTIONS = [
    "English",
    "Hindi",
    "Marathi",
    "Gujarati",
    "Tamil",
    "Telugu",
    "Kannada",
    "Bengali",
    "Punjabi",
    "Other",
]

CONDITION_OPTIONS = [
    "Diabetes",
    "High blood pressure",
    "High cholesterol",
    "Heart condition",
    "Thyroid",
    "Other",
    "None",
]

ACTIVITY_LEVEL_OPTIONS = [
    "Mostly sedentary",
    "Light activity",
    "Moderate activity",
    "Very active",
]

REMINDER_PREFERENCE_OPTIONS = [
    "Medication reminders",
    "Meal check-ins",
    "Exercise reminders",
    "Daily summary",
    "Weekly summary",
]


class OnboardingQuestion(BaseModel):
    key: str
    target: str
    type: str
    prompt: str
    options: list[str] | None = None


ONBOARDING_STEPS: list[OnboardingQuestion] = [
    OnboardingQuestion(
        key="preferred_language",
        target="parent",
        type="choice",
        prompt="Which language does the parent prefer?",
        options=LANGUAGE_OPTIONS,
    ),
    OnboardingQuestion(
        key="conditions",
        target="child",
        type="multi_choice",
        prompt="Which conditions are we helping your parent manage?",
        options=CONDITION_OPTIONS,
    ),
    OnboardingQuestion(
        key="medications",
        target="child",
        type="free_text",
        prompt=(
            "Please tell me the medicines your parent takes and when they take them. "
            "You can also say we'll add them later."
        ),
    ),
    OnboardingQuestion(
        key="dietary_preferences",
        target="child",
        type="free_text",
        prompt=(
            "Are there any dietary restrictions, food preferences, allergies, or foods "
            "the doctor has asked them to avoid?"
        ),
    ),
    OnboardingQuestion(
        key="activity_level",
        target="parent",
        type="choice",
        prompt="How active is your parent on a typical day?",
        options=ACTIVITY_LEVEL_OPTIONS,
    ),
    OnboardingQuestion(
        key="reminder_preferences",
        target="child",
        type="multi_choice",
        prompt="Which reminders would be helpful for your family?",
        options=REMINDER_PREFERENCE_OPTIONS,
    ),
]

FIRST_STEP = ONBOARDING_STEPS[0]

_STEP_INDEX_BY_KEY = {step.key: index for index, step in enumerate(ONBOARDING_STEPS)}


def get_question(step_key: str) -> OnboardingQuestion | None:
    return next((step for step in ONBOARDING_STEPS if step.key == step_key), None)


def get_next_question(step_key: str) -> OnboardingQuestion | None:
    """Return the question after step_key, or None if step_key was the last one."""
    index = _STEP_INDEX_BY_KEY[step_key]
    next_index = index + 1
    return ONBOARDING_STEPS[next_index] if next_index < len(ONBOARDING_STEPS) else None
