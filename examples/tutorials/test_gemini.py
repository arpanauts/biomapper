import requests
from dotenv import load_dotenv
import os


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


if __name__ == "__main__":
    test_gemini_api()
