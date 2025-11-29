import subprocess
import os
import time
from typing import Tuple, Optional


class CodeExecutor:
    """Utility to execute code in multiple languages with given input."""

    def __init__(self, timeout: int = 30, language: str = "python"):
        self.timeout = timeout
        self.language = language.lower()

    def _get_file_extensions(self) -> dict:
        """Get file extensions for different languages."""
        return {
            'python': '.py',
            'java': '.java',
            'cpp': '.cpp',
            'c++': '.cpp'
        }

    def _get_compile_command(self, code_file: str) -> Optional[list]:
        """Get compilation command for the language."""
        if self.language == 'java':
            # Extract class name from file (assuming filename matches class name)
            class_name = os.path.splitext(os.path.basename(code_file))[0]
            return ['javac', code_file]
        elif self.language in ['cpp', 'c++']:
            output_file = os.path.splitext(code_file)[0]
            return ['g++', '-o', output_file, code_file, '-std=c++17']
        return None

    def _get_run_command(self, code_file: str) -> list:
        """Get execution command for the language."""
        if self.language == 'python':
            return ['python3', code_file]
        elif self.language == 'java':
            # Extract class name from file
            class_name = os.path.splitext(os.path.basename(code_file))[0]
            dir_path = os.path.dirname(code_file) or '.'
            return ['java', '-cp', dir_path, class_name]
        elif self.language in ['cpp', 'c++']:
            executable = os.path.splitext(code_file)[0]
            return [executable]
        else:
            raise ValueError(f"Unsupported language: {self.language}")

    def execute(self, code_file: str, input_file: str, output_file: str) -> Tuple[bool, str, float]:
        """
        Execute code with input from file and save output to file.

        Args:
            code_file: Path to code file to execute
            input_file: Path to input file
            output_file: Path to save output

        Returns:
            Tuple of (success: bool, error_message: str, execution_time: float in seconds)
        """
        if not os.path.exists(code_file):
            return False, f"Code file not found: {code_file}"

        if not os.path.exists(input_file):
            return False, f"Input file not found: {input_file}", 0.0

        try:
            # Compile if needed
            compile_cmd = self._get_compile_command(code_file)
            if compile_cmd:
                compile_result = subprocess.run(
                    compile_cmd,
                    capture_output=True,
                    text=True,
                    timeout=self.timeout
                )
                if compile_result.returncode != 0:
                    error_msg = f"Compilation failed:\n"
                    error_msg += f"STDERR: {compile_result.stderr}\n"
                    error_msg += f"STDOUT: {compile_result.stdout}"
                    return False, error_msg, 0.0

            # Read input from file
            with open(input_file, 'r') as f_in:
                input_data = f_in.read()

            # Execute and measure time
            run_cmd = self._get_run_command(code_file)
            start_time = time.time()
            result = subprocess.run(
                run_cmd,
                input=input_data,
                capture_output=True,
                text=True,
                timeout=self.timeout
            )
            execution_time = time.time() - start_time

            if result.returncode != 0:
                error_msg = f"Execution failed with return code {result.returncode}\n"
                error_msg += f"STDERR: {result.stderr}\n"
                error_msg += f"STDOUT: {result.stdout}"
                return False, error_msg, execution_time

            # Save output
            with open(output_file, 'w') as f_out:
                f_out.write(result.stdout)

            return True, "", execution_time

        except subprocess.TimeoutExpired:
            return False, f"Execution timed out after {self.timeout} seconds", self.timeout
        except Exception as e:
            return False, f"Execution error: {str(e)}", 0.0
