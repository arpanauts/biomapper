#!/usr/bin/env python3
"""
Test external API dependencies and connectivity for biomapper.
"""

import asyncio
import aiohttp
import time
from typing import Dict, Any, Optional
from dataclasses import dataclass
import logging


@dataclass
class APITestResult:
    """Result of API connectivity test."""

    api_name: str
    url: str
    success: bool
    response_time: float
    status_code: Optional[int] = None
    error_message: Optional[str] = None
    data_sample: Optional[str] = None


class APIConnectivityTester:
    """Test connectivity and performance of external APIs."""

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.session: Optional[aiohttp.ClientSession] = None

        # Define APIs to test
        self.apis_to_test = {
            "Chemical Translation Service": {
                "url": "https://cts.fiehnlab.ucdavis.edu/service/convert/Chemical%20Name/InChIKey/aspirin",
                "timeout": 10,
                "expected_status": 200,
            },
            "UniProt": {
                "url": "https://rest.uniprot.org/uniprotkb/P04637.json",
                "timeout": 10,
                "expected_status": 200,
            },
            "MyGene": {
                "url": "https://mygene.info/v3/gene/1017",
                "timeout": 10,
                "expected_status": 200,
            },
            "BioMart": {
                "url": "https://www.ensembl.org/biomart/martservice",
                "timeout": 15,
                "expected_status": 200,
                "method": "GET",
            },
            "PubChem": {
                "url": "https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/name/aspirin/property/InChIKey/JSON",
                "timeout": 10,
                "expected_status": 200,
            },
            "ChEBI": {
                "url": "https://www.ebi.ac.uk/webservices/chebi/2.0/test",
                "timeout": 10,
                "expected_status": 200,
            },
        }

    async def __aenter__(self):
        """Async context manager entry."""
        timeout = aiohttp.ClientTimeout(total=30)
        self.session = aiohttp.ClientSession(timeout=timeout)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.session:
            await self.session.close()

    async def test_api_connectivity(
        self, api_name: str, config: Dict[str, Any]
    ) -> APITestResult:
        """Test connectivity to a single API."""

        url = config["url"]
        timeout = config.get("timeout", 10)
        expected_status = config.get("expected_status", 200)
        method = config.get("method", "GET")

        start_time = time.time()

        try:
            if method.upper() == "GET":
                async with self.session.get(url) as response:
                    response_time = time.time() - start_time

                    # Read a small sample of the response
                    content = await response.text()
                    data_sample = content[:200] if content else None

                    success = response.status == expected_status

                    return APITestResult(
                        api_name=api_name,
                        url=url,
                        success=success,
                        response_time=response_time,
                        status_code=response.status,
                        data_sample=data_sample,
                    )
            else:
                # Handle other HTTP methods if needed
                async with self.session.request(method, url) as response:
                    response_time = time.time() - start_time

                    content = await response.text()
                    data_sample = content[:200] if content else None

                    success = response.status == expected_status

                    return APITestResult(
                        api_name=api_name,
                        url=url,
                        success=success,
                        response_time=response_time,
                        status_code=response.status,
                        data_sample=data_sample,
                    )

        except asyncio.TimeoutError:
            response_time = time.time() - start_time
            return APITestResult(
                api_name=api_name,
                url=url,
                success=False,
                response_time=response_time,
                error_message=f"Timeout after {timeout}s",
            )
        except Exception as e:
            response_time = time.time() - start_time
            return APITestResult(
                api_name=api_name,
                url=url,
                success=False,
                response_time=response_time,
                error_message=str(e),
            )

    async def test_all_apis(self) -> Dict[str, APITestResult]:
        """Test connectivity to all configured APIs."""

        results = {}

        tasks = []
        for api_name, config in self.apis_to_test.items():
            task = self.test_api_connectivity(api_name, config)
            tasks.append((api_name, task))

        # Execute all tests concurrently
        completed_tasks = await asyncio.gather(
            *[task for _, task in tasks], return_exceptions=True
        )

        for (api_name, _), result in zip(tasks, completed_tasks):
            if isinstance(result, Exception):
                results[api_name] = APITestResult(
                    api_name=api_name,
                    url=self.apis_to_test[api_name]["url"],
                    success=False,
                    response_time=0.0,
                    error_message=str(result),
                )
            else:
                results[api_name] = result

        return results

    def analyze_results(self, results: Dict[str, APITestResult]) -> Dict[str, Any]:
        """Analyze API test results and generate recommendations."""

        analysis = {
            "total_apis": len(results),
            "successful_apis": 0,
            "failed_apis": 0,
            "slow_apis": [],  # > 5 seconds
            "unavailable_apis": [],
            "timeout_apis": [],
            "average_response_time": 0.0,
            "reliability_score": 0.0,
        }

        total_response_time = 0.0

        for api_name, result in results.items():
            if result.success:
                analysis["successful_apis"] += 1
            else:
                analysis["failed_apis"] += 1

                if "timeout" in (result.error_message or "").lower():
                    analysis["timeout_apis"].append(api_name)
                else:
                    analysis["unavailable_apis"].append(api_name)

            if result.response_time > 5.0:
                analysis["slow_apis"].append(
                    {"api": api_name, "response_time": result.response_time}
                )

            total_response_time += result.response_time

        analysis["average_response_time"] = (
            total_response_time / len(results) if results else 0.0
        )
        analysis["reliability_score"] = (
            analysis["successful_apis"] / analysis["total_apis"] * 100
            if results
            else 0.0
        )

        return analysis


