#!/usr/bin/env python3
"""
Test script to validate the caching implementation in PDFComparisonEngine
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

from app.services.pdf_comparison_service import PDFComparisonEngine
import time
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_caching_performance():
    """Test that caching improves performance by avoiding repeated text extraction"""
    
    # Find test files (adjust paths as needed)
    workflow_path = "app/data/workflow-FSD_CH0047533549_SWC_CH_de.json"
    pdf1_path = "app/data/SRC-FSD_CH0047533549_SWC_CH_de.pdf"
    pdf2_path = "app/data/SRC-FSD_CH0009074300_SWC_CH_de.pdf"
    
    # Check if files exist
    if not all(os.path.exists(path) for path in [workflow_path, pdf1_path, pdf2_path]):
        logger.error("Test files not found. Please ensure PDF files and workflow exist.")
        return False
    
    logger.info("Starting caching performance test...")
    
    # Create engine instance
    engine = PDFComparisonEngine(workflow_path, pdf1_path, pdf2_path)
    
    try:
        # Load resources
        start_time = time.time()
        engine.load_resources()
        load_time = time.time() - start_time
        logger.info(f"Resource loading took: {load_time:.2f} seconds")
        
        # Test page caching
        start_time = time.time()
        engine._cache_all_pages()
        cache_time = time.time() - start_time
        logger.info(f"Page caching took: {cache_time:.2f} seconds")
        
        # Test cache retrieval (should be very fast)
        start_time = time.time()
        for doc_num in [1, 2]:
            doc = engine.doc1 if doc_num == 1 else engine.doc2
            for page_num in range(min(3, len(doc))):  # Test first 3 pages
                cached_text = engine.get_cached_page_text(doc_num, page_num)
                assert cached_text is not None, f"Cache miss for doc {doc_num}, page {page_num}"
        
        retrieval_time = time.time() - start_time
        logger.info(f"Cache retrieval test took: {retrieval_time:.4f} seconds")
        
        # Test full text cache preparation
        start_time = time.time()
        engine._prepare_full_text_cache()
        full_cache_time = time.time() - start_time
        logger.info(f"Full text cache preparation took: {full_cache_time:.2f} seconds")
        
        # Verify cache contents
        assert engine.full_text_doc1_md is not None, "Full text cache for doc1 is empty"
        assert engine.full_text_doc2_md is not None, "Full text cache for doc2 is empty"
        assert len(engine.page_cache_doc1) > 0, "Page cache for doc1 is empty"
        assert len(engine.page_cache_doc2) > 0, "Page cache for doc2 is empty"
        
        logger.info("✅ Caching test PASSED!")
        logger.info(f"Doc1 has {len(engine.page_cache_doc1)} cached pages")
        logger.info(f"Doc2 has {len(engine.page_cache_doc2)} cached pages")
        logger.info(f"Full text cache sizes - Doc1: {len(engine.full_text_doc1_md)} chars, Doc2: {len(engine.full_text_doc2_md)} chars")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Caching test FAILED: {e}")
        return False
        
    finally:
        engine.close_resources()

if __name__ == "__main__":
    success = test_caching_performance()
    sys.exit(0 if success else 1) 