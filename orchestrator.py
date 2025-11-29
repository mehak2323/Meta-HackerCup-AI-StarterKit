import os
import yaml
import json
import time
from typing import Dict, Optional, Tuple, List
from agents import TesterAgent, BruteAgent, OptimalAgent, ComprehensiveTestAgent
from utils import CodeExecutor, OutputComparator, ProgressIndicator


class ProblemSolverOrchestrator:
    """Main orchestrator for the multi-agent problem solving system."""

    def __init__(self, config_path: str = "config.yaml"):
        """Initialize orchestrator with configuration."""
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)

        # Set up API key
        api_keys = self.config.get('api_keys', {})

        # Google API key for Gemini
        google_key = api_keys.get('google')
        if google_key and google_key != "your-google-api-key-here":
            os.environ['GOOGLE_API_KEY'] = google_key

        # Get language configuration
        self.language = self.config.get('language', 'python').lower()
        
        # Initialize agents with language
        self.tester_agent = TesterAgent(self.config['models']['tester_agent'])
        self.brute_agent = BruteAgent(self.config['models']['brute_agent'], language=self.language)
        self.optimal_agent = OptimalAgent(self.config['models']['optimal_agent'], language=self.language)
        # Use same model as tester for comprehensive tests, or allow config
        comprehensive_model = self.config['models'].get('comprehensive_test_agent', self.config['models']['tester_agent'])
        self.comprehensive_test_agent = ComprehensiveTestAgent(comprehensive_model)

        # Initialize utilities
        timeout = self.config['execution']['timeout_seconds']
        self.executor = CodeExecutor(timeout=timeout, language=self.language)
        self.comparator = OutputComparator()

        # Set up workspace
        self.workspace = self.config['output']['workspace_dir']
        os.makedirs(self.workspace, exist_ok=True)

        # Get file extensions based on language
        lang_extensions = {
            'python': '.py',
            'java': '.java',
            'cpp': '.cpp',
            'c++': '.cpp'
        }
        ext = lang_extensions.get(self.language, '.py')
        
        # File paths with proper extensions
        brute_sol_base = self.config['files']['brute_solution']
        optimal_sol_base = self.config['files']['optimal_solution']
        
        self.files = {
            'test_inputs': os.path.join(self.workspace, self.config['files']['test_inputs']),
            'brute_solution': os.path.join(self.workspace, brute_sol_base + ext),
            'brute_outputs': os.path.join(self.workspace, self.config['files']['brute_outputs']),
            'optimal_solution': os.path.join(self.workspace, optimal_sol_base + ext),
            'optimal_outputs': os.path.join(self.workspace, self.config['files']['optimal_outputs']),
            'input_file': os.path.join(self.workspace, 'input.txt'),
            'output_file': os.path.join(self.workspace, 'output.txt')
        }

        self.max_attempts = self.config['execution']['max_optimal_attempts']

    def solve(self, problem_statement: str, image_paths: Optional[List[str]] = None, sample_input: Optional[str] = None, sample_output: Optional[str] = None) -> Tuple[bool, Optional[str], Dict]:
        """
        Solve the given problem using multi-agent approach.

        Args:
            problem_statement: The problem description
            image_paths: Optional list of image file paths from problem statement
            sample_input: Optional sample input from problem folder
            sample_output: Optional sample output from problem folder

        Returns:
            Tuple of (success, optimal_code, metadata)
        """
        metadata = {
            'attempts': 0,
            'test_cases_generated': False,
            'brute_force_generated': False,
            'brute_force_executed': False,
            'optimal_solution_found': False,
            'errors': [],
            'optimal_attempts': []  # Store all attempts with details
        }

        print("=" * 80)
        print("STEP 1: Generating test cases...")
        print("=" * 80)

        try:
            with ProgressIndicator("Generating test cases with TesterAgent"):
                test_cases = self.tester_agent.generate_test_cases(
                    problem_statement, 
                    image_paths=image_paths,
                    sample_input=sample_input,
                    sample_output=sample_output
                )
            with open(self.files['test_inputs'], 'w') as f:
                f.write(test_cases)
            metadata['test_cases_generated'] = True
            print(f"✓ Test cases saved to: {self.files['test_inputs']}\n")
        except Exception as e:
            error = f"Failed to generate test cases: {str(e)}"
            metadata['errors'].append(error)
            print(f"✗ {error}\n")
            return False, None, metadata

        print("=" * 80)
        print("STEP 2: Generating brute force solution...")
        print("=" * 80)

        try:
            # Get expected class name for Java
            expected_class_name = None
            if self.language == 'java':
                expected_class_name = os.path.splitext(os.path.basename(self.files['brute_solution']))[0]
            
            # Determine sample input file path if available
            sample_input_file = None
            if sample_input:
                # Use the sample input file from problem folder
                problem_config = self.config.get('problem', {})
                problem_folder = problem_config.get('folder', './problem')
                sample_input_filename = problem_config.get('sample_input', 'sample_in.txt')
                sample_input_file = os.path.join(problem_folder, sample_input_filename)
                # Use absolute path
                if not os.path.isabs(sample_input_file):
                    sample_input_file = os.path.abspath(sample_input_file)
            
            with ProgressIndicator("Generating brute force solution with BruteAgent"):
                brute_code = self.brute_agent.generate_solution(
                    problem_statement, 
                    image_paths=image_paths, 
                    expected_class_name=expected_class_name,
                    sample_input=sample_input,
                    sample_output=sample_output,
                    sample_input_file=sample_input_file
                )
            with open(self.files['brute_solution'], 'w') as f:
                f.write(brute_code)
            metadata['brute_force_generated'] = True
            print(f"✓ Brute force solution saved to: {self.files['brute_solution']}\n")
        except Exception as e:
            error = f"Failed to generate brute force solution: {str(e)}"
            metadata['errors'].append(error)
            print(f"✗ {error}\n")
            return False, None, metadata

        print("=" * 80)
        print("STEP 3: Executing brute force solution...")
        print("=" * 80)

        # Use sample input file if available, otherwise use test inputs
        brute_input_file = self.files['input_file']
        if sample_input:
            # Use the sample input file from problem folder
            problem_config = self.config.get('problem', {})
            problem_folder = problem_config.get('folder', './problem')
            sample_input_filename = problem_config.get('sample_input', 'sample_in.txt')
            sample_input_file = os.path.join(problem_folder, sample_input_filename)
            # Use absolute path
            if not os.path.isabs(sample_input_file):
                sample_input_file = os.path.abspath(sample_input_file)
            if os.path.exists(sample_input_file):
                brute_input_file = sample_input_file
                print(f"Using sample input file: {brute_input_file}")
            else:
                # Fallback to test inputs if sample input file doesn't exist
                print(f"Warning: Sample input file not found at {sample_input_file}, using test inputs instead")
                with open(self.files['test_inputs'], 'r') as f_in:
                    with open(self.files['input_file'], 'w') as f_out:
                        f_out.write(f_in.read())
        else:
            # Copy test inputs to input.txt for execution
            with open(self.files['test_inputs'], 'r') as f_in:
                with open(self.files['input_file'], 'w') as f_out:
                    f_out.write(f_in.read())
        
        success, error, exec_time = self.executor.execute(
            self.files['brute_solution'],
            brute_input_file,
            self.files['output_file']
        )
        
        # Copy output to brute_outputs
        if success:
            with open(self.files['output_file'], 'r') as f_in:
                with open(self.files['brute_outputs'], 'w') as f_out:
                    f_out.write(f_in.read())

        if not success:
            error_msg = f"Brute force execution failed: {error}"
            metadata['errors'].append(error_msg)
            print(f"✗ {error_msg}\n")
            return False, None, metadata

        metadata['brute_force_executed'] = True
        print(f"✓ Brute force outputs saved to: {self.files['brute_outputs']}\n")

        print("=" * 80)
        print("STEP 4: Generating and testing optimal solution...")
        print("=" * 80)

        feedback = None
        optimal_code = None

        for attempt in range(1, self.max_attempts + 1):
            metadata['attempts'] = attempt
            print(f"\n--- Attempt {attempt}/{self.max_attempts} ---")

            attempt_data = {
                'attempt_number': attempt,
                'timestamp': time.time(),
                'code': None,
                'verdict': None,
                'error_message': None,
                'execution_success': False,
                'output_match': False,
                'output_diff': None
            }

            try:
                # Get expected class name for Java
                expected_class_name = None
                if self.language == 'java':
                    expected_class_name = os.path.splitext(os.path.basename(self.files['optimal_solution']))[0]
                
                with ProgressIndicator(f"Generating optimal solution (attempt {attempt}/{self.max_attempts})"):
                    optimal_code = self.optimal_agent.generate_solution(
                        problem_statement,
                        feedback=feedback,
                        attempt=attempt,
                        image_paths=image_paths,
                        expected_class_name=expected_class_name,
                        sample_input=sample_input,
                        sample_output=sample_output
                    )

                attempt_data['code'] = optimal_code

                # Save this attempt separately
                lang_ext = { 'python': '.py', 'java': '.java', 'cpp': '.cpp', 'c++': '.cpp' }.get(self.language, '.py')
                attempt_file = os.path.join(self.workspace, f'optimal_attempt_{attempt}{lang_ext}')
                with open(attempt_file, 'w') as f:
                    f.write(optimal_code)

                # Also update the main optimal solution file
                with open(self.files['optimal_solution'], 'w') as f:
                    f.write(optimal_code)

                print(f"✓ Generated optimal solution")

            except Exception as e:
                error = f"Failed to generate optimal solution: {str(e)}"
                attempt_data['verdict'] = 'Generation Failed'
                attempt_data['error_message'] = str(e)
                metadata['errors'].append(error)
                metadata['optimal_attempts'].append(attempt_data)
                print(f"✗ {error}")
                continue

            # Copy test inputs to input.txt for execution
            with open(self.files['test_inputs'], 'r') as f_in:
                with open(self.files['input_file'], 'w') as f_out:
                    f_out.write(f_in.read())
            
            # Execute optimal solution
            attempt_output_file = os.path.join(self.workspace, f'optimal_attempt_{attempt}_output.txt')
            success, error, exec_time = self.executor.execute(
                self.files['optimal_solution'],
                self.files['input_file'],
                self.files['output_file']
            )

            # Copy output to attempt file and main output file
            if success:
                with open(self.files['output_file'], 'r') as f_in:
                    output_content = f_in.read()
                    with open(attempt_output_file, 'w') as f_out:
                        f_out.write(output_content)
                    with open(self.files['optimal_outputs'], 'w') as f_out:
                        f_out.write(output_content)

            if not success:
                print(f"✗ Execution failed: {error}")
                attempt_data['verdict'] = 'Runtime Error'
                attempt_data['error_message'] = error
                attempt_data['execution_success'] = False
                attempt_data['execution_time'] = exec_time
                metadata['optimal_attempts'].append(attempt_data)
                feedback = f"Your solution failed to execute:\n{error}\n\nPlease fix the errors."
                metadata['errors'].append(f"Attempt {attempt}: Execution failed - {error}")
                continue

            attempt_data['execution_success'] = True
            attempt_data['execution_time'] = exec_time
            print(f"✓ Execution successful (Time: {exec_time:.3f}s)")

            # Compare outputs
            if self.comparator.compare(self.files['brute_outputs'], attempt_output_file):
                print(f"✓ Outputs match! Solution found in {attempt} attempt(s)")
                attempt_data['verdict'] = 'Accepted'
                attempt_data['output_match'] = True
                metadata['optimal_attempts'].append(attempt_data)
                metadata['optimal_solution_found'] = True
                metadata['optimal_execution_time'] = exec_time  # Store execution time for optimal solution
                print("\n" + "=" * 80)
                print("SUCCESS: Optimal solution found!")
                print("=" * 80)

                # Generate results JSON for viewer
                self._generate_results_json(problem_statement, metadata)

                return True, optimal_code, metadata
            else:
                diff = self.comparator.get_diff_summary(
                    self.files['brute_outputs'],
                    attempt_output_file
                )
                print(f"✗ Outputs don't match")
                print(f"Difference: {diff[:200]}...")
                attempt_data['verdict'] = 'Wrong Answer'
                attempt_data['output_match'] = False
                attempt_data['output_diff'] = diff
                metadata['optimal_attempts'].append(attempt_data)
                feedback = f"Your solution produced incorrect output:\n{diff}\n\nPlease fix the logic."
                metadata['errors'].append(f"Attempt {attempt}: Output mismatch")

        print("\n" + "=" * 80)
        print(f"FAILED: Could not find correct solution in {self.max_attempts} attempts")
        print("=" * 80)

        # Generate results JSON even on failure
        self._generate_results_json(problem_statement, metadata)

        return False, optimal_code, metadata

    def _generate_results_json(self, problem_statement: str, metadata: Dict):
        """Generate results.json for the web viewer."""
        # Read all necessary files
        test_input = ""
        brute_code = ""
        brute_output = ""

        try:
            with open(self.files['test_inputs'], 'r') as f:
                test_input = f.read()
        except:
            pass

        try:
            with open(self.files['brute_solution'], 'r') as f:
                brute_code = f.read()
        except:
            pass

        try:
            with open(self.files['brute_outputs'], 'r') as f:
                brute_output = f.read()
        except:
            pass

        results = {
            'problem_statement': problem_statement,
            'test_input': test_input,
            'test_output': brute_output,
            'brute_force_code': brute_code,
            'optimal_attempts': metadata['optimal_attempts'],
            'success': metadata['optimal_solution_found'],
            'total_attempts': metadata['attempts'],
            'optimal_execution_time': metadata.get('optimal_execution_time', None),
            'comprehensive_tests': metadata.get('comprehensive_tests', None)
        }

        results_file = os.path.join(self.workspace, 'results.json')
        with open(results_file, 'w') as f:
            json.dump(results, f, indent=2)

        print(f"\n✓ Results saved to: {results_file}")
        print("\n" + "=" * 80)
        print("📊 VIEW RESULTS IN WEB BROWSER")
        print("=" * 80)
        print("\nTo view the beautiful HTML report, run:")
        print("\n  python -m http.server 8000")
        print("\nThen open: http://localhost:8000/viewer.html")
        print("\n(HTTP server needed to avoid CORS restrictions)")
        print("=" * 80)

    def run_comprehensive_tests(self, problem_statement: str, optimal_code: str, image_paths: Optional[List[str]] = None, sample_input: Optional[str] = None, sample_output: Optional[str] = None) -> Dict:
        """
        Run comprehensive tests on the optimal solution.
        
        Args:
            problem_statement: The problem description
            optimal_code: The optimal solution code
            image_paths: Optional list of image file paths
            sample_input: Optional sample input from problem folder
            sample_output: Optional sample output from problem folder
            
        Returns:
            Dictionary with comprehensive test results
        """
        print("\n" + "=" * 80)
        print("COMPREHENSIVE TESTING")
        print("=" * 80)
        
        comprehensive_results = {
            'test_cases_generated': False,
            'test_cases_executed': False,
            'all_passed': False,
            'total_test_cases': 0,
            'passed_test_cases': 0,
            'failed_test_cases': 0,
            'test_results': [],
            'average_execution_time': 0.0,
            'max_execution_time': 0.0,
            'min_execution_time': float('inf'),
            'errors': []
        }
        
        # Generate comprehensive test cases
        print("\nGenerating comprehensive test cases...")
        try:
            with ProgressIndicator("Generating comprehensive test cases"):
                comprehensive_test_cases = self.comprehensive_test_agent.generate_test_cases(
                    problem_statement,
                    image_paths=image_paths,
                    sample_input=sample_input,
                    sample_output=sample_output
                )
            
            comprehensive_test_file = os.path.join(self.workspace, 'comprehensive_tests.txt')
            with open(comprehensive_test_file, 'w') as f:
                f.write(comprehensive_test_cases)
            
            comprehensive_results['test_cases_generated'] = True
            print(f"✓ Comprehensive test cases saved to: {comprehensive_test_file}\n")
        except Exception as e:
            error = f"Failed to generate comprehensive test cases: {str(e)}"
            comprehensive_results['errors'].append(error)
            print(f"✗ {error}\n")
            return comprehensive_results
        
        # Parse test cases (assuming they're separated by blank lines)
        test_cases = []
        current_case = []
        for line in comprehensive_test_cases.split('\n'):
            if line.strip() == '':
                if current_case:
                    test_cases.append('\n'.join(current_case))
                    current_case = []
            else:
                current_case.append(line)
        if current_case:
            test_cases.append('\n'.join(current_case))
        
        comprehensive_results['total_test_cases'] = len(test_cases)
        print(f"Found {len(test_cases)} test cases to execute\n")
        
        # Execute each test case
        print("Executing comprehensive test cases...")
        total_exec_time = 0.0
        
        for i, test_case in enumerate(test_cases, 1):
            test_input_file = os.path.join(self.workspace, f'comprehensive_test_{i}_input.txt')
            test_output_file = os.path.join(self.workspace, f'comprehensive_test_{i}_output.txt')
            
            # Write test case to input file
            with open(test_input_file, 'w') as f:
                f.write(test_case)
            
            # Execute optimal solution on this test case
            success, error, exec_time = self.executor.execute(
                self.files['optimal_solution'],
                test_input_file,
                test_output_file
            )
            
            test_result = {
                'test_number': i,
                'input': test_case[:200] + '...' if len(test_case) > 200 else test_case,
                'success': success,
                'execution_time': exec_time,
                'error': error if not success else None
            }
            
            if success:
                comprehensive_results['passed_test_cases'] += 1
                total_exec_time += exec_time
                comprehensive_results['max_execution_time'] = max(comprehensive_results['max_execution_time'], exec_time)
                comprehensive_results['min_execution_time'] = min(comprehensive_results['min_execution_time'], exec_time)
                print(f"✓ Test case {i}/{len(test_cases)} passed (Time: {exec_time:.3f}s)")
            else:
                comprehensive_results['failed_test_cases'] += 1
                print(f"✗ Test case {i}/{len(test_cases)} failed: {error[:100]}")
            
            comprehensive_results['test_results'].append(test_result)
        
        comprehensive_results['test_cases_executed'] = True
        comprehensive_results['all_passed'] = (comprehensive_results['failed_test_cases'] == 0)
        
        if comprehensive_results['passed_test_cases'] > 0:
            comprehensive_results['average_execution_time'] = total_exec_time / comprehensive_results['passed_test_cases']
            if comprehensive_results['min_execution_time'] == float('inf'):
                comprehensive_results['min_execution_time'] = 0.0
        
        print("\n" + "=" * 80)
        print("COMPREHENSIVE TEST RESULTS")
        print("=" * 80)
        print(f"Total test cases: {comprehensive_results['total_test_cases']}")
        print(f"Passed: {comprehensive_results['passed_test_cases']}")
        print(f"Failed: {comprehensive_results['failed_test_cases']}")
        if comprehensive_results['passed_test_cases'] > 0:
            print(f"Average execution time: {comprehensive_results['average_execution_time']:.3f}s")
            print(f"Min execution time: {comprehensive_results['min_execution_time']:.3f}s")
            print(f"Max execution time: {comprehensive_results['max_execution_time']:.3f}s")
        print("=" * 80)
        
        return comprehensive_results
