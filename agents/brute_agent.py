from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage
from typing import Optional, List, Union
from PIL import Image


class BruteAgent:
    """Agent responsible for generating brute force solutions."""

    def __init__(self, model_name: str, language: str = "python"):
        # Parse model name (format: "google:model-name")
        if ":" in model_name:
            provider, model = model_name.split(":", 1)
        else:
            model = model_name

        # Remove 'models/' prefix if present - LangChain adds it automatically
        if model.startswith("models/"):
            model = model.replace("models/", "")

        self.model = ChatGoogleGenerativeAI(model=model, temperature=0.3)
        self.language = language.lower()
        self._update_system_prompt()

    def _update_system_prompt(self):
        """Update system prompt based on language."""
        lang_info = {
            'python': {
                'name': 'Python',
                'io': 'Use open("input.txt", "r") for reading and open("output.txt", "w") for writing. Read all input at once for speed.',
                'ext': 'python'
            },
            'java': {
                'name': 'Java',
                'io': 'Use BufferedReader and FileReader for fast input, PrintWriter for fast output. Read from "input.txt" and write to "output.txt".',
                'ext': 'java',
                'note': 'IMPORTANT: The class name must match the filename (without .java extension). For example, if the file is "brute.java", the class must be named "brute".'
            },
            'cpp': {
                'name': 'C++',
                'io': 'Use ifstream for reading from "input.txt" and ofstream for writing to "output.txt". Use ios_base::sync_with_stdio(false) for speed.',
                'ext': 'cpp'
            }
        }
        
        info = lang_info.get(self.language, lang_info['python'])
        
        java_note = f"\n- {info.get('note', '')}" if self.language == 'java' and 'note' in info else ""
        
        self.system_prompt = f"""You are a brute force algorithm expert.

Your task is to generate a SIMPLE, CORRECT brute force solution in {info['name']}.

Guidelines:
- Prioritize CORRECTNESS over efficiency
- Use simple, straightforward approaches (nested loops, recursion, etc.)
- Don't worry about time/space complexity
- {info['io']}{java_note}
- Handle the exact input/output format specified
- Include proper input parsing
- Optimize file I/O for speed (read/write efficiently)
- No unnecessary comments or explanations in code
- Make sure the solution is complete and runnable
- The solution must read from "input.txt" and write to "output.txt"

Output ONLY the {info['name']} code, no markdown, no explanations.
"""

    def _load_image(self, image_path: str) -> Image.Image:
        """Load image from file path."""
        try:
            return Image.open(image_path)
        except Exception as e:
            raise ValueError(f"Could not load image {image_path}: {e}")

    def generate_solution(self, problem_statement: Union[str, List], image_paths: Optional[List[str]] = None, expected_class_name: Optional[str] = None) -> str:
        """Generate brute force solution for the given problem.
        
        Args:
            problem_statement: Problem description (text or list of content parts)
            image_paths: Optional list of image file paths to include
            expected_class_name: For Java, the expected class name (filename without extension)
        """
        # Prepare content for HumanMessage
        content_parts = []
        
        # Add text problem statement
        java_class_note = ""
        if self.language == 'java' and expected_class_name:
            java_class_note = f"\n\nCRITICAL FOR JAVA: The class must be named exactly '{expected_class_name}' (matching the filename)."
        
        if isinstance(problem_statement, str):
            content_parts.append(f"Generate a brute force {self.language} solution for this problem:{java_class_note}\n\n{problem_statement}")
        else:
            if java_class_note:
                content_parts.append(java_class_note)
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
        code = response.content.strip()

        # Remove markdown code blocks if present
        lang_ext = {'python': 'python', 'java': 'java', 'cpp': 'cpp', 'c++': 'cpp'}.get(self.language, 'python')
        if code.startswith(f"```{lang_ext}"):
            code = code.split(f"```{lang_ext}")[1].split("```")[0].strip()
        elif code.startswith("```"):
            code = code.split("```")[1].split("```")[0].strip()

        return code
