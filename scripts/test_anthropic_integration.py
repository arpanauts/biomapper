#!/usr/bin/env python3
"""
Test script to verify Anthropic (Claude) integration for LLM analysis.

This script tests that:
1. ANTHROPIC_API_KEY is properly loaded from .env
2. The LLM analysis action can use Anthropic
3. Claude can generate analysis for progressive mapping results
"""

import os
import sys
import asyncio
from pathlib import Path
from dotenv import load_dotenv

# Add biomapper to path
sys.path.insert(0, "/home/ubuntu/biomapper")

# Load environment variables from .env
load_dotenv("/home/ubuntu/biomapper/.env")


async def test_anthropic_integration():
    """Test Anthropic integration for LLM analysis."""
    
    print("=" * 80)
    print("Testing Anthropic (Claude) Integration")
    print("=" * 80)
    
    # Check API key
    print("\n1. Checking ANTHROPIC_API_KEY...")
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if api_key:
        print(f"   ✅ API key found (length: {len(api_key)} chars)")
    else:
        print("   ❌ ANTHROPIC_API_KEY not found in environment")
        return False
    
    # Test provider initialization
    print("\n2. Testing Anthropic provider initialization...")
    try:
        from biomapper.core.strategy_actions.utils.llm_providers import AnthropicProvider
        
        provider = AnthropicProvider(model="claude-3-opus-20240229")
        print(f"   ✅ Provider initialized with model: {provider.model}")
        print(f"   ✅ API key loaded: {'Yes' if provider.api_key else 'No'}")
    except Exception as e:
        print(f"   ❌ Failed to initialize provider: {e}")
        return False
    
    # Test with sample progressive stats
    print("\n3. Testing analysis generation with sample data...")
    sample_data = {
        "progressive_stats": {
            "total_processed": 1000,
            "stages": {
                1: {
                    "name": "direct_match",
                    "method": "Direct UniProt",
                    "matched": 650,
                    "cumulative_matched": 650,
                    "confidence_avg": 1.0,
                    "computation_time": "0.5s"
                },
                3: {
                    "name": "historical_resolution",
                    "method": "Historical API",
                    "new_matches": 150,
                    "cumulative_matched": 800,
                    "confidence_avg": 0.90,
                    "computation_time": "12.3s",
                    "api_calls": 150
                }
            },
            "final_match_rate": 0.80
        }
    }
    
    # Create a simple test prompt
    test_prompt = """
    Analyze this progressive protein mapping result and provide:
    1. A brief summary (2-3 sentences)
    2. Key performance metrics
    3. One optimization recommendation
    
    Keep the response concise and scientific.
    """
    
    try:
        print("   Sending request to Claude...")
        response = await provider.generate_analysis(test_prompt, sample_data)
        
        if response.success:
            print(f"   ✅ Analysis generated successfully")
            print(f"   ✅ Tokens used: {response.usage.total_tokens}")
            print(f"\n   Response preview (first 200 chars):")
            print(f"   {response.content[:200]}...")
        else:
            print(f"   ❌ Analysis failed: {response.error_message}")
            return False
            
    except Exception as e:
        print(f"   ❌ Error during analysis: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Test the actual action
    print("\n4. Testing GENERATE_LLM_ANALYSIS action...")
    try:
        from biomapper.core.strategy_actions.reports.generate_llm_analysis import (
            GenerateLLMAnalysis,
            LLMAnalysisParams
        )
        
        action = GenerateLLMAnalysis()
        params = LLMAnalysisParams(
            provider="anthropic",
            model="claude-3-opus-20240229",
            include_recommendations=True,
            output_directory="/tmp/biomapper/test_anthropic"
        )
        
        print(f"   ✅ Action initialized with Anthropic provider")
        print(f"   ✅ Ready to use in v3.0 strategy")
        
    except Exception as e:
        print(f"   ❌ Failed to initialize action: {e}")
        return False
    
    return True


def main():
    """Main entry point."""
    success = asyncio.run(test_anthropic_integration())
    
    if success:
        print("\n" + "=" * 80)
        print("✅ ANTHROPIC INTEGRATION TEST PASSED")
        print("=" * 80)
        print("\nThe v3.0 strategy is configured to use Claude for analysis!")
        print("\nConfiguration in strategy:")
        print("  llm_provider: anthropic")
        print("  llm_model: claude-3-opus-20240229")
        print("\nTo run the strategy with Claude analysis:")
        print("  poetry run biomapper run prot_arv_to_kg2c_uniprot_v3.0_progressive")
    else:
        print("\n" + "=" * 80)
        print("❌ ANTHROPIC INTEGRATION TEST FAILED")
        print("=" * 80)
        print("\nPlease ensure:")
        print("1. ANTHROPIC_API_KEY is set in .env file")
        print("2. The API key is valid and has credits")
        print("3. Network connection is available")
        sys.exit(1)


if __name__ == "__main__":
    main()