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
from orchestrator import ProblemSolverOrchestrator

# Ensure UTF-8 encoding for Windows console
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')


def main():
    print("Multi-Agent Programming Problem Solver")
    print("=" * 80)

    # Initialize orchestrator
    orchestrator = ProblemSolverOrchestrator()

    # Load problem files from problem folder
    try:
        problem_statement, sample_input, sample_output, image_paths = orchestrator.load_problem_files()
        
        print(f"\nProblem loaded from: {orchestrator.problem_statement_file}")
        if sample_input:
            print(f"Sample input loaded from: {orchestrator.sample_input_file}")
        if sample_output:
            print(f"Sample output loaded from: {orchestrator.sample_output_file}")
        if image_paths:
            print(f"Images found: {len(image_paths)}")
            for img in image_paths:
                print(f"  - {img}")
        print("\n" + problem_statement)
        if sample_input:
            print("\n=== SAMPLE INPUT ===")
            print(sample_input)
        if sample_output:
            print("\n=== SAMPLE OUTPUT ===")
            print(sample_output)
        print("\n")
    except FileNotFoundError as e:
        print(f"Error: {e}")
        print(f"\nPlease ensure the problem folder structure is set up correctly:")
        print(f"  - Problem folder: {orchestrator.problem_folder}")
        print(f"  - Required file: {orchestrator.problem_statement_file}")
        print(f"  - Optional files: {orchestrator.sample_input_file}, {orchestrator.sample_output_file}")
        print(f"  - Images matching pattern: {orchestrator.image_pattern}")
        return 1
    except Exception as e:
        print(f"Error loading problem files: {e}")
        return 1

    # Solve the problem
    success, optimal_code, metadata = orchestrator.solve(
        problem_statement, 
        sample_input=sample_input,
        sample_output=sample_output,
        image_paths=image_paths if image_paths else None
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
        print(f"All generated files are in: {orchestrator.generated_files_dir}")
    else:
        print("\nFailed to find a working solution.")
        if orchestrator.files['brute_solution']:
            print(f"Brute force solution available at: {orchestrator.files['brute_solution']}")
        print(f"All generated files are in: {orchestrator.generated_files_dir}")

    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
