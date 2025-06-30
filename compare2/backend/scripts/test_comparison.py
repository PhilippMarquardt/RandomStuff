#!/usr/bin/env python3
"""
Test script for the PDF Comparison Engine

This script demonstrates how to use the PDF comparison engine with a workflow template.

Usage:
    python test_comparison.py <workflow.json> <pdf1.pdf> <pdf2.pdf>

Example:
    python test_comparison.py workflow-template.json document1.pdf document2.pdf
"""

import sys
import json
from pathlib import Path
from pdf_comparison_engine import PDFComparisonEngine


def print_detailed_results(results_path: str):
    """Print detailed results from the comparison"""
    with open(results_path, 'r') as f:
        results = json.load(f)
    
    print("\n" + "="*80)
    print("DETAILED COMPARISON RESULTS")
    print("="*80)
    
    # Metadata
    print("\nMetadata:")
    print(f"  Workflow: {results['metadata']['workflow']}")
    print(f"  Document 1: {results['metadata']['document1']}")
    print(f"  Document 2: {results['metadata']['document2']}")
    print(f"  Timestamp: {results['metadata']['timestamp']}")
    
    # Summary
    print("\nSummary:")
    summary = results['summary']
    for key, value in summary.items():
        print(f"  {key}: {value}")
    
    # Individual results
    print("\nDetailed Results:")
    for i, result in enumerate(results['results'], 1):
        print(f"\n{i}. Box ID: {result['box_id']}")
        print(f"   Type: {result['box_type']}")
        print(f"   Comparison Type: {result['comparison_type']}")
        print(f"   Status: {result['status']}")
        
        if result['error_message']:
            print(f"   Error: {result['error_message']}")
        
        if result['comparison_type'] == 'exact_match' and result['status'] == 'mismatch':
            print(f"   Text 1: '{result['details']['text1']}'")
            print(f"   Text 2: '{result['details']['text2']}'")
        
        if result['llm_response']:
            print(f"   LLM Response:")
            # Print first 200 characters of response
            response_preview = result['llm_response'][:200]
            if len(result['llm_response']) > 200:
                response_preview += "..."
            print(f"     {response_preview}")
        
        if result['comparison_type'] == 'position_not_guaranteed':
            details = result['details']
            if 'doc1_page' in details:
                print(f"   Found in Doc 1: Page {details.get('doc1_page', 'N/A')}")
                print(f"   Found in Doc 2: Page {details.get('doc2_page', 'N/A')}")


def main():
    """Main function to run the test"""
    if len(sys.argv) != 4:
        print(__doc__)
        sys.exit(1)
    
    workflow_path = sys.argv[1]
    pdf1_path = sys.argv[2]
    pdf2_path = sys.argv[3]
    
    # Validate inputs exist
    for path, name in [(workflow_path, "Workflow"), (pdf1_path, "PDF 1"), (pdf2_path, "PDF 2")]:
        if not Path(path).exists():
            print(f"Error: {name} file not found: {path}")
            sys.exit(1)
    
    # Run comparison
    print(f"Starting PDF comparison...")
    print(f"Workflow: {workflow_path}")
    print(f"PDF 1: {pdf1_path}")
    print(f"PDF 2: {pdf2_path}")
    
    try:
        engine = PDFComparisonEngine(workflow_path, pdf1_path, pdf2_path)
        output_path = "test_comparison_results.json"
        engine.save_results(output_path)
        
        # Print detailed results
        print_detailed_results(output_path)
        
        print(f"\nFull results saved to: {output_path}")
        
    except Exception as e:
        print(f"\nError during comparison: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main() 