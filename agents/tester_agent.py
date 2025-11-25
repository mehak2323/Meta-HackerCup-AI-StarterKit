from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage
from typing import Optional, List, Union
from PIL import Image


class TesterAgent:
    """Agent responsible for generating small test cases from problem statement."""

    def __init__(self, model_name: str):
        # Parse model name (format: "google:model-name")
        if ":" in model_name:
            provider, model = model_name.split(":", 1)
        else:
            model = model_name

        # Remove 'models/' prefix if present - LangChain adds it automatically
        if model.startswith("models/"):
            model = model.replace("models/", "")

        self.model = ChatGoogleGenerativeAI(model=model, temperature=0.7)
        self.system_prompt = """You are a test case generation expert for programming problems.

Your task is to generate SMALL, simple test cases that adhere to the input format specified in the problem statement.

Guidelines:
- Generate 3-5 small test cases
- Follow the exact input format specified
- Use small values (arrays of size 2-5, numbers < 100, etc.)
- Cover edge cases (empty, single element, boundary values)
- Output ONLY the test input, nothing else - NO markdown, NO code blocks, NO explanations
- Each test case should be separated by a blank line if multiple cases
- DO NOT wrap output in ``` markers or any other formatting

Example format for multiple test cases:
3
1 2 3

2
5 10

1
42

CRITICAL: Output ONLY the raw test input data above, nothing else!
"""

    def _load_image(self, image_path: str) -> Image.Image:
        """Load image from file path."""
        try:
            return Image.open(image_path)
        except Exception as e:
            raise ValueError(f"Could not load image {image_path}: {e}")

    def generate_test_cases(self, problem_statement: Union[str, List], image_paths: Optional[List[str]] = None) -> str:
        """Generate test cases for the given problem statement.
        
        Args:
            problem_statement: Problem description (text or list of content parts)
            image_paths: Optional list of image file paths to include
        """
        # Prepare content for HumanMessage
        content_parts = []
        
        # Add text problem statement
        if isinstance(problem_statement, str):
            content_parts.append(f"Generate small test cases for this problem:\n\n{problem_statement}")
        else:
            content_parts.extend(problem_statement)
        
        # Add images if provided
        if image_paths:
            for img_path in image_paths:
                try:
                    img = self._load_image(img_path)
                    content_parts.append(img)
                except Exception as e:
                    print(f"Warning: Could not load image {img_path}: {e}")
        
        # Use HumanMessage for multimodal content
        messages = [
            {"role": "system", "content": self.system_prompt},
            HumanMessage(content=content_parts)
        ]

        response = self.model.invoke(messages)
        content = response.content.strip()

        # Remove markdown code blocks if present
        if content.startswith("```"):
            lines = content.split("\n")
            # Remove first and last lines if they are markdown markers
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].startswith("```"):
                lines = lines[:-1]
            content = "\n".join(lines).strip()

        return content
