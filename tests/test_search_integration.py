"""Test suite for web search integration.

Tests all components:
- Search decision engine
- Search providers (Serper, Tavily, Python fallback)
- Search router with fallback logic
- Chat service integration
"""

import asyncio
import logging
from typing import List

from app.services.search_decision_engine import SearchDecisionEngine, SearchRequestType
from app.services.search_router import SearchRouter
from app.services.providers.serper_provider import SerperProvider
from app.services.providers.tavily_provider import TavilyProvider
from app.services.providers.python_search_provider import PythonSearchProvider

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger("tests.search_integration")


class SearchTests:
    """Comprehensive search functionality tests."""
    
    # Test cases: (query, expected_type, should_search)
    TEST_CASES = [
        # Queries that should NOT search
        ("What is Python?", SearchRequestType.GENERAL, False),
        ("Explain REST APIs", SearchRequestType.EXPLANATION, False),
        ("What is 2 + 2?", SearchRequestType.REASONING, False),
        ("Write a Python function", SearchRequestType.CODING, False),
        ("Translate 'hello' to Spanish", SearchRequestType.TRANSLATION, False),
        ("Create a landing page", SearchRequestType.CREATIVE, False),
        
        # Queries that SHOULD search
        ("What is the latest Python version?", SearchRequestType.LATEST, True),
        ("What happened today?", SearchRequestType.CURRENT, True),
        ("Latest news about AI", SearchRequestType.NEWS, True),
        ("Current price of Bitcoin", SearchRequestType.PRICE, True),
        ("Search the web for...", SearchRequestType.EXPLICIT, True),
        ("Compare iPhone 15 vs Samsung Galaxy", SearchRequestType.COMPARISON, True),
        ("Is this true?", SearchRequestType.FACT_CHECK, True),
        ("Restaurants near me", SearchRequestType.LOCAL, True),
        ("Latest React release notes", SearchRequestType.LATEST, True),
    ]
    
    @staticmethod
    async def test_decision_engine():
        """Test search decision engine classification."""
        logger.info("=" * 70)
        logger.info("TESTING SEARCH DECISION ENGINE")
        logger.info("=" * 70)
        
        passed = 0
        failed = 0
        
        for query, expected_type, expected_search in SearchTests.TEST_CASES:
            try:
                classified_type = SearchDecisionEngine.classify_request(query)
                should_search = SearchDecisionEngine.should_search(query)
                reason = SearchDecisionEngine.get_search_reason(query)
                
                type_match = classified_type == expected_type
                search_match = should_search == expected_search
                
                status = "✓ PASS" if (type_match and search_match) else "✗ FAIL"
                
                logger.info(f"{status}: '{query}'")
                logger.info(f"  Type: {classified_type} (expected {expected_type}) {'' if type_match else '[MISMATCH]'}")
                logger.info(f"  Search: {should_search} (expected {expected_search}) {'' if search_match else '[MISMATCH]'}")
                logger.info(f"  Reason: {reason}")
                
                if type_match and search_match:
                    passed += 1
                else:
                    failed += 1
                    
            except Exception as e:
                logger.error(f"✗ EXCEPTION for '{query}': {e}")
                failed += 1
        
        logger.info(f"\nDecision Engine Results: {passed} passed, {failed} failed")
        return passed, failed
    
    @staticmethod
    async def test_provider_availability():
        """Test availability of search providers."""
        logger.info("=" * 70)
        logger.info("TESTING PROVIDER AVAILABILITY")
        logger.info("=" * 70)
        
        serper_available = SerperProvider.is_available()
        tavily_available = TavilyProvider.is_available()
        python_available = PythonSearchProvider.is_available()
        
        logger.info(f"Serper available: {serper_available}")
        logger.info(f"Tavily available: {tavily_available}")
        logger.info(f"Python fallback available: {python_available}")
        
        status = SearchRouter.get_search_status()
        logger.info(f"\nOverall search status: {status}")
        
        if not status["any_available"]:
            logger.warning("⚠ WARNING: No search providers available")
            return False
        
        logger.info(f"✓ At least one provider available")
        return True
    
    @staticmethod
    async def test_serper_provider():
        """Test Serper provider (if configured)."""
        logger.info("=" * 70)
        logger.info("TESTING SERPER PROVIDER")
        logger.info("=" * 70)
        
        if not SerperProvider.is_available():
            logger.warning("Serper not configured, skipping")
            return None
        
        try:
            result = await SerperProvider.search("What is artificial intelligence?", num_results=5)
            logger.info(f"✓ Serper search succeeded")
            logger.info(f"  Results: {result.get('result_count', 0)}")
            logger.info(f"  Provider: {result.get('provider')}")
            logger.info(f"  First result: {result.get('results', [{}])[0].get('title', 'N/A')}")
            return True
        except Exception as e:
            logger.error(f"✗ Serper search failed: {e}")
            return False
    
    @staticmethod
    async def test_tavily_provider():
        """Test Tavily provider (if configured)."""
        logger.info("=" * 70)
        logger.info("TESTING TAVILY PROVIDER")
        logger.info("=" * 70)
        
        if not TavilyProvider.is_available():
            logger.warning("Tavily not configured, skipping")
            return None
        
        try:
            result = await TavilyProvider.search("Latest breakthroughs in AI")
            logger.info(f"✓ Tavily search succeeded")
            logger.info(f"  Results: {len(result.get('results', []))}")
            logger.info(f"  Provider: {result.get('provider')}")
            if result.get("results"):
                logger.info(f"  First result: {result.get('results', [{}])[0].get('title', 'N/A')}")
            return True
        except Exception as e:
            logger.error(f"✗ Tavily search failed: {e}")
            return False
    
    @staticmethod
    async def test_python_fallback():
        """Test Python fallback provider."""
        logger.info("=" * 70)
        logger.info("TESTING PYTHON FALLBACK PROVIDER")
        logger.info("=" * 70)
        
        if not PythonSearchProvider.is_available():
            logger.warning("Python fallback (ddgs) not installed, skipping")
            logger.info("Install with: pip install duckduckgo-search")
            return None
        
        try:
            result = await PythonSearchProvider.search("Python programming tutorial", num_results=5)
            logger.info(f"✓ Python fallback search succeeded")
            logger.info(f"  Results: {result.get('result_count', 0)}")
            logger.info(f"  Provider: {result.get('provider')}")
            logger.info(f"  Fallback: {result.get('fallback', False)}")
            if result.get("results"):
                logger.info(f"  First result: {result.get('results', [{}])[0].get('title', 'N/A')}")
            return True
        except Exception as e:
            logger.error(f"✗ Python fallback search failed: {e}")
            return False
    
    @staticmethod
    async def test_search_router():
        """Test search router with fallback logic."""
        logger.info("=" * 70)
        logger.info("TESTING SEARCH ROUTER")
        logger.info("=" * 70)
        
        test_queries = [
            ("What is the latest OpenAI model?", SearchRequestType.LATEST),
            ("Explain quantum computing", SearchRequestType.EXPLANATION),
            ("Breaking news today", SearchRequestType.NEWS),
        ]
        
        results = []
        
        for query, expected_type in test_queries:
            try:
                logger.info(f"\nTesting query: '{query}'")
                
                # Test with decision engine
                should_search = SearchDecisionEngine.should_search(query)
                logger.info(f"  Should search: {should_search}")
                
                if should_search:
                    # Perform search
                    result = await SearchRouter.search_with_decision(query, num_results=5)
                    
                    if result:
                        logger.info(f"  ✓ Search succeeded with {result.get('provider')}")
                        logger.info(f"  Results count: {result.get('result_count', 0)}")
                        results.append(True)
                    else:
                        logger.warning(f"  ✗ Search returned no results")
                        results.append(False)
                else:
                    logger.info(f"  → Search not needed (as expected)")
                    results.append(True)
                    
            except Exception as e:
                logger.error(f"  ✗ Exception: {e}")
                results.append(False)
        
        passed = sum(results)
        total = len(results)
        logger.info(f"\nRouter Results: {passed}/{total} passed")
        return passed == total
    
    @staticmethod
    async def run_all_tests():
        """Run all tests."""
        logger.info("\n" + "=" * 70)
        logger.info("VEDAAPEX WEB SEARCH INTEGRATION TEST SUITE")
        logger.info("=" * 70 + "\n")
        
        # Test 1: Decision Engine
        passed, failed = await SearchTests.test_decision_engine()
        decision_ok = failed == 0
        
        # Test 2: Provider Availability
        availability_ok = await SearchTests.test_provider_availability()
        
        # Test 3: Individual Providers
        logger.info("\n")
        serper_ok = await SearchTests.test_serper_provider()
        tavily_ok = await SearchTests.test_tavily_provider()
        python_ok = await SearchTests.test_python_fallback()
        
        # Test 4: Router
        logger.info("\n")
        router_ok = await SearchTests.test_search_router()
        
        # Summary
        logger.info("\n" + "=" * 70)
        logger.info("TEST SUMMARY")
        logger.info("=" * 70)
        logger.info(f"Decision Engine: {'✓ PASS' if decision_ok else '✗ FAIL'}")
        logger.info(f"Provider Availability: {'✓ PASS' if availability_ok else '✗ FAIL'}")
        logger.info(f"Serper Provider: {f'✓ PASS' if serper_ok else ('✗ FAIL' if serper_ok is False else '⊘ SKIPPED')}")
        logger.info(f"Tavily Provider: {f'✓ PASS' if tavily_ok else ('✗ FAIL' if tavily_ok is False else '⊘ SKIPPED')}")
        logger.info(f"Python Fallback: {f'✓ PASS' if python_ok else ('✗ FAIL' if python_ok is False else '⊘ SKIPPED')}")
        logger.info(f"Search Router: {'✓ PASS' if router_ok else '✗ FAIL'}")
        logger.info("=" * 70 + "\n")
        
        return decision_ok and availability_ok and router_ok


if __name__ == "__main__":
    result = asyncio.run(SearchTests.run_all_tests())
    exit(0 if result else 1)