def generate_api_dependency_report(
    results: Dict[str, APITestResult], analysis: Dict[str, Any]
) -> str:
    """Generate comprehensive API dependency report."""

    report = f"""# External API Dependencies Analysis Report

## Summary
- **Total APIs Tested**: {analysis['total_apis']}
- **Successful Connections**: {analysis['successful_apis']}
- **Failed Connections**: {analysis['failed_apis']}
- **Average Response Time**: {analysis['average_response_time']:.2f}s
- **Reliability Score**: {analysis['reliability_score']:.1f}%

## API Status Details

"""

    for api_name, result in results.items():
        status_icon = "✅" if result.success else "❌"
        report += f"""### {status_icon} {api_name}
- **URL**: `{result.url}`
- **Status**: {'SUCCESS' if result.success else 'FAILED'}
- **Response Time**: {result.response_time:.2f}s
"""

        if result.status_code:
            report += f"- **Status Code**: {result.status_code}\n"

        if result.error_message:
            report += f"- **Error**: {result.error_message}\n"

        if result.data_sample:
            report += f"- **Sample Response**: `{result.data_sample[:100]}...`\n"

        report += "\n"

    # Performance Issues
    if analysis["slow_apis"]:
        report += """## Performance Issues

### Slow APIs (>5s response time)
"""
        for slow_api in analysis["slow_apis"]:
            report += f"- **{slow_api['api']}**: {slow_api['response_time']:.2f}s\n"

    # Connectivity Issues
    if analysis["failed_apis"] > 0:
        report += """
## Connectivity Issues
"""

        if analysis["timeout_apis"]:
            report += """
### Timeout Issues
These APIs exceeded the timeout threshold:
"""
            for api in analysis["timeout_apis"]:
                report += f"- {api}\n"

        if analysis["unavailable_apis"]:
            report += """
### Unavailable APIs
These APIs returned errors or unexpected status codes:
"""
            for api in analysis["unavailable_apis"]:
                report += f"- {api}\n"

    # Recommendations
    report += """
## Recommendations

"""

    if analysis["reliability_score"] < 80:
        report += """### Critical Action Required
- **Low reliability score detected**
- Implement retry logic with exponential backoff
- Add circuit breaker patterns for failing APIs
- Consider implementing caching for API responses
- Set up monitoring and alerting for API health

"""

    if analysis["slow_apis"]:
        report += """### Performance Optimization
- Increase timeout values for slow APIs
- Implement async/concurrent API calls
- Add response caching to reduce API load
- Consider API rate limiting to avoid throttling

"""

    if analysis["failed_apis"] > 0:
        report += """### Fault Tolerance
- Implement graceful degradation for failed APIs
- Add fallback data sources where possible
- Set up health check endpoints
- Create API status monitoring dashboard

"""

    report += """
## Infrastructure Requirements

### Network Configuration
- Ensure outbound HTTPS access is available
- Configure firewall rules for API endpoints
- Consider using a reverse proxy for API calls
- Set up DNS resolution for external domains

### Error Handling
- Implement comprehensive error logging
- Add retry mechanisms for transient failures
- Create fallback strategies for each API
- Set up alerting for API failures

### Monitoring
- Track API response times and success rates
- Monitor API quota usage and rate limits
- Set up automated health checks
- Create dashboards for API dependency status
"""

    return report


async def main():
    """Main function to run API connectivity tests."""

    print("Starting external API connectivity tests...")

    async with APIConnectivityTester() as tester:
        results = await tester.test_all_apis()
        analysis = tester.analyze_results(results)

        # Generate and save report
        report = generate_api_dependency_report(results, analysis)

        with open("/tmp/api_dependency_report.md", "w") as f:
            f.write(report)

        print("API connectivity test complete.")
        print(
            f"Results: {analysis['successful_apis']}/{analysis['total_apis']} APIs accessible"
        )
        print(f"Average response time: {analysis['average_response_time']:.2f}s")
        print(f"Reliability score: {analysis['reliability_score']:.1f}%")
        print("Report saved to /tmp/api_dependency_report.md")


if __name__ == "__main__":
    asyncio.run(main())
