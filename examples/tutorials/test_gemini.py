import requests
from dotenv import load_dotenv
import os
import pytest
from unittest.mock import patch, Mock


@pytest.mark.skipif(
    not os.getenv("GEMINI_API_URL") or not os.getenv("GEMINI_API_KEY"),
    reason="GEMINI_API_URL and GEMINI_API_KEY not set in environment",
)
def test_gemini_api():
    """Test the Gemini API integration."""
    # Load environment variables
    load_dotenv()

    # Test prompt
    prompt = {
        "model": "gemini-pro",
        "messages": [{"content": "What is Phenomics according to Lee Hood?"}],
    }

    # Make API call
    r = requests.post(
        os.getenv("GEMINI_API_URL"),
        headers={"Authorization": f"Bearer {os.getenv('GEMINI_API_KEY')}"},
        json=prompt,
    )

    print(f"Status code: {r.status_code}")
    print(f"Response text: {r.text}")

    if r.status_code == 200:
        res = r.json()
        print("\nParsed response:")
        print(res["choices"][0]["message"]["content"])


def test_gemini_api_mocked():
    """Test the Gemini API integration with mocked response."""
    # Mock response
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "choices": [
            {
                "message": {
                    "content": "Phenomics is the comprehensive study of phenotypes..."
                }
            }
        ]
    }
    mock_response.text = '{"choices": [{"message": {"content": "Phenomics is..."}}]}'

    # Test prompt
    prompt = {
        "model": "gemini-pro",
        "messages": [{"content": "What is Phenomics according to Lee Hood?"}],
    }

    with patch("requests.post", return_value=mock_response):
        # Make API call
        r = requests.post(
            "https://api.example.com/gemini",  # Mock URL
            headers={"Authorization": "Bearer mock_key"},
            json=prompt,
        )

        assert r.status_code == 200
        res = r.json()
        assert "choices" in res
        assert res["choices"][0]["message"]["content"].startswith("Phenomics")


if __name__ == "__main__":
    test_gemini_api()
