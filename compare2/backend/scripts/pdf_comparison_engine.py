import argparse
import json
import logging
from pathlib import Path
from app.services.pdf_comparison_service import PDFComparisonEngine

def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="Compare two PDFs using an annotation workflow template")
    parser.add_argument("workflow", help="Path to the workflow JSON file")
    parser.add_argument("pdf1", help="Path to the first PDF")
    parser.add_argument("pdf2", help="Path to the second PDF")
    parser.add_argument("-o", "--output", default="comparison_results.json", 
                       help="Output file for results (default: comparison_results.json)")
    parser.add_argument("--log-level", default="INFO", 
                       choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
                       help="Set logging level")
    parser.add_argument("--debug", action="store_true",
                       help="Enable debug mode (saves images for position-not-guaranteed comparisons)")
    parser.add_argument("--include-reference-image", action="store_true",
                       help="Include reference image from workflow JSON in position-not-guaranteed comparisons")
    parser.add_argument("--use-headline", action="store_true",
                       help="Use page headlines for searching in position-not-guaranteed comparisons instead of reference text")
    parser.add_argument("--parallel-boxes", type=int, default=1,
                       help="Number of annotation boxes to process in parallel (default: 1 - sequential processing)")
    
    args = parser.parse_args()
    
    # Set logging level
    logging.basicConfig(level=getattr(logging, args.log_level.upper()), 
                        format='%(asctime)s - %(levelname)s - %(message)s')
    
    # Validate inputs
    for path, name in [(args.workflow, "Workflow"), (args.pdf1, "PDF 1"), (args.pdf2, "PDF 2")]:
        if not Path(path).exists():
            logging.error(f"{name} file not found: {path}")
            return 1
    
    # Run comparison
    try:
        engine = PDFComparisonEngine(args.workflow, args.pdf1, args.pdf2, 
                                   debug_mode=args.debug, 
                                   include_reference_image=args.include_reference_image, 
                                   use_headline=args.use_headline,
                                   parallel_boxes=args.parallel_boxes)
        engine.save_results(args.output)
        
        # Print summary
        with open(args.output, 'r') as f:
            results = json.load(f)
            
        summary = results['summary']
        logger = logging.getLogger(__name__)
        logger.info("\n" + "="*50)
        logger.info("COMPARISON SUMMARY")
        logger.info("="*50)
        logger.info(f"Total comparisons: {summary['total_comparisons']}")
        logger.info(f"Matches: {summary['matches']}")
        logger.info(f"Mismatches: {summary['mismatches']}")
        logger.info(f"Errors: {summary['errors']}")
        logger.info(f"Not found: {summary['not_found']}")
        logger.info(f"Success rate: {summary['success_rate']:.1f}%")
        logger.info("="*50)
        
        return 0
        
    except Exception as e:
        logging.error(f"Comparison failed: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    exit(main()) 