#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Multi-Agent Programming Problem Solver

This system uses three specialized agents to solve programming problems:
1. TesterAgent: Generates small test cases
2. BruteAgent: Creates a correct but potentially inefficient solution
3. OptimalAgent: Iteratively develops an efficient solution
"""

import sys
import io
import os
import glob
import yaml
from orchestrator import ProblemSolverOrchestrator

# Ensure UTF-8 encoding for Windows console
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')


def find_image_files(directory: str, patterns: list) -> list:
    """Find image files in the directory matching the given patterns."""
    image_files = []
    for pattern in patterns:
        # Use glob to find files matching the pattern
        full_pattern = os.path.join(directory, pattern)
        image_files.extend(glob.glob(full_pattern))
        # Also try case-insensitive variants
        image_files.extend(glob.glob(full_pattern.lower()))
        image_files.extend(glob.glob(full_pattern.upper()))
    # Remove duplicates and sort
    return sorted(list(set(image_files)))


def main():
    # Load configuration
    config_path = "config.yaml"
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
    except FileNotFoundError:
        print(f"Error: {config_path} not found!")
        return 1

    # Get problem configuration
    problem_config = config.get('problem', {})
    problem_folder = problem_config.get('folder', './problem')
    statement_file = problem_config.get('statement', 'statement.txt')
    sample_input_file = problem_config.get('sample_input', 'sample_in.txt')
    sample_output_file = problem_config.get('sample_output', 'sample_out.txt')
    image_patterns = problem_config.get('image_patterns', ['img_*.jpg', 'img_*.jpeg', 'img_*.png'])

    # Construct full paths
    statement_path = os.path.join(problem_folder, statement_file)
    sample_input_path = os.path.join(problem_folder, sample_input_file)
    sample_output_path = os.path.join(problem_folder, sample_output_file)

    # Read problem statement
    try:
        with open(statement_path, 'r', encoding='utf-8') as f:
            problem_statement = f.read().strip()
    except FileNotFoundError:
        print(f"Error: Problem statement not found at {statement_path}!")
        print(f"Please create a {statement_file} file in the {problem_folder} folder.")
        return 1

    # Read sample input/output if they exist
    sample_input = None
    sample_output = None
    if os.path.exists(sample_input_path):
        try:
            with open(sample_input_path, 'r', encoding='utf-8') as f:
                sample_input = f.read().strip()
        except Exception as e:
            print(f"Warning: Could not read sample input from {sample_input_path}: {e}")

    if os.path.exists(sample_output_path):
        try:
            with open(sample_output_path, 'r', encoding='utf-8') as f:
                sample_output = f.read().strip()
        except Exception as e:
            print(f"Warning: Could not read sample output from {sample_output_path}: {e}")

    # Find image files in the problem folder
    image_paths = find_image_files(problem_folder, image_patterns) if os.path.exists(problem_folder) else []

    print("Multi-Agent Programming Problem Solver")
    print("=" * 80)
    print(f"\nProblem folder: {problem_folder}")
    print(f"Problem statement: {statement_path}")
    if sample_input:
        print(f"Sample input: {sample_input_path}")
    if sample_output:
        print(f"Sample output: {sample_output_path}")
    if image_paths:
        print(f"Images found: {len(image_paths)}")
        for img in image_paths:
            print(f"  - {img}")
    print("\n" + problem_statement)
    if sample_input:
        print("\n" + "=" * 80)
        print("SAMPLE INPUT:")
        print("=" * 80)
        print(sample_input)
    if sample_output:
        print("\n" + "=" * 80)
        print("SAMPLE OUTPUT:")
        print("=" * 80)
        print(sample_output)
    print("\n")

    # Initialize orchestrator
    orchestrator = ProblemSolverOrchestrator()

    # Solve the problem
    success, optimal_code, metadata = orchestrator.solve(
        problem_statement, 
        image_paths=image_paths if image_paths else None,
        sample_input=sample_input,
        sample_output=sample_output
    )

    # Print results
    print("\n" + "=" * 80)
    print("FINAL RESULTS")
    print("=" * 80)
    print(f"Success: {success}")
    print(f"Attempts used: {metadata['attempts']}/{orchestrator.max_attempts}")
    print(f"Test cases generated: {metadata['test_cases_generated']}")
    print(f"Brute force generated: {metadata['brute_force_generated']}")
    print(f"Brute force executed: {metadata['brute_force_executed']}")
    print(f"Optimal solution found: {metadata['optimal_solution_found']}")
    if metadata.get('optimal_execution_time') is not None:
        print(f"Optimal solution execution time: {metadata['optimal_execution_time']:.3f}s")

    if metadata['errors']:
        print(f"\nErrors encountered: {len(metadata['errors'])}")
        for i, error in enumerate(metadata['errors'], 1):
            print(f"  {i}. {error}")

    if success and optimal_code:
        print("\n" + "=" * 80)
        print("OPTIMAL SOLUTION CODE:")
        print("=" * 80)
        print(optimal_code)
        print("\n")
        print(f"Solution saved to: {orchestrator.files['optimal_solution']}")
        
        # Ask user if they want to run comprehensive tests
        print("\n" + "=" * 80)
        print("COMPREHENSIVE TESTING OPTION")
        print("=" * 80)
        print("Would you like to generate and run comprehensive test cases?")
        print("This will create additional test cases with edge cases and large inputs.")
        print("(y/n): ", end='', flush=True)
        
        try:
            user_input = input().strip().lower()
            if user_input in ['y', 'yes']:
                # Run comprehensive tests
                comprehensive_results = orchestrator.run_comprehensive_tests(
                    problem_statement,
                    optimal_code,
                    image_paths=image_paths if image_paths else None,
                    sample_input=sample_input,
                    sample_output=sample_output
                )
                
                # Update metadata with comprehensive test results
                metadata['comprehensive_tests'] = comprehensive_results
                
                # Regenerate results.json with comprehensive test data
                orchestrator._generate_results_json(problem_statement, metadata)
            else:
                print("Skipping comprehensive tests.")
        except (EOFError, KeyboardInterrupt):
            print("\nSkipping comprehensive tests.")
    else:
        print("\nFailed to find a working solution.")
        if orchestrator.files['brute_solution']:
            print(f"Brute force solution available at: {orchestrator.files['brute_solution']}")

    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
